"""Integration tests for /api/users/* endpoints (Wave 2.7 P2.3)."""
from __future__ import annotations

import io
import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


_FULL_SCORE = {
    "recognition_per_industry": {
        "consulting": "high",
        "finance": "medium",
        "internet_strategic": "high",
        "internet_operational": "medium",
        "internet_data": "medium",
        "education": "low",
        "market_research": "low",
        "brand_marketing": "low",
    },
    "vertical_fit_per_lens": {
        "A_strategy_research": "core",
        "B_data_analytics": "adjacent",
        "C_product_ops": "adjacent",
        "D_finance_markets": "weak",
        "HC_human_capital": "weak",
    },
    "ai_digital_fluency": "moderate",
}


def _mock_llm():
    p = MagicMock()
    p.call = AsyncMock(return_value=json.dumps(_FULL_SCORE))
    return p


@pytest.fixture
def isolated_root(monkeypatch, tmp_path):
    """Point harness.config.config.repo_root at a tmp dir."""
    fake_root = tmp_path
    (fake_root / "packages/harness/data/users").mkdir(parents=True, exist_ok=True)

    from harness.config import config
    monkeypatch.setattr(config, "repo_root", fake_root)
    return fake_root


@pytest.fixture
def client(monkeypatch, isolated_root):
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    # Patch get_llm_provider in users module so background scoring uses mock
    import harness.api.users as users_module
    monkeypatch.setattr(users_module, "get_llm_provider", _mock_llm)
    from harness.api.main import app
    return TestClient(app)


# ---------------- upload-resume ----------------


def test_upload_resume_md_happy_path(client, isolated_root):
    md = b"# Education\nSchool A\n\n# Experience\nCompany X\n"
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("resume.md", md, "text/markdown")},
        headers={"X-User-Id": "test-user-md"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["format"] == "md"
    assert body["confidence"] == 0.95
    assert body["section_count"] >= 2

    # master.tex exists on disk
    master = isolated_root / "packages/harness/data/users/test-user-md/master.tex"
    assert master.exists()
    assert "\\documentclass" in master.read_text()


def test_upload_resume_tex_passthrough(client, isolated_root):
    tex = b"\\documentclass{article}\n\\begin{document}\n\\section*{X}\nbody\n\\end{document}\n"
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("r.tex", tex, "text/x-tex")},
        headers={"X-User-Id": "test-user-tex"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "tex"
    assert body["confidence"] == 1.0


def test_upload_resume_rejects_empty(client):
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("r.md", b"", "text/markdown")},
        headers={"X-User-Id": "test-user-empty"},
    )
    assert r.status_code == 400


def test_upload_resume_rejects_oversized(client):
    # 5MB cap (matches _RESUME_MAX_BYTES post-Wave-2.7-dogfood bump)
    big = b"x" * (5 * 1024 * 1024 + 1)
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("r.md", big, "text/markdown")},
        headers={"X-User-Id": "test-user-big"},
    )
    assert r.status_code == 413


def test_upload_resume_rejects_unknown_format(client):
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("resume.txt", b"hello", "text/plain")},
        headers={"X-User-Id": "test-user-bad"},
    )
    assert r.status_code == 400


# ---------------- upload-experiences ----------------


