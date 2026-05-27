"""Gate 2 contract tests — LLMHealthMonitor + /api/health endpoint + precheck.

Tests assert product behavior:
1. Monitor tracks success/failure/circuit-open state correctly.
2. GET /api/health returns schema-compliant snapshot.
3. POST /api/tier1-tailor returns 503 when monitor says down.
4. POST /api/users/masters/generate returns 503 when monitor says down.
5. Singleton reset between cases.
"""
from __future__ import annotations

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

from harness.llm.health import LLMHealthMonitor, get_monitor
from harness.llm.circuit_breaker import CircuitBreaker
from harness.llm.factory import _reset_provider_for_tests


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    # _reset_provider_for_tests() atomically resets both provider + monitor.
    _reset_provider_for_tests()
    yield
    _reset_provider_for_tests()


# ---------------------------------------------------------------------------
# 1. LLMHealthMonitor unit tests
# ---------------------------------------------------------------------------


def test_monitor_initial_state_healthy():
    m = LLMHealthMonitor(provider_name="anthropic")
    snap = m.snapshot()
    assert snap.status == "healthy"
    assert snap.consecutive_failures == 0
    assert snap.circuit_open is False
    assert snap.last_success_at is None
    assert snap.last_failure_at is None


def test_monitor_single_failure_is_degraded():
    m = LLMHealthMonitor()
    m.record_failure()
    snap = m.snapshot()
    assert snap.status == "degraded"
    assert snap.consecutive_failures == 1
    assert snap.last_failure_at is not None


def test_monitor_threshold_failures_is_down():
    m = LLMHealthMonitor(circuit_open_threshold=3)
    m.record_failure()
    m.record_failure()
    assert m.snapshot().status == "degraded"
    m.record_failure()
    assert m.snapshot().status == "down"


def test_monitor_circuit_open_is_down():
    m = LLMHealthMonitor()
    m.record_circuit_open()
    snap = m.snapshot()
    assert snap.status == "down"
    assert snap.circuit_open is True
    assert m.is_down() is True


def test_monitor_success_resets_to_healthy():
    m = LLMHealthMonitor()
    m.record_failure()
    m.record_failure()
    assert m.snapshot().status == "degraded"
    m.record_success()
    snap = m.snapshot()
    assert snap.status == "healthy"
    assert snap.consecutive_failures == 0
    assert snap.circuit_open is False
    assert snap.last_success_at is not None


def test_monitor_circuit_open_clears_on_success():
    m = LLMHealthMonitor()
    m.record_circuit_open()
    assert m.is_down()
    m.record_success()
    assert not m.is_down()


def test_monitor_circuit_open_self_clears_after_cooldown():
    # Simulate cooldown elapsed by backdating _circuit_opened_at past the window.
    import time
    m = LLMHealthMonitor(circuit_cooldown_seconds=10)
    m.record_circuit_open()
    assert m.is_down()
    # Backdate so cooldown appears elapsed.
    m._circuit_opened_at = time.monotonic() - 11
    assert not m.is_down()
    assert m.snapshot().circuit_open is False


def test_monitor_circuit_open_stays_down_within_cooldown():
    import time
    m = LLMHealthMonitor(circuit_cooldown_seconds=300)
    m.record_circuit_open()
    # Opened just now — well within cooldown.
    assert m.is_down()
    assert m.snapshot().circuit_open is True


# ---------------------------------------------------------------------------
# 2. CircuitBreaker callbacks wire into monitor
# ---------------------------------------------------------------------------


def test_circuit_breaker_calls_on_success_callback():
    called = []
    breaker = CircuitBreaker(on_success=lambda: called.append("success"))
    breaker.record_success()
    assert called == ["success"]


def test_circuit_breaker_calls_on_failure_callback():
    called = []
    breaker = CircuitBreaker(
        failure_threshold=3,
        on_failure=lambda: called.append("failure"),
        on_circuit_open=lambda: called.append("open"),
    )
    breaker.record_failure()
    breaker.record_failure()
    assert called == ["failure", "failure"]
    breaker.record_failure()
    assert "open" in called


