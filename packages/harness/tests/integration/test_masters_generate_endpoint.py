"""Integration tests for /api/users/masters/* (Wave 4 C.1.4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


def _mock_llm():
    p = MagicMock()
    # Default response shape that the master_gen engine can parse and verify.
    payload = {
        "master_tex": "% generated per-lens master\n\\section*{Summary}\nLens-tailored.\n",
        "experiences_included": ["exp-1"],
        "experiences_dropped": [],
        "summary_text": "content from upload.",
        "decision_rationale": "Lens fits the experience bank.",
    }
    p.call = AsyncMock(return_value=json.dumps(payload))
    return p


def _seed_user(root: Path, user_id: str, *, with_master: bool = True):
    user_dir = root / "packages/harness/data/users" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "experiences").mkdir(exist_ok=True)
    (user_dir / "runs").mkdir(exist_ok=True)
    (user_dir / "experiences" / "exp-1.md").write_text(
        "# content from upload.\nSenior PM details.\n"
    )
    (user_dir / "experiences-index.json").write_text(json.dumps({
        "experiences": [
            {
                "id": "exp-1",
                "file_name": "exp-1.md",
                "scoring_status": "done",
                "vertical_fit_per_lens": {
                    "C_product_ops": "core",
                    "A_strategy_research": "weak",
                },
            }
        ]
    }))
    profile = {
        "user_id": user_id,
        "candidate_names": ["Test User"],
        "target_lens_default": "C_product_ops",
        "target_lens_secondary": ["A_strategy_research"],
    }
    (user_dir / "profile.json").write_text(json.dumps(profile))
    if with_master:
        (user_dir / "master.tex").write_text(
            "\\documentclass{article}\\begin{document}content from upload.\\end{document}"
        )
    return user_dir


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


# ---------------- POST /api/users/masters/generate ----------------


def test_generate_master_happy_path(client, isolated_root):
    user_id = "u-gen-happy"
    _seed_user(isolated_root, user_id)

    r = client.post(
        "/api/users/masters/generate",
        json={"lens": "C_product_ops"},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["lens"] == "C_product_ops"
    assert body["status"] == "scheduled"

    # Background task runs after the response (TestClient waits for it).
    user_dir = isolated_root / "packages/harness/data/users" / user_id
    master_path = user_dir / "masters" / "C_product_ops" / "master.tex"
    assert master_path.exists()
    assert "Lens-tailored" in master_path.read_text()
    # generated_at + generation_method siblings written
    assert (user_dir / "masters" / "C_product_ops" / "generated_at.txt").exists()
    method = (
        (user_dir / "masters" / "C_product_ops" / "generation_method.txt")
        .read_text()
        .strip()
    )
    assert method == "rewrite_from_upload_and_bank"
    # Profile updated
    profile = json.loads((user_dir / "profile.json").read_text())
    assert "C_product_ops" in profile["masters_generated"]
    # Generating marker cleaned up
    assert not (user_dir / "masters" / "C_product_ops" / ".generating").exists()


def test_generate_master_lens_not_in_targets(client, isolated_root):
    """Lens that is not in target_lens_default + target_lens_secondary → 422."""
    user_id = "u-gen-bad-target"
    _seed_user(isolated_root, user_id)
    # User's targets are C_product_ops + A_strategy_research; D is not picked.

    r = client.post(
        "/api/users/masters/generate",
        json={"lens": "D_finance_markets"},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 422


def test_generate_master_invalid_lens_enum(client, isolated_root):
    user_id = "u-gen-bad-enum"
    _seed_user(isolated_root, user_id)

    r = client.post(
        "/api/users/masters/generate",
        json={"lens": "Z_made_up"},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 422


def test_generate_master_no_upload_returns_404(client, isolated_root):
    user_id = "u-gen-no-master"
    _seed_user(isolated_root, user_id, with_master=False)

    r = client.post(
        "/api/users/masters/generate",
        json={"lens": "C_product_ops"},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 404


# ---------------- GET /api/users/masters ----------------


def test_get_masters_returns_targets_only(client, isolated_root):
    user_id = "u-gm-targets"
    _seed_user(isolated_root, user_id)
    r = client.get("/api/users/masters", headers={"X-User-Id": user_id})
    assert r.status_code == 200
    body = r.json()
    # Only C + A, NOT all 5 lenses.
    assert set(body.keys()) == {"C_product_ops", "A_strategy_research"}
    for entry in body.values():
        assert entry["status"] == "absent"
        assert entry["has_master"] is False


def test_get_masters_after_generation(client, isolated_root):
    user_id = "u-gm-after"
    _seed_user(isolated_root, user_id)
    r1 = client.post(
        "/api/users/masters/generate",
        json={"lens": "C_product_ops"},
        headers={"X-User-Id": user_id},
    )
    assert r1.status_code == 200
    r2 = client.get("/api/users/masters", headers={"X-User-Id": user_id})
    assert r2.status_code == 200
    body = r2.json()
    assert body["C_product_ops"]["status"] == "ready"
    assert body["C_product_ops"]["has_master"] is True
    assert body["C_product_ops"]["method"] == "rewrite_from_upload_and_bank"
    assert body["A_strategy_research"]["status"] == "absent"


def test_delete_master_removes_dir_and_profile_entry(client, isolated_root):
    user_id = "u-del-master"
    _seed_user(isolated_root, user_id)
    # Generate one
    client.post(
        "/api/users/masters/generate",
        json={"lens": "C_product_ops"},
        headers={"X-User-Id": user_id},
    )
    # Delete it
    r = client.delete(
        "/api/users/masters/C_product_ops",
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["lens"] == "C_product_ops"
    user_dir = isolated_root / "packages/harness/data/users" / user_id
    assert not (user_dir / "masters" / "C_product_ops").exists()
    profile = json.loads((user_dir / "profile.json").read_text())
    assert (
        "masters_generated" not in profile
        or "C_product_ops" not in profile.get("masters_generated", {})
    )


def test_delete_master_returns_404_when_absent(client, isolated_root):
    user_id = "u-del-missing"
    _seed_user(isolated_root, user_id)
    r = client.delete(
        "/api/users/masters/C_product_ops",
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 404


def test_delete_master_invalid_lens_enum(client, isolated_root):
    user_id = "u-del-bad-enum"
    _seed_user(isolated_root, user_id)
    r = client.delete(
        "/api/users/masters/Z_made_up",
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 422