def test_upload_experiences_multi_file(client, isolated_root):
    files = [
        ("files", ("exp1.md", b"# Project A\n\nContent A", "text/markdown")),
        ("files", ("exp2.md", b"# Project B\n\nContent B", "text/markdown")),
    ]
    r = client.post(
        "/api/users/experiences/upload",
        files=files,
        headers={"X-User-Id": "test-user-exp"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert len(body["experiences"]) == 2
    for record in body["experiences"]:
        assert "id" in record
        assert "file_name" in record
        assert record["scoring_status"] == "queued"

    # Background scoring should have completed by the time TestClient
    # finishes the request (fastapi BackgroundTasks run after response).
    # Verify by reading the index file.
    idx_path = (
        isolated_root
        / "packages/harness/data/users/test-user-exp/experiences-index.json"
    )
    assert idx_path.exists()
    items = json.loads(idx_path.read_text())["experiences"]
    assert len(items) == 2
    # After background task ran, scoring_status should be "done"
    statuses = {it["scoring_status"] for it in items}
    assert statuses == {"done"}
    # 3-axis fields populated from mock LLM
    for it in items:
        assert it["recognition_per_industry"]["consulting"] == "high"
        assert it["vertical_fit_per_lens"]["A_strategy_research"] == "core"
        assert it["ai_digital_fluency"] == "moderate"


def test_upload_experiences_cap_30(client):
    files = [
        ("files", (f"exp{i}.md", b"# Project\n\ncontent", "text/markdown"))
        for i in range(31)
    ]
    r = client.post(
        "/api/users/experiences/upload",
        files=files,
        headers={"X-User-Id": "test-user-cap"},
    )
    assert r.status_code == 413


def test_upload_experiences_rejects_oversized(client):
    # 2MB cap (matches _EXP_MAX_BYTES post-Wave-2.7-dogfood bump)
    big = b"x" * (2 * 1024 * 1024 + 1)
    files = [("files", ("big.md", big, "text/markdown"))]
    r = client.post(
        "/api/users/experiences/upload",
        files=files,
        headers={"X-User-Id": "test-user-bigexp"},
    )
    assert r.status_code == 413


# ---------------- GET /api/users/me ----------------


def test_get_me_before_any_upload(client):
    r = client.get("/api/users/me", headers={"X-User-Id": "fresh-user"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "fresh-user"
    assert body["has_resume"] is False
    assert body["experience_count"] == 0
    assert body["experiences"] == []


def test_get_me_after_resume_upload(client):
    md = b"# Education\nSchool\n# Experience\nCo\n"
    client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("resume.md", md, "text/markdown")},
        headers={"X-User-Id": "user-with-resume"},
    )
    r = client.get("/api/users/me", headers={"X-User-Id": "user-with-resume"})
    assert r.status_code == 200
    body = r.json()
    assert body["has_resume"] is True
    assert body["profile"]["master_format"] == "md"


# ---------------- DELETE ----------------


def test_delete_experience_success_and_404(client):
    files = [("files", ("e.md", b"# E\ncontent", "text/markdown"))]
    r = client.post(
        "/api/users/experiences/upload",
        files=files,
        headers={"X-User-Id": "user-del"},
    )
    assert r.status_code == 200
    exp_id = r.json()["experiences"][0]["id"]

    # Success
    r2 = client.delete(
        f"/api/users/experiences/{exp_id}",
        headers={"X-User-Id": "user-del"},
    )
    assert r2.status_code == 200
    assert r2.json()["ok"] is True

    # Idempotent — 404 second time
    r3 = client.delete(
        f"/api/users/experiences/{exp_id}",
        headers={"X-User-Id": "user-del"},
    )
    assert r3.status_code == 404


def test_invalid_x_user_id_rejected(client):
    r = client.get(
        "/api/users/me",
        headers={"X-User-Id": "../etc/passwd"},
    )
    assert r.status_code == 400


# ---------------- GET /api/users/me/master/tex ----------------


def test_get_master_tex_404_when_no_upload(client):
    r = client.get(
        "/api/users/me/master/tex",
        headers={"X-User-Id": "no-master-yet"},
    )
    assert r.status_code == 404


def test_get_master_tex_returns_content_after_upload(client, isolated_root):
    md = b"# Education\nSchool A\n\n# Experience\nCompany X\n"
    r = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("resume.md", md, "text/markdown")},
        headers={"X-User-Id": "tex-fetcher"},
    )
    assert r.status_code == 200

    r2 = client.get(
        "/api/users/me/master/tex",
        headers={"X-User-Id": "tex-fetcher"},
    )
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("text/x-tex")
    body = r2.text
    assert "\\documentclass" in body


# ---------------- GET /api/users/me/master/pdf ----------------


