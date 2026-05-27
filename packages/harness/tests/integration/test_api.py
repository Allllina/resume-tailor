"""Integration test for /api/tier1-tailor endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    """FastAPI TestClient with mocked LLM provider + isolated artifact dir."""
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    from harness.api.main import app
    return TestClient(app)


def _mock_llm():
    """Build a mock LLMProvider — duck-typed to satisfy the Protocol.

    Phase 2: returns sub-skill-shaped JSON per system prompt so the
    pipeline runs end-to-end instead of fail-fasting on the first
    sub-skill that gets garbage input. Tests that need specific
    sub-skill responses can override via keyword args."""
    from tests.integration._mocks import make_phase2_llm_mock
    return make_phase2_llm_mock()


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_tier1_tailor_rejects_invalid_input(client):
    """JD too short → 422 schema validation error."""
    r = client.post("/api/tier1-tailor", json={
        "mode": "manual",
        "jd": {"source": "paste", "raw_text": "short"},  # < 50 chars violates schema
        "candidate_profile_ref": "x",
        "target_market": "mainland-china",
    })
    assert r.status_code == 422


def test_tier1_tailor_rejects_invalid_mode(client):
    r = client.post("/api/tier1-tailor", json={
        "mode": "invalid_mode",
        "jd": {"source": "paste", "raw_text": "x" * 100},
        "candidate_profile_ref": "x",
        "target_market": "mainland-china",
    })
    assert r.status_code == 422


def test_tier1_tailor_happy_path(client, monkeypatch):
    """With valid input + mocked LLM, returns 200 with tier1 routing dict."""
    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post("/api/tier1-tailor", json={
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": "AIGC 内容实习生 招聘. " + "Prompt Agent LLM RAG 生成式 AI 工作流 " * 10},
            "candidate_profile_ref": "assets/profile/user-profile.md",
            "target_market": "mainland-china",
        })

    assert r.status_code == 200, r.text
    body = r.json()
    assert "run_id" in body
    assert "verdict" in body
    # W4 D.3: tier is now dynamic (assign_tier on resume_match_score). The
    # default experience-bank against an AIGC JD with C_product_ops lens
    # produces a low Pass C score → Tier 3. The point of this test is the
    # happy-path API contract, so we just assert tier is one of the three
    # valid values and lens routing landed correctly.
    # _REBASELINE_TODO (D11): tier_assigned may shift now that the active
    # experience-bank is the sample tree. Routing decision is keyword-driven
    # from JD text (AIGC/Agent/RAG) so primary_lens=C_product_ops should hold.
    # Controller verifies after running the suite once on sample data.
    assert body["tier_assigned"] in (1, 2, 3)
    assert body["lens_routing"]["primary_lens"] == "C_product_ops"
