"""Private local pipe worker. This file is an entry point, not a network service."""
from pathlib import Path
import sys

root = Path(__file__).resolve()
sys.path.insert(0, str(root.parents[1]))
sys.path.insert(0, str(root.parents[2] / "vendor"))

import asyncio
import json
import time
import warnings
import logging

from kicad_open_assistant.policy import AppError, MAX_BODY, validate_request
from kicad_open_assistant.storage import Store


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


async def dispatch(command):
    action = command["action"]
    if action == "extract":
        from kicad_open_assistant.attachments import extract
        emit({"type": "result", "value": extract(command["path"])})
        return
    store = Store()
    if action == "load":
        rows = store.list()
        if not rows:
            store.create()
            rows = store.list()
        identifier = command.get("conversation") or rows[0]["id"]
        if command.get("recover"):
            store.interrupt(identifier)
        emit({"type": "result", "value": {"conversations": rows, "messages": store.messages(identifier), "selected": identifier, "settings": store.settings()}})
    elif action == "create":
        emit({"type": "result", "value": store.create()})
    elif action == "rename":
        store.rename(command["conversation"], command["title"])
        emit({"type": "result", "value": True})
    elif action == "delete":
        store.delete(command["conversation"])
        emit({"type": "result", "value": True})
    elif action == "settings":
        from kicad_open_assistant.credentials import write, delete, target
        settings = command["settings"]
        if settings["mode"] == "sponsored":
            from kicad_open_assistant.transport import sponsored_url
            sponsored_url(settings["endpoint"])
        if command.get("forget"):
            delete(target(settings["mode"], settings.get("endpoint", "")))
        elif command.get("credential"):
            write(target(settings["mode"], settings.get("endpoint", "")), command["credential"])
        store.save_settings(settings)
        emit({"type": "result", "value": True})
    elif action == "status":
        from kicad_open_assistant.credentials import read, target
        from kicad_open_assistant.transport import sponsored_status
        settings = command["settings"]
        result = await sponsored_status(settings["endpoint"], read(target("sponsored", settings["endpoint"])))
        emit({"type": "result", "value": result})
    elif action == "chat":
        from kicad_open_assistant.credentials import read, target
        from kicad_open_assistant.transport import openai_stream, sponsored_stream
        request = validate_request(command["request"])
        settings = command["settings"]
        secret = read(target(settings["mode"], settings.get("endpoint", "")))
        if not secret:
            raise AppError("missing_credentials", "No credential saved for this connection. Open Connection settings; your key or access token stays in Windows Credential Manager.")
        conversation = command["conversation"]
        user_id = store.add(conversation, "user", request["input"][-1]["content"])
        reply = store.add(conversation, "assistant", [{"type": "input_text", "text": ""}], "streaming")
        emit({"type": "started", "reply_id": reply, "user_id": user_id})
        stream = openai_stream(request, secret) if settings["mode"] == "personal" else sponsored_stream(request, settings["endpoint"], secret, command["request_id"])
        answer, status, checkpoint = "", "failed", time.monotonic()
        buffered, painted = "", time.monotonic()
        try:
            async with asyncio.timeout(180):
                async for event in stream:
                    if event["type"] == "delta":
                        answer += event["text"]
                        buffered += event["text"]
                        if len(answer) > 250_000:
                            raise AppError("output_limit", "Response exceeded the local display limit.")
                        if time.monotonic() - checkpoint > 0.5:
                            store.finish(reply, answer, "streaming")
                            checkpoint = time.monotonic()
                        if time.monotonic() - painted >= 0.04:
                            emit({"type": "delta", "text": buffered})
                            buffered, painted = "", time.monotonic()
                    elif event["type"] == "done":
                        status = event["status"]
                        if buffered:
                            emit({"type": "delta", "text": buffered})
                            buffered = ""
                        emit(event)
        finally:
            if buffered:
                emit({"type": "delta", "text": buffered})
            await stream.aclose()
            store.finish(reply, answer, status)
    elif action == "recover":
        store.interrupt(command["conversation"])
        emit({"type": "result", "value": True})
    elif action == "finish":
        store.finish(command["reply_id"], command["text"], command["status"])
        emit({"type": "result", "value": True})
    else:
        raise AppError("operation", "Unsupported local operation.")


def main():
    # Parser/SDK diagnostics may contain document fragments. Suppress them; only
    # allowlisted application errors cross the pipe. No stderr is persisted.
    logging.disable(logging.CRITICAL)
    warnings.simplefilter("ignore")
    try:
        blob = sys.stdin.buffer.read(MAX_BODY + 4096)
        if len(blob) >= MAX_BODY + 4096:
            raise AppError("limit", "Local request is too large.")
        asyncio.run(dispatch(json.loads(blob)))
    except AppError as error:
        emit({"type": "error", "code": error.code, "message": error.message})
    except TimeoutError:
        emit({"type": "error", "code": "timeout", "message": "Operation timed out; partial output is preserved."})
    except Exception:
        emit({"type": "error", "code": "local", "message": "Local operation failed. Check storage permissions, dependencies and the selected file."})


if __name__ == "__main__":
    main()