def test_get_master_pdf_503_when_toolchain_unavailable(client, monkeypatch):
    from harness.pdf.compiler import PdfToolchainUnavailable

    async def fake_compile(_tex_path):
        raise PdfToolchainUnavailable("Docker Desktop is not running")

    monkeypatch.setattr("harness.pdf.compiler.compile_tex_to_pdf", fake_compile)
    r = client.post(
        "/api/users/profile/upload-resume",
        files={
            "file": (
                "resume.tex",
                b"\\documentclass{article}\\begin{document}hi\\end{document}",
                "text/x-tex",
            )
        },
        headers={"X-User-Id": "pdf-fetcher"},
    )
    assert r.status_code == 200

    r2 = client.get(
        "/api/users/me/master/pdf",
        headers={"X-User-Id": "pdf-fetcher"},
    )
    assert r2.status_code == 503
    assert r2.json()["detail"]["code"] == "pdf_toolchain_unavailable"


# ---------------- GET /api/users/masters/{lens}/tex ----------------


def test_get_lens_master_tex_422_on_invalid_lens(client):
    r = client.get(
        "/api/users/masters/BOGUS/tex",
        headers={"X-User-Id": "lens-tex-user"},
    )
    assert r.status_code == 422
    assert "BOGUS" in r.text


def test_get_lens_master_tex_404_when_not_generated(client, isolated_root):
    r = client.get(
        "/api/users/masters/C_product_ops/tex",
        headers={"X-User-Id": "lens-tex-empty"},
    )
    assert r.status_code == 404


