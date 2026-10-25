"""Offline API fixture, copied ONLY into an isolated manual UI test installation.

The actual KiCad/wx UI, workers, parsing and SQLite remain real. Provider streams
and credential reads are synthetic. This file is excluded from release archives.
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("koa_real_worker", HERE / "_real_worker.py")
real_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_worker)

import httpx2
from openai import AsyncOpenAI
from kicad_open_assistant import credentials, transport
from kicad_open_assistant.policy import AppError

MODE_FILE = HERE / "fixture-mode.json"
mode = json.loads(MODE_FILE.read_text())["mode"]
credentials.read = lambda name: None if mode == "missing" else "synthetic-ui-fixture-only"

def no_credential_changes(*args):
    raise AppError("fixture", "Offline fixture does not read or change real credentials.")

credentials.write = credentials.delete = no_credential_changes
original_stream = transport.openai_stream

class Body(httpx2.AsyncByteStream):
    async def __aiter__(self):
        text = "[OFFLINE API FIXTURE] A 1 kOhm resistor at 1 mA has a 1 V drop by V = I R. Check actual ratings and circuit assumptions. "
        chunks = text.split(" ")
        for index, word in enumerate(chunks):
            await asyncio.sleep(0.25)
            yield ("data: " + json.dumps({"type": "response.output_text.delta", "sequence_number": index, "item_id": "fixture", "output_index": 0, "content_index": 0, "delta": word + " "}) + "\n\n").encode()
        event = {"type": "response.completed", "sequence_number": len(chunks), "response": {"id": "resp_fixture", "object": "response", "created_at": 0, "model": "gpt-4.1-mini", "status": "completed", "output": [], "usage": {"input_tokens": 50, "output_tokens": 40, "total_tokens": 90}}}
        yield ("data: " + json.dumps(event) + "\n\n").encode()

    async def aclose(self):
        pass

def handle(request):
    if mode == "network":
        raise httpx2.ConnectError("Synthetic offline network failure", request=request)
    if mode == "quota":
        return httpx2.Response(429, json={"error": {"message": "Synthetic capacity exhaustion", "type": "insufficient_quota"}})
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=Body())

async def mocked_stream(request, key):
    async with AsyncOpenAI(api_key="synthetic-ui-fixture-only", max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle))) as client:
        async for event in original_stream(request, "synthetic-ui-fixture-only", client):
            yield event

async def sponsored(request, endpoint, token, request_id):
    if mode == "quota":
        raise AppError("quota", "Your sponsored allowance is exhausted. You can choose personal mode.")
    async for event in mocked_stream(request, token):
        yield event

async def status(endpoint, token):
    return {"enabled": mode != "quota", "remaining_microdollars": 0 if mode == "quota" else 1_000_000, "model": "gpt-4.1-mini-2025-04-14", "max_output_tokens": 64}

transport.openai_stream = mocked_stream
transport.sponsored_stream = sponsored
transport.sponsored_status = status
if __name__ == "__main__":
    real_worker.main()