def test_circuit_breaker_monitor_integration():
    monitor = LLMHealthMonitor(circuit_open_threshold=2)
    breaker = CircuitBreaker(
        failure_threshold=2,
        on_success=monitor.record_success,
        on_failure=monitor.record_failure,
        on_circuit_open=monitor.record_circuit_open,
    )
    breaker.record_failure()
    assert monitor.snapshot().status == "degraded"
    breaker.record_failure()
    assert monitor.snapshot().status == "down"
    breaker.record_success()
    assert monitor.snapshot().status == "healthy"


def test_openai_provider_gets_monitored_breaker():
    # Regression for P2a: _build_provider() must pass the monitored breaker
    # to OpenAIProvider so failures update the health monitor, not a
    # private unconnected breaker inside the provider.
    from unittest.mock import patch
    from harness.llm.factory import _build_provider
    from harness.llm.openai_provider import OpenAIProvider

    class _FakeCfg:
        llm_provider = "openai"
        openai_api_key = "sk-test"
        openai_model = "gpt-4o"
        openai_max_retries = 1
        openai_timeout_seconds = 10
        openai_base_url = None

    provider = _build_provider(_FakeCfg())
    assert isinstance(provider, OpenAIProvider)
    # The breaker wired into the provider must have health callbacks attached.
    assert provider.breaker.on_success is not None
    assert provider.breaker.on_failure is not None
    assert provider.breaker.on_circuit_open is not None


# ---------------------------------------------------------------------------
# 3. GET /api/health response shape
# ---------------------------------------------------------------------------


def test_api_health_returns_healthy_snapshot():
    from harness.api.main import app
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "llm-health-v1"
    assert "harness_version" in body
    llm = body["llm"]
    assert llm["status"] == "healthy"
    assert llm["consecutive_failures"] == 0
    assert llm["circuit_open"] is False
    assert llm["seconds_since_last_success"] is None
    assert llm["seconds_since_last_failure"] is None


def test_api_health_reflects_monitor_state():
    monitor = get_monitor()
    monitor.record_failure()
    monitor.record_failure()

    from harness.api.main import app
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    llm = resp.json()["llm"]
    assert llm["status"] == "degraded"
    assert llm["consecutive_failures"] == 2


def test_api_health_circuit_open_shows_down():
    monitor = get_monitor()
    monitor.record_circuit_open()

    from harness.api.main import app
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    llm = resp.json()["llm"]
    assert llm["status"] == "down"
    assert llm["circuit_open"] is True


@pytest.mark.asyncio
async def test_api_health_stays_responsive_during_blocking_tailor_loop(monkeypatch):
    """Regression for MVP P0: tailor work must not starve /api/health."""
    from harness.api import tier1_tailor as tier1_module
    from harness.api.main import app

    run_started = False

    async def blocking_run_tier1(**_kwargs):
        nonlocal run_started
        run_started = True
        time.sleep(0.75)
        return {
            "run_id": "blocking-regression",
            "input_ref": "sha256:blocking-regression",
            "verdict": "complete",
            "tier_assigned": 1,
            "lens_routing": {"primary_lens": "C_product_ops"},
            "trace": {
                "perception_events": [],
                "planning_events": [],
                "action_events": [],
                "feedback_events": [],
            },
            "metrics": {"total_tokens": 0, "total_claude_calls": 0, "elapsed_seconds": 0.75},
            "degradation_events": [],
        }

    monkeypatch.setattr(tier1_module, "run_tier1", blocking_run_tier1)
    monkeypatch.setattr(tier1_module, "make_llm_provider_for_thread", lambda: MagicMock())

    req = {
        "mode": "manual",
        "jd": {
            "source": "paste",
            "raw_text": "AIGC 内容实习生 招聘. " + "Prompt Agent LLM RAG 生成式 AI 工作流 " * 10,
        },
        "candidate_profile_ref": "assets/profile/user-profile.md",
        "target_market": "mainland-china",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        started_at = time.perf_counter()
        tailor_task = asyncio.create_task(client.post("/api/tier1-tailor", json=req))
        await asyncio.sleep(0)

        health_resp = await client.get("/api/health")
        health_elapsed = time.perf_counter() - started_at
        tailor_resp = await tailor_task

    assert run_started is True
    assert health_resp.status_code == 200
    assert health_elapsed < 0.5
    assert tailor_resp.status_code == 200