def test_get_lens_master_tex_returns_content_when_present(client, isolated_root):
    from harness.users.storage import UserStorage

    uid = "lens-tex-ready"
    storage = UserStorage(isolated_root)
    storage.ensure_user_dir(uid)
    storage.add_lens_master(
        uid,
        "C_product_ops",
        "\\documentclass{article}\nlens master content\n",
        method="rewrite_from_upload_and_bank",
    )

    r = client.get(
        "/api/users/masters/C_product_ops/tex",
        headers={"X-User-Id": uid},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/x-tex")
    assert "lens master content" in r.text


# ---------------- PATCH /api/users/me ----------------


def test_patch_me_updates_candidate_names(client):
    r = client.patch(
        "/api/users/me",
        json={"candidate_names": ["张明", "Zhang Ming"]},
        headers={"X-User-Id": "patch-names"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["candidate_names"] == ["张明", "Zhang Ming"]

    # Persisted across fetches
    r2 = client.get("/api/users/me", headers={"X-User-Id": "patch-names"})
    assert r2.json()["profile"]["candidate_names"] == ["张明", "Zhang Ming"]


def test_patch_me_updates_target_market(client):
    r = client.patch(
        "/api/users/me",
        json={"target_market_default": "north-america"},
        headers={"X-User-Id": "patch-market"},
    )
    assert r.status_code == 200
    assert r.json()["profile"]["target_market_default"] == "north-america"


def test_patch_me_rejects_invalid_market(client):
    r = client.patch(
        "/api/users/me",
        json={"target_market_default": "uk"},
        headers={"X-User-Id": "patch-bad-market"},
    )
    assert r.status_code == 422  # pydantic validation error


def test_patch_me_partial_does_not_clobber(client):
    # Set names first
    r1 = client.patch(
        "/api/users/me",
        json={"candidate_names": ["Alpha"]},
        headers={"X-User-Id": "patch-partial"},
    )
    assert r1.status_code == 200

    # Now update only market — names must persist
    r2 = client.patch(
        "/api/users/me",
        json={"target_market_default": "hong-kong"},
        headers={"X-User-Id": "patch-partial"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["profile"]["candidate_names"] == ["Alpha"]
    assert body["profile"]["target_market_default"] == "hong-kong"


# ---------------- DELETE /api/users/me ----------------


def test_delete_me_cascades_user_dir(client, isolated_root):
    # Seed: upload a resume + an experience, then nuke it
    client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("r.md", b"# A\nbody\n# B\nbody\n", "text/markdown")},
        headers={"X-User-Id": "user-to-nuke"},
    )
    client.post(
        "/api/users/experiences/upload",
        files=[("files", ("e.md", b"# E\nbody", "text/markdown"))],
        headers={"X-User-Id": "user-to-nuke"},
    )
    user_dir = isolated_root / "packages/harness/data/users/user-to-nuke"
    assert user_dir.exists()

    r = client.delete("/api/users/me", headers={"X-User-Id": "user-to-nuke"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert not user_dir.exists()


def test_delete_me_idempotent(client):
    # Calling on a fresh user that's never uploaded — still ok
    r = client.delete("/api/users/me", headers={"X-User-Id": "never-uploaded"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_delete_me_rejects_invalid_user_id(client):
    r = client.delete(
        "/api/users/me",
        headers={"X-User-Id": "../etc/passwd"},
    )
    assert r.status_code == 400


# ---------------- rescore queued experiences ----------------


def test_rescore_queued_walks_index(client, isolated_root):
    """POST /api/users/experiences/rescore re-enqueues every queued item."""
    user_id = "rescore-user"
    user_dir = isolated_root / "packages/harness/data/users" / user_id
    (user_dir / "experiences").mkdir(parents=True, exist_ok=True)

    # Two queued experiences with raw .md content; one already done
    (user_dir / "experiences" / "exp-1.md").write_text("Senior PM at Anker; built AIGC pipeline.")
    (user_dir / "experiences" / "exp-2.md").write_text("Strategy intern at Kearney; semiconductor research.")
    (user_dir / "experiences" / "exp-3.md").write_text("Done already.")
    (user_dir / "experiences-index.json").write_text(json.dumps({
        "experiences": [
            {"id": "exp-1", "file_name": "exp-1.md", "scoring_status": "queued"},
            {"id": "exp-2", "file_name": "exp-2.md", "scoring_status": "queued"},
            {"id": "exp-3", "file_name": "exp-3.md", "scoring_status": "done"},
        ]
    }))
    (user_dir / "profile.json").write_text(json.dumps({
        "user_id": user_id,
        "candidate_names": [],
        "experience_count": 3,
        "experiences_scored_count": 1,
    }))

    r = client.post("/api/users/experiences/rescore", headers={"X-User-Id": user_id})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["scheduled"] == 2
    assert sorted(body["experience_ids"]) == ["exp-1", "exp-2"]


def test_rescore_skips_when_raw_file_missing(client, isolated_root):
    """If the index has a queued entry but the raw .md is gone, skip it (don't 500)."""
    user_id = "missing-raw"
    user_dir = isolated_root / "packages/harness/data/users" / user_id
    (user_dir / "experiences").mkdir(parents=True, exist_ok=True)
    # Only one of the two raw files exists
    (user_dir / "experiences" / "exp-present.md").write_text("here.")
    (user_dir / "experiences-index.json").write_text(json.dumps({
        "experiences": [
            {"id": "exp-missing", "file_name": "exp-missing.md", "scoring_status": "queued"},
            {"id": "exp-present", "file_name": "exp-present.md", "scoring_status": "queued"},
        ]
    }))
    (user_dir / "profile.json").write_text(json.dumps({
        "user_id": user_id,
        "candidate_names": [],
    }))

    r = client.post("/api/users/experiences/rescore", headers={"X-User-Id": user_id})
    assert r.status_code == 200
    body = r.json()
    assert body["scheduled"] == 1
    assert body["experience_ids"] == ["exp-present"]


def test_rescore_returns_zero_when_all_done(client, isolated_root):
    user_id = "all-done"
    user_dir = isolated_root / "packages/harness/data/users" / user_id
    (user_dir / "experiences").mkdir(parents=True, exist_ok=True)
    (user_dir / "experiences-index.json").write_text(json.dumps({
        "experiences": [
            {"id": "exp-1", "file_name": "exp-1.md", "scoring_status": "done"},
        ]
    }))
    (user_dir / "profile.json").write_text(json.dumps({"user_id": user_id, "candidate_names": []}))

    r = client.post("/api/users/experiences/rescore", headers={"X-User-Id": user_id})
    assert r.status_code == 200
    body = r.json()
    assert body["scheduled"] == 0
    assert body["experience_ids"] == []


def test_rescore_rejects_invalid_user_id(client):
    r = client.post(
        "/api/users/experiences/rescore",
        headers={"X-User-Id": "../etc/passwd"},
    )
    assert r.status_code == 400
