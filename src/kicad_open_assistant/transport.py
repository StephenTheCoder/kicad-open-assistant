"""Foreground Responses streaming; TLS verified, no tools, no automatic retry."""
import asyncio
import json
from urllib.parse import urlsplit
from .policy import AppError, INSTRUCTIONS, validate_request


def error_for(error):
    status = getattr(error, "status_code", getattr(getattr(error, "response", None), "status_code", None))
    name = type(error).__name__
    if status == 401:
        return AppError("authentication", "Credential rejected. Update it in Connection settings.")
    if status == 403:
        return AppError("permission", "This account lacks access to the selected model or service.")
    if status == 429:
        return AppError("quota", "Rate or usage allowance exhausted. Wait, or check the account's billing and limits.")
    if status in (400, 404, 422):
        return AppError("model_or_request", "Model or request is unsupported. Check the configured model's Responses and image compatibility.")
    if "Timeout" in name:
        return AppError("timeout", "Connection timed out. Partial output is preserved; retry is a new request.")
    if "Connection" in name or "Connect" in name:
        return AppError("network", "Cannot connect securely. Check network access and certificates.")
    return AppError("service", "The service failed. Partial output is preserved; no automatic retry was made.")


async def openai_stream(request, key, client=None):
    validate_request(request)
    if not key:
        raise AppError("missing_credentials", "No personal OpenAI key is saved. Add it in Connection settings.")
    from openai import AsyncOpenAI
    owned = client is None
    if owned:
        import httpx2
        client = AsyncOpenAI(api_key=key, base_url="https://api.openai.com/v1", max_retries=0, timeout=45.0,
                             http_client=httpx2.AsyncClient(verify=True, trust_env=False, follow_redirects=False, timeout=45.0))
    try:
        stream = await client.responses.create(**request, instructions=INSTRUCTIONS, store=False, stream=True)
        terminal = False
        async with stream:
            async for event in stream:
                if event.type in ("response.output_text.delta", "response.refusal.delta"):
                    yield {"type": "delta", "text": event.delta}
                elif event.type in ("response.completed", "response.incomplete"):
                    terminal = True
                    usage = event.response.usage
                    yield {"type": "done", "status": "completed" if event.type == "response.completed" else "incomplete",
                           "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens} if usage else None}
                elif event.type in ("error", "response.failed"):
                    raise AppError("service", "OpenAI could not complete the response. No automatic retry was made.")
        if not terminal:
            raise AppError("interrupted", "The stream ended before completion. Partial output is preserved.")
    except (AppError, asyncio.CancelledError):
        raise
    except Exception as error:
        raise error_for(error) from None
    finally:
        if owned:
            await client.close()


def sponsored_url(endpoint):
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise AppError("endpoint", "Sponsored service requires an HTTPS address without credentials or query parameters.")
    return endpoint.rstrip("/")


async def sponsored_status(endpoint, token):
    import httpx
    if not token:
        raise AppError("missing_credentials", "Sign in with an administrator-issued sponsored access token in Connection settings.")
    try:
        async with httpx.AsyncClient(verify=True, trust_env=False, timeout=15, follow_redirects=False) as client:
            response = await client.get(sponsored_url(endpoint) + "/v1/status", headers={"Authorization": "Bearer " + token})
            response.raise_for_status()
            return response.json()
    except AppError:
        raise
    except Exception as error:
        raise error_for(error) from None


async def sponsored_stream(request, endpoint, token, request_id):
    import httpx
    validate_request(request)
    if not token:
        raise AppError("missing_credentials", "No sponsored access token saved. Sign in in Connection settings or choose personal mode.")
    try:
        async with httpx.AsyncClient(verify=True, trust_env=False, timeout=45, follow_redirects=False) as client:
            async with client.stream("POST", sponsored_url(endpoint) + "/v1/chat", headers={"Authorization": "Bearer " + token, "Idempotency-Key": request_id}, json=request) as response:
                if response.status_code != 200:
                    # Bounded, allowlisted service error codes, never echo server bodies.
                    code = response.headers.get("X-KOA-Error", "")
                    if code in {"disabled", "budget", "quota", "concurrency", "rate", "revoked", "accounting", "duplicate", "configuration"}:
                        raise AppError(code, {"disabled": "Sponsored access is disabled. Choose personal mode or contact the operator.", "budget": "Sponsored capacity is exhausted. You can choose personal mode.", "quota": "Your sponsored allowance is exhausted. You can choose personal mode.", "concurrency": "A sponsored request is already active. Wait before retrying.", "rate": "Too many sponsored requests. Wait a minute before retrying.", "revoked": "Sponsored access was revoked. Contact the operator.", "accounting": "Sponsored accounting is unavailable; requests are safely disabled.", "duplicate": "This request was already accepted; it will not be charged again.", "configuration": "Sponsored service configuration needs operator attention."}[code])
                    response.raise_for_status()
                terminal = False
                async for line in response.aiter_lines():
                    if len(line) > 128_000:
                        raise AppError("service", "Service event exceeds the size limit.")
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("type") == "delta" and isinstance(event.get("text"), str):
                        yield {"type": "delta", "text": event["text"]}
                    elif event.get("type") == "done":
                        terminal = True
                        yield {"type": "done", "status": event.get("status", "completed"), "usage": event.get("usage")}
                    elif event.get("type") == "error":
                        raise AppError("service", "Sponsored generation stopped. Partial output is preserved; contact the operator if this repeats.")
                if not terminal:
                    raise AppError("interrupted", "Sponsored connection ended before completion.")
    except (AppError, asyncio.CancelledError):
        raise
    except Exception as error:
        raise error_for(error) from None
