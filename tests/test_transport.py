from types import SimpleNamespace
import asyncio
import pytest
from kicad_open_assistant.policy import AppError, make_request
from kicad_open_assistant.transport import openai_stream, sponsored_url


class Stream:
    closed = False
    def __init__(self, events):
        self.events = events
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        self.closed = True
    def __aiter__(self):
        return self.iterate()
    async def iterate(self):
        for event in self.events:
            yield event


@pytest.mark.asyncio
async def test_actual_request_policy_and_typed_stream():
    captured = {}
    stream = Stream([SimpleNamespace(type="response.output_text.delta", delta="answer"), SimpleNamespace(type="response.completed", response=SimpleNamespace(usage=SimpleNamespace(input_tokens=20, output_tokens=3)))])
    async def create(**kwargs):
        captured.update(kwargs)
        return stream
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    events = [e async for e in openai_stream(make_request("gpt-4.1-mini", "Hello", [], []), "test-only", client)]
    assert events[0]["text"] == "answer" and events[-1]["usage"]["output_tokens"] == 3
    assert captured["store"] is False and captured["stream"] is True and "tools" not in captured
    assert stream.closed


@pytest.mark.asyncio
async def test_disconnect_is_failure_not_completion():
    stream = Stream([SimpleNamespace(type="response.output_text.delta", delta="partial")])
    async def create(**kwargs):
        return stream
    with pytest.raises(AppError, match="before completion"):
        async for _ in openai_stream(make_request("gpt-4.1-mini", "Hello", [], []), "test-only", SimpleNamespace(responses=SimpleNamespace(create=create))):
            pass
    assert stream.closed


def test_tls_endpoint_policy():
    for endpoint in ("http://localhost:8000", "https://user:key@example.com", "https://example.com?key=secret", "file:///secret"):
        with pytest.raises(AppError):
            sponsored_url(endpoint)
    assert sponsored_url("https://assistant.example.org/") == "https://assistant.example.org"


@pytest.mark.asyncio
async def test_installed_sdk_against_mocked_http_stream():
    import json
    import httpx2
    from openai import AsyncOpenAI
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        completed = {"type": "response.completed", "sequence_number": 2, "response": {"id": "resp_fixture", "object": "response", "created_at": 0, "model": "gpt-4.1-mini", "status": "completed", "output": [], "usage": {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11}}}
        events = [{"type": "response.output_text.delta", "sequence_number": 1, "item_id": "msg_fixture", "output_index": 0, "content_index": 0, "delta": "OK"}, completed]
        body = "".join("data: " + json.dumps(e) + "\n\n" for e in events)
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, text=body)
    async with AsyncOpenAI(api_key="synthetic-test-only", max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle))) as client:
        events = [e async for e in openai_stream(make_request("gpt-4.1-mini", "Hello", [], []), "synthetic", client)]
    assert events[0]["text"] == "OK" and events[-1]["usage"]["input_tokens"] == 10
    assert len(requests) == 1 and requests[0]["store"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expected", [(401, "authentication"), (403, "permission"), (404, "model_or_request"), (429, "quota"), (500, "service")])
async def test_sdk_errors_are_safe_and_not_retried(status, expected):
    import httpx2
    from openai import AsyncOpenAI
    calls = []
    def handle(request):
        calls.append(request)
        return httpx2.Response(status, json={"error": {"message": "PRIVATE PROVIDER DETAIL", "type": "test_error"}})
    async with AsyncOpenAI(api_key="synthetic-test-only", max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle))) as client:
        with pytest.raises(AppError) as caught:
            async for _ in openai_stream(make_request("gpt-4.1-mini", "Hello", [], []), "synthetic", client):
                pass
    assert caught.value.code == expected and "PRIVATE" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_sdk_network_failure_is_safe():
    import httpx2
    from openai import AsyncOpenAI
    def handle(request):
        raise httpx2.ConnectError("PRIVATE NETWORK DETAIL", request=request)
    async with AsyncOpenAI(api_key="synthetic-test-only", max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle))) as client:
        with pytest.raises(AppError) as caught:
            async for _ in openai_stream(make_request("gpt-4.1-mini", "Hello", [], []), "synthetic", client):
                pass
    assert caught.value.code == "network" and "PRIVATE" not in str(caught.value)
