"""Authenticated advisory service, not an arbitrary OpenAI proxy."""
import asyncio
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from ..policy import AppError, DEFAULT_MODEL, MAX_BODY, validate_request
from ..transport import openai_stream
from .ledger import Ledger


@dataclass(frozen=True)
class Config:
    database: str
    enabled: bool = False
    secret_file: str = ""
    model: str = DEFAULT_MODEL
    output_limit: int = 2048
    # micro-USD per million tokens: $0.40 / $1.60. Cached discounts ignored.
    input_rate: int = 400_000
    output_rate: int = 1_600_000
    model_context: int = 1_047_576
    price_valid_until: str = "2000-01-01"
    global_concurrency: int = 4
    server_secret_env: bool = False

    def check(self):
        if not self.enabled:
            raise AppError("disabled", "Sponsored mode disabled.")
        if self.model != DEFAULT_MODEL or self.model_context != 1_047_576 or not 16 <= self.output_limit <= 4096:
            raise AppError("configuration", "Model policy requires a reviewed service release.")
        if self.input_rate < 400_000 or self.output_rate < 1_600_000 or not 1 <= self.global_concurrency <= 32:
            raise AppError("configuration", "Invalid rate/concurrency policy.")
        try:
            if date.fromisoformat(self.price_valid_until) < date.today():
                raise ValueError()
        except ValueError:
            raise AppError("configuration", "Pricing review expired.") from None

    def cost(self, input_tokens, output_tokens):
        return (input_tokens * self.input_rate + output_tokens * self.output_rate + 999_999) // 1_000_000

    def reservation(self):
        # Reserve the entire model context, not a client estimate. No tool fees.
        return self.cost(self.model_context, self.output_limit)

    def read_key(self):
        try:
            if self.server_secret_env:
                if self.secret_file:
                    raise ValueError()
                # Explicit server-only adapter for managed, sealed secret stores.
                key = os.environ.get("KOA_SERVER_OPENAI_KEY", "").strip()
            else:
                with Path(self.secret_file).open(encoding="utf-8") as source:
                    key = source.read(2401).strip()
            if not key or len(key) > 2400 or "\n" in key or "\r" in key:
                raise ValueError()
            return key
        except Exception:
            raise AppError("configuration", "Server secret is unavailable or invalid.") from None


def create_app(config=None, provider=openai_stream):
    if config is None:
        config = Config(database=os.environ.get("KOA_LEDGER", "/data/ledger.sqlite3"),
                        enabled=os.environ.get("KOA_SPONSORED_ENABLED") == "true",
                        secret_file=os.environ.get("KOA_OPENAI_SECRET_FILE", ""),
                        server_secret_env=os.environ.get("KOA_USE_SERVER_SECRET_ENV") == "true",
                        price_valid_until=os.environ.get("KOA_PRICE_VALID_UNTIL", "2000-01-01"))
    ledger = Ledger(config.database)
    app = FastAPI(title="KiCad Open Assistant service", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ledger = ledger

    @app.exception_handler(AppError)
    async def known_error(request, error):
        code = error.code
        status = 401 if code == "authentication" else 403 if code == "revoked" else 429 if code in {"budget", "quota", "rate", "concurrency"} else 409 if code == "duplicate" else 503 if code in {"disabled", "accounting", "configuration"} else 400
        return JSONResponse({"error": code}, status_code=status, headers={"X-KOA-Error": code, "Cache-Control": "no-store"})

    async def authenticate(request):
        peer = request.client.host if request.client else "unknown"
        await asyncio.to_thread(ledger.attempt, hashlib.sha256(peer.encode()).hexdigest())
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise AppError("authentication", "Authentication required.")
        return await asyncio.to_thread(ledger.authenticate, auth[7:])

    @app.get("/healthz")
    async def health():
        return {"service": "kicad-open-assistant", "sponsored_configured": config.enabled}

    @app.get("/v1/status")
    async def status(request: Request):
        user = await authenticate(request)
        result = await asyncio.to_thread(ledger.status, user)
        try:
            config.check()
        except AppError:
            result["enabled"] = False
        return {**result, "model": config.model, "max_output_tokens": config.output_limit}

    @app.post("/v1/chat")
    async def chat(request: Request):
        user = await authenticate(request)
        config.check()
        key_id = request.headers.get("idempotency-key", "")
        if not re.fullmatch(r"[a-f0-9]{32}", key_id):
            raise AppError("invalid_request", "A request ID is required.")
        body = bytearray()
        try:
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > MAX_BODY:
                        raise AppError("limit", "Payload exceeds service limit.")
        except TimeoutError:
            raise AppError("limit", "Request body timed out.") from None
        try:
            value = json.loads(body)
        except Exception:
            raise AppError("invalid_request", "Invalid JSON.") from None
        await asyncio.to_thread(validate_request, value)
        if value["model"] != config.model or value["max_output_tokens"] > config.output_limit:
            raise AppError("model", "Server model or output policy does not match the reviewed request.")
        key = config.read_key()
        await asyncio.to_thread(ledger.reserve, user, key_id, config.reservation(), 1, config.global_concurrency)

        async def generate():
            actual = None
            pending = None
            stream = provider(value, key)
            deadline = time.monotonic() + 180
            try:
                while True:
                    if pending is None:
                        pending = asyncio.create_task(anext(stream))
                    done, _ = await asyncio.wait({pending}, timeout=0.5)
                    if time.monotonic() > deadline:
                        raise AppError("timeout", "Generation deadline exceeded.")
                    allowed = await asyncio.to_thread(ledger.status, user)
                    if not allowed["enabled"]:
                        raise AppError("disabled", "Operator stopped the service.")
                    if not done:
                        continue
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        break
                    pending = None
                    if event["type"] == "done" and event.get("usage"):
                        usage = event["usage"]
                        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")):
                            raise AppError("accounting", "Invalid provider usage.")
                        actual = config.cost(usage["input_tokens"], usage["output_tokens"])
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except asyncio.CancelledError:
                raise
            except Exception:
                yield '{"type":"error","code":"generation_stopped"}\n'
            finally:
                if pending:
                    pending.cancel()
                    try:
                        await pending
                    except (asyncio.CancelledError, Exception):
                        pass
                await stream.aclose()
                # A ledger failure leaves the reservation intact. Never refund on failure.
                try:
                    await asyncio.shield(asyncio.to_thread(ledger.settle, user, key_id, actual))
                except AppError:
                    pass
        return StreamingResponse(generate(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app
