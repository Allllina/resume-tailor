"""Integration tests for POST /api/users/lens-targets (Wave 4 C.1.4)."""
from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


def _mock_llm():
    p = MagicMock()
    p.call = AsyncMock(return_value=json.dumps({"recognition_per_industry": {}}))
    return p


@pytest.fixture
def isolated_root(monkeypatch, tmp_path):
    fake_root = tmp_path
    (fake_root / "packages/harness/data/users").mkdir(parents=True, exist_ok=True)
    from harness.config import config
    monkeypatch.setattr(config, "repo_root", fake_root)
    return fake_root


@pytest.fixture
def client(monkeypatch, isolated_root):
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    import harness.api.users as users_module
    monkeypatch.setattr(users_module, "get_llm_provider", _mock_llm)
    from harness.api.main import app
    return TestClient(app)


def test_post_lens_targets_happy(client, isolated_root):
    r = client.post(
        "/api/users/lens-targets",
        json={"primary": "C_product_ops", "secondary": ["B_data_analytics"]},
        headers={"X-User-Id": "u-lt-happy"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["primary"] == "C_product_ops"
    assert body["secondary"] == ["B_data_analytics"]
    # profile.json reflects it
    profile_path = (
        isolated_root / "packages/harness/data/users/u-lt-happy/profile.json"
    )
    profile = json.loads(profile_path.read_text())
    assert profile["target_lens_default"] == "C_product_ops"
    assert profile["target_lens_secondary"] == ["B_data_analytics"]


def test_post_lens_targets_rejects_invalid_lens(client):
    r = client.post(
        "/api/users/lens-targets",
        json={"primary": "Z_made_up", "secondary": []},
        headers={"X-User-Id": "u-lt-bad"},
    )
    assert r.status_code == 422


def test_post_lens_targets_rejects_invalid_secondary(client):
    r = client.post(
        "/api/users/lens-targets",
        json={"primary": "A_strategy_research", "secondary": ["Z_made_up"]},
        headers={"X-User-Id": "u-lt-bad-sec"},
    )
    assert r.status_code == 422


def test_post_lens_targets_rejects_primary_in_secondary(client):
    r = client.post(
        "/api/users/lens-targets",
        json={
            "primary": "C_product_ops",
            "secondary": ["C_product_ops", "B_data_analytics"],
        },
        headers={"X-User-Id": "u-lt-overlap"},
    )
    assert r.status_code == 422


def test_post_lens_targets_idempotent(client, isolated_root):
    body = {"primary": "A_strategy_research", "secondary": ["C_product_ops"]}
    r1 = client.post(
        "/api/users/lens-targets",
        json=body,
        headers={"X-User-Id": "u-lt-idem"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/users/lens-targets",
        json=body,
        headers={"X-User-Id": "u-lt-idem"},
    )
    assert r2.status_code == 200
    profile_path = (
        isolated_root / "packages/harness/data/users/u-lt-idem/profile.json"
    )
    profile = json.loads(profile_path.read_text())
    assert profile["target_lens_default"] == "A_strategy_research"
    assert profile["target_lens_secondary"] == ["C_product_ops"]


def test_get_me_reflects_lens_targets(client):
    client.post(
        "/api/users/lens-targets",
        json={
            "primary": "B_data_analytics",
            "secondary": ["A_strategy_research"],
        },
        headers={"X-User-Id": "u-lt-me"},
    )
    r = client.get("/api/users/me", headers={"X-User-Id": "u-lt-me"})
    assert r.status_code == 200
    profile = r.json()["profile"]
    assert profile["target_lens_default"] == "B_data_analytics"
    assert profile["target_lens_secondary"] == ["A_strategy_research"]


def test_post_lens_targets_secondary_dedup(client, isolated_root):
    """Duplicate secondary entries are squashed; primary not in secondary."""
    r = client.post(
        "/api/users/lens-targets",
        json={
            "primary": "C_product_ops",
            "secondary": ["B_data_analytics", "B_data_analytics", "A_strategy_research"],
        },
        headers={"X-User-Id": "u-lt-dedup"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["secondary"] == ["B_data_analytics", "A_strategy_research"]
