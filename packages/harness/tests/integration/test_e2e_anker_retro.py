"""E2E retro-test: reproduce v0.3.3 Anker AIGC routing via Wave 1 API.

Locks the v0.3.3 → v0.4.0 invariant. The manual tailoring done at
commit e0b358d routed Anker AIGC JD to C_product_ops + ai-innovation.
If this test breaks, lens routing has drifted — investigate before merge.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    from harness.api.main import app
    return TestClient(app)


def _mock_llm():
    """Mock LLMProvider returning a generic non-routing response.

    Lens routing for the Anker JD is deterministic (≥3 keyword hits)
    so no LLM call is made for routing. Phase 2 needs every sub-skill
    to receive a sub-skill-shaped response or it fail-fasts; the smart
    mock handles all critical sub-skills.
    """
    from tests.integration._mocks import make_phase2_llm_mock
    return make_phase2_llm_mock()


@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
def test_anker_aigc_routes_to_C_product_ops(client):
    jd_text = (FIXTURES / "jd_anker_aigc.txt").read_text()
    expected = json.loads((FIXTURES / "expected_anker_routing.json").read_text())

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post("/api/tier1-tailor", json={
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": jd_text},
            "candidate_profile_ref": "assets/profile/user-profile.md",
            "target_market": "mainland-china",
        })

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lens_routing"]["primary_lens"] == expected["primary_lens"], (
        f"Lens routing drift: expected {expected['primary_lens']}, got "
        f"{body['lens_routing']['primary_lens']}. Anker AIGC JD has 5+ AIGC/Agent/Prompt keywords."
    )
    assert body["matched_resume_version"] == expected["matched_resume_version"]
    assert body["tier_assigned"] == expected["tier_assigned"]
    assert body["verdict"] == expected["verdict"]
    assert body["lens_routing"]["used_llm_fallback"] == expected["lens_routing_used_llm_fallback"]


def test_anker_aigc_scenario_is_ai_innovation(client):
    jd_text = (FIXTURES / "jd_anker_aigc.txt").read_text()

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post("/api/tier1-tailor", json={
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": jd_text},
            "candidate_profile_ref": "assets/profile/user-profile.md",
            "target_market": "mainland-china",
        })

    body = r.json()
    assert body["lens_routing"]["scenario"] == "ai-innovation"


def test_anker_aigc_produces_tex_artifact(client):
    """End-to-end: artifact file exists at the path returned in output."""
    jd_text = (FIXTURES / "jd_anker_aigc.txt").read_text()

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post("/api/tier1-tailor", json={
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": jd_text},
            "candidate_profile_ref": "assets/profile/user-profile.md",
            "target_market": "mainland-china",
        })

    body = r.json()
    assert body.get("tex_artifact_path"), "No tex_artifact_path returned"
    assert Path(body["tex_artifact_path"]).exists(), "Tex artifact file missing on disk"


def test_anker_aigc_lens_routing_deterministic(client):
    """The Anker JD must route deterministically (≥3 keyword hits) — no LLM fallback."""
    jd_text = (FIXTURES / "jd_anker_aigc.txt").read_text()

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post("/api/tier1-tailor", json={
            "mode": "manual",
            "jd": {"source": "paste", "raw_text": jd_text},
            "candidate_profile_ref": "assets/profile/user-profile.md",
            "target_market": "mainland-china",
        })

    body = r.json()
    assert body["lens_routing"]["used_llm_fallback"] is False
