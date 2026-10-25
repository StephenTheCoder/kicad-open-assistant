import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import uuid
import httpx
import pytest
from kicad_open_assistant.policy import AppError, DEFAULT_MODEL, make_request
from kicad_open_assistant.service.app import Config, create_app
from kicad_open_assistant.service.ledger import Ledger


def setup_ledger(tmp_path, budget=1_000_000):
    ledger = Ledger(tmp_path / "ledger.db")
    ledger.initialize()
    ledger.configure(budget, True)
    return ledger


def test_atomic_budget_under_concurrency_and_replay(tmp_path):
    ledger = setup_ledger(tmp_path, 1000)
    for i in range(24):
        ledger.issue(str(i), 1000)
    def attempt(i):
        try:
            Ledger(ledger.path).reserve(str(i), str(i), 300, global_concurrency=100)
            return True
        except AppError as error:
            assert error.code == "budget"
            return False
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(attempt, range(24)))
    assert sum(results) == 3
    assert ledger.status("0")["remaining_microdollars"] == 100


def test_unknown_usage_quota_revocation_and_kill(tmp_path):
    ledger = setup_ledger(tmp_path, 1000)
    token = ledger.issue("alice", 600)
    assert ledger.authenticate(token) == "alice"
    ledger.reserve("alice", "first", 500)
    with pytest.raises(AppError, match="Concurrency"):
        ledger.reserve("alice", "second", 500)
    ledger.settle("alice", "first", None)
    assert ledger.status("alice")["remaining_microdollars"] == 100
    with pytest.raises(AppError) as duplicate:
        ledger.reserve("alice", "first", 10)
    assert duplicate.value.code == "duplicate"
    with pytest.raises(AppError) as quota:
        ledger.reserve("alice", "new", 500)
    assert quota.value.code == "quota"
    ledger.revoke("alice")
    with pytest.raises(AppError) as revoked:
        ledger.authenticate(token)
    assert revoked.value.code == "revoked"
    ledger.kill()
    ledger.issue("bob", 1000)
    with pytest.raises(AppError) as disabled:
        ledger.reserve("bob", "b", 100)
    assert disabled.value.code == "disabled"
    assert token.encode() not in ledger.path.read_bytes()


def test_accounting_missing_and_underreservation_fail_closed(tmp_path):
    ledger = Ledger(tmp_path / "missing" / "db")
    with pytest.raises(AppError) as unavailable:
        ledger.reserve("a", "r", 100)
    assert unavailable.value.code == "accounting"
    ledger = setup_ledger(tmp_path)
    ledger.issue("a", 1_000_000)
    ledger.reserve("a", "r", 100)
    ledger.settle("a", "r", 101)
    assert not ledger.status("a")["enabled"]


@pytest.mark.asyncio
async def test_http_auth_policy_user_isolation_and_secret_exclusion(tmp_path):
    secret = "test-only-server-secret-do-not-expose"
    secret_file = tmp_path / "secret"
    secret_file.write_text(secret)
    calls = []
    async def provider(request, key):
        assert key == secret
        calls.append(request)
        yield {"type": "delta", "text": "A resistor limits current."}
        yield {"type": "done", "status": "completed", "usage": {"input_tokens": 100, "output_tokens": 10}}
    config = Config(str(tmp_path / "db"), True, str(secret_file), price_valid_until="2099-01-01")
    app = create_app(config, provider)
    ledger = app.state.ledger
    ledger.initialize()
    ledger.configure(2_000_000, True)
    alice, bob = ledger.issue("a", 1_000_000), ledger.issue("b", 1_000_000)
    request = make_request(DEFAULT_MODEL, "Resistors?", [], [])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        assert (await client.post("/v1/chat", json=request)).status_code == 401
        headers = {"Authorization": "Bearer " + alice, "Idempotency-Key": uuid.uuid4().hex}
        assert (await client.post("/v1/chat", json={**request, "tools": []}, headers=headers)).status_code == 400
        assert (await client.post("/v1/chat", json={**request, "model": "arbitrary-model"}, headers=headers)).status_code == 400
        response = await client.post("/v1/chat", json=request, headers=headers)
        assert response.status_code == 200 and "resistor" in response.text
        assert secret not in response.text and alice not in response.text
        assert (await client.post("/v1/chat", json=request, headers=headers)).status_code == 409
        status_b = await client.get("/v1/status", headers={"Authorization": "Bearer " + bob})
        assert status_b.json()["remaining_microdollars"] == 1_000_000
        ledger.revoke("a")
        assert (await client.get("/v1/status", headers={"Authorization": "Bearer " + alice})).status_code == 403
        assert len(calls) == 1
    # Request bodies, server key, tokens and answers are absent from accounting DB.
    for path in tmp_path.glob("db*"):
        blob = path.read_bytes()
        assert secret.encode() not in blob and b"Resistors?" not in blob and alice.encode() not in blob


@pytest.mark.asyncio
async def test_disabled_service_never_calls_provider(tmp_path):
    async def forbidden(request, key):
        raise AssertionError("must not call provider")
        yield
    app = create_app(Config(str(tmp_path / "db")), forbidden)
    app.state.ledger.initialize()
    token = app.state.ledger.issue("a", 10_000_000)
    app.state.ledger.configure(10_000_000, True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post("/v1/chat", json=make_request(DEFAULT_MODEL, "Hello", [], []), headers={"Authorization": "Bearer " + token, "Idempotency-Key": uuid.uuid4().hex})
        assert response.status_code == 503 and response.headers["X-KOA-Error"] == "disabled"


def test_rate_limits_and_rotation_do_not_reset_ledger(tmp_path):
    ledger = setup_ledger(tmp_path)
    token = ledger.issue("a", 1000)
    ledger.reserve("a", "r", 500)
    ledger.settle("a", "r", 200)
    replacement = ledger.issue("a", 1000)
    with pytest.raises(AppError):
        ledger.authenticate(token)
    assert ledger.authenticate(replacement) == "a"
    assert ledger.status("a")["remaining_microdollars"] == 800
    ledger.attempt("peer", 1)
    with pytest.raises(AppError) as limited:
        ledger.attempt("peer", 1)
    assert limited.value.code == "rate"


@pytest.mark.asyncio
async def test_kill_switch_interrupts_and_retains_unknown_cost(tmp_path):
    secret = tmp_path / "key"
    secret.write_text("synthetic-server-test")
    started, closed = asyncio.Event(), asyncio.Event()
    async def provider(request, key):
        try:
            started.set()
            await asyncio.sleep(60)
            yield {"type": "delta", "text": "must not reach client"}
        finally:
            closed.set()
    config = Config(str(tmp_path / "db"), True, str(secret), price_valid_until="2099-01-01")
    app = create_app(config, provider)
    ledger = app.state.ledger
    ledger.initialize()
    ledger.configure(1_000_000, True)
    token = ledger.issue("user", 1_000_000)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        task = asyncio.create_task(client.post("/v1/chat", json=make_request(DEFAULT_MODEL, "Hello", [], []), headers={"Authorization": "Bearer " + token, "Idempotency-Key": uuid.uuid4().hex}))
        await asyncio.wait_for(started.wait(), 3)
        ledger.kill()
        response = await asyncio.wait_for(task, 3)
        assert "generation_stopped" in response.text and "must not reach client" not in response.text
        assert closed.is_set()
    assert ledger.status("user")["remaining_microdollars"] == 1_000_000 - config.reservation()


@pytest.mark.asyncio
async def test_http_disconnect_keeps_reservation(tmp_path):
    secret = tmp_path / "key"
    secret.write_text("synthetic-server-test")
    started = asyncio.Event()
    async def provider(request, key):
        started.set()
        await asyncio.sleep(60)
        yield
    config = Config(str(tmp_path / "db"), True, str(secret), price_valid_until="2099-01-01")
    app = create_app(config, provider)
    ledger = app.state.ledger
    ledger.initialize()
    ledger.configure(1_000_000, True)
    token = ledger.issue("user", 1_000_000)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        task = asyncio.create_task(client.post("/v1/chat", json=make_request(DEFAULT_MODEL, "Hello", [], []), headers={"Authorization": "Bearer " + token, "Idempotency-Key": uuid.uuid4().hex}))
        await asyncio.wait_for(started.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.05)
    assert ledger.status("user")["remaining_microdollars"] == 1_000_000 - config.reservation()
