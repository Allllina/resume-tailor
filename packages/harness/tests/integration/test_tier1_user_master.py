"""Integration tests for Wave 2.7 P2.4 — tier1 uses user-uploaded master.tex.

These tests use the real repo_root because tier1 reads contracts/schemas/,
assets/resume-bank/versions/, and assets/experience-bank/index.json.
We use ephemeral user_ids and clean up after each test so they don't
pollute default's run history.
"""
from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


JD_TEXT = (
    "AIGC 内容实习生 招聘. "
    + "Prompt Agent LLM RAG 生成式 AI 工作流 " * 10
)


def _mock_llm():
    # Phase 2: smart mock dispatches valid JSON per sub-skill so the
    # pipeline reaches its tex artifact instead of fail-fasting on
    # fit_diagnosis_pre_rewrite.
    from tests.integration._mocks import make_phase2_llm_mock
    mock = make_phase2_llm_mock()
    mock.last_usage = None
    return mock


@pytest.fixture
def ephemeral_user_id(repo_root):
    """Generate a fresh user_id and remove its data dir after the test."""
    uid = f"test-{secrets.token_hex(6)}"
    yield uid
    user_dir = repo_root / "packages/harness/data/users" / uid
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    from harness.api.main import app
    return TestClient(app)


# ---------------- Tier1Tools / MasterSelector unit tests ----------------


def test_tier1tools_plumbs_user_master_path_to_selector(repo_root, tmp_path):
    """Tier1Tools(user_master_path=...) → master_selector.select() returns
    that path regardless of lens."""
    from harness.repl.eval import Tier1Tools

    user_tex = tmp_path / "master.tex"
    user_tex.write_text(r"\documentclass{article}\begin{document}USER\end{document}")

    tools = Tier1Tools(
        repo_root,
        llm_client=MagicMock(),
        policy_gateway=MagicMock(),
        user_master_path=user_tex,
    )
    selection = tools.master_selector.select("A_strategy_research")
    assert selection.master_path == user_tex
    assert selection.metadata.get("source") == "user_uploaded"


def test_master_selector_user_master_missing_falls_through(repo_root, tmp_path):
    """user_master_path provided but file doesn't exist → fall through to
    assets-based selection (defensive)."""
    from harness.tier1.master_selector import MasterSelector

    nonexistent = tmp_path / "no-master.tex"
    sel = MasterSelector(repo_root, user_master_path=nonexistent)
    result = sel.select("C_product_ops")
    assert result.master_path.exists()
    assert "user_uploaded" not in result.metadata.get("source", "")


# ---------------- API integration ----------------


def test_non_jingwen_user_with_uploaded_master_runs_tier1(
    client, repo_root, ephemeral_user_id, monkeypatch
):
    """Upload master via API, then POST /api/tier1-tailor with that user_id;
    tier1 should pick the user-uploaded master.tex (proven by a marker
    that only appears in our upload)."""
    # Stub the auto-scorer's LLM provider so background scoring (irrelevant
    # here, since we don't upload experiences) doesn't try to use a real key
    import harness.api.users as users_module
    monkeypatch.setattr(users_module, "get_llm_provider", _mock_llm)

    user_tex = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "% USER_UPLOADED_MARKER\n"
        "\\section*{Skills}\nPython, SQL\n"
        "\\section*{Experience}\nCo X — analyst\n"
        "\\end{document}\n"
    )

    upload_resp = client.post(
        "/api/users/profile/upload-resume",
        files={"file": ("master.tex", user_tex.encode("utf-8"), "text/x-tex")},
        headers={"X-User-Id": ephemeral_user_id},
    )
    assert upload_resp.status_code == 200, upload_resp.text

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post(
            "/api/tier1-tailor",
            json={
                "mode": "manual",
                "jd": {"source": "paste", "raw_text": JD_TEXT},
                "candidate_profile_ref": "x",
                "target_market": "mainland-china",
            },
            headers={"X-User-Id": ephemeral_user_id},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    run_id = body["run_id"]

    runs_dir = (
        repo_root
        / "packages/harness/data/users"
        / ephemeral_user_id
        / "runs"
        / run_id
    )
    tex_path = runs_dir / "resume.tex"
    assert tex_path.exists(), f"missing {tex_path}"
    rendered = tex_path.read_text()
    assert "USER_UPLOADED_MARKER" in rendered


def test_non_jingwen_user_without_master_returns_412(
    client, ephemeral_user_id
):
    """Brand-new user with no uploaded master → tier1-tailor returns 412."""
    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post(
            "/api/tier1-tailor",
            json={
                "mode": "manual",
                "jd": {"source": "paste", "raw_text": JD_TEXT},
                "candidate_profile_ref": "x",
                "target_market": "mainland-china",
            },
            headers={"X-User-Id": ephemeral_user_id},
        )
    assert r.status_code == 412
    assert "upload" in r.text.lower()


# ---------------- Wave 4 D.5+follow-up — per-lens master plumbing ----------------


def test_tier1tools_plumbs_user_dir_to_selector(repo_root, tmp_path):
    """Tier1Tools(user_dir=...) → MasterSelector consults the priority chain
    user_dir/masters/<lens>/master.tex first, then user_dir/master.tex.

    Wave 4 D.5 follow-up: C.1+C.2 ship per-lens masters but tier1_tailor.py
    was still using the legacy user_master_path entrypoint that bypassed the
    full priority chain.
    """
    from harness.repl.eval import Tier1Tools

    user_dir = tmp_path / "user-data"
    per_lens_dir = user_dir / "masters" / "C_product_ops"
    per_lens_dir.mkdir(parents=True)
    per_lens_tex = per_lens_dir / "master.tex"
    per_lens_tex.write_text(
        r"\documentclass{article}\begin{document}PER_LENS\end{document}"
    )
    # Legacy single master also present — per-lens must win.
    legacy_tex = user_dir / "master.tex"
    legacy_tex.write_text(
        r"\documentclass{article}\begin{document}LEGACY\end{document}"
    )

    tools = Tier1Tools(
        repo_root,
        llm_client=MagicMock(),
        policy_gateway=MagicMock(),
        user_dir=user_dir,
    )
    selection = tools.master_selector.select("C_product_ops")
    assert selection.master_path == per_lens_tex
    assert selection.metadata.get("source") == "user_uploaded_per_lens"


def test_tier1tools_user_dir_falls_back_to_legacy_when_no_per_lens(repo_root, tmp_path):
    """user_dir present but no per-lens master for the routed lens → falls
    back to <user_dir>/master.tex with source=user_uploaded_legacy."""
    from harness.repl.eval import Tier1Tools

    user_dir = tmp_path / "user-data"
    user_dir.mkdir()
    legacy_tex = user_dir / "master.tex"
    legacy_tex.write_text(
        r"\documentclass{article}\begin{document}LEGACY\end{document}"
    )

    tools = Tier1Tools(
        repo_root,
        llm_client=MagicMock(),
        policy_gateway=MagicMock(),
        user_dir=user_dir,
    )
    selection = tools.master_selector.select("C_product_ops")
    assert selection.master_path == legacy_tex
    assert selection.metadata.get("source") == "user_uploaded_legacy"


def test_non_jingwen_user_with_only_per_lens_master_runs_tier1(
    client, repo_root, ephemeral_user_id, monkeypatch
):
    """A user with per-lens master(s) but no legacy single master should
    still be able to tailor — the 412 gate must check has_master OR any
    per-lens master, not has_master alone."""
    import harness.api.users as users_module
    monkeypatch.setattr(users_module, "get_llm_provider", _mock_llm)

    # Manually seed per-lens master via the storage helper (mirrors what
    # the master_gen background task does in C.2).
    from harness.config import config
    from harness.users.storage import UserStorage

    storage = UserStorage(config.repo_root)
    storage.ensure_user_dir(ephemeral_user_id)
    user_dir = storage.user_dir(ephemeral_user_id)

    # Plant a profile with target_market so endpoint doesn't 412 on profile.
    storage.save_profile(
        ephemeral_user_id,
        {"candidate_names": ["Test User"], "target_market_default": "mainland-china"},
    )

    per_lens_dir = user_dir / "masters" / "C_product_ops"
    per_lens_dir.mkdir(parents=True)
    per_lens_tex = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "% PER_LENS_C_MARKER\n"
        "\\section*{Skills}\nPython, SQL\n"
        "\\section*{Experience}\nCo Y — PM\n"
        "\\end{document}\n"
    )
    (per_lens_dir / "master.tex").write_text(per_lens_tex)

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post(
            "/api/tier1-tailor",
            json={
                "mode": "manual",
                "jd": {"source": "paste", "raw_text": JD_TEXT},
                "candidate_profile_ref": "x",
                "target_market": "mainland-china",
                "lens_hint": "C_product_ops",  # bypass router uncertainty
            },
            headers={"X-User-Id": ephemeral_user_id},
        )
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    tex_path = (
        repo_root
        / "packages/harness/data/users"
        / ephemeral_user_id
        / "runs"
        / run_id
        / "resume.tex"
    )
    assert tex_path.exists(), f"missing {tex_path}"
    rendered = tex_path.read_text()
    assert "PER_LENS_C_MARKER" in rendered, (
        "tier1 should have picked the per-lens master, not project sample"
    )


def test_non_jingwen_user_with_per_lens_uses_lens_routed_version(
    client, repo_root, ephemeral_user_id, monkeypatch
):
    """User has per-lens masters for BOTH B and C; lens_hint=C routes to C
    version. Proves per-lens routing actually uses the routed lens, not
    the first lens alphabetically."""
    import harness.api.users as users_module
    monkeypatch.setattr(users_module, "get_llm_provider", _mock_llm)

    from harness.config import config
    from harness.users.storage import UserStorage

    storage = UserStorage(config.repo_root)
    storage.ensure_user_dir(ephemeral_user_id)
    user_dir = storage.user_dir(ephemeral_user_id)
    storage.save_profile(
        ephemeral_user_id,
        {"candidate_names": ["Test User"], "target_market_default": "mainland-china"},
    )

    def _seed(lens: str, marker: str):
        d = user_dir / "masters" / lens
        d.mkdir(parents=True)
        (d / "master.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\n"
            f"% {marker}\n"
            "\\section*{Skills}\nPython\n"
            "\\section*{Experience}\nCo — analyst\n"
            "\\end{document}\n"
        )

    _seed("B_data_analytics", "MARKER_B")
    _seed("C_product_ops", "MARKER_C")

    with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
        r = client.post(
            "/api/tier1-tailor",
            json={
                "mode": "manual",
                "jd": {"source": "paste", "raw_text": JD_TEXT},
                "candidate_profile_ref": "x",
                "target_market": "mainland-china",
                "lens_hint": "C_product_ops",
            },
            headers={"X-User-Id": ephemeral_user_id},
        )
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    rendered = (
        repo_root
        / "packages/harness/data/users"
        / ephemeral_user_id
        / "runs"
        / run_id
        / "resume.tex"
    ).read_text()
    assert "MARKER_C" in rendered
    assert "MARKER_B" not in rendered


def test_jingwen_default_without_upload_uses_legacy_assets(client, repo_root):
    """Backward compat: default with no uploaded master still works
    via legacy assets/resume-bank/versions/. We delete any existing master
    before the test to simulate the legacy state, then restore.

    D11 note: post-isolation, assets/resume-bank/versions/<lens>/resume.zh.tex
    is gitignored. On fresh-clone CI the MasterSelector resolves to
    resume.sample.zh.tex (project_sample); on a maintainer's local repo with
    private real masters present, project_master wins. Either path produces
    a valid run; the test only asserts verdict ∈ {complete, failed}.
    """
    master_path = repo_root / "packages/harness/data/users/default/master.tex"
    backup_bytes: bytes | None = None
    if master_path.exists():
        backup_bytes = master_path.read_bytes()
        master_path.unlink()

    try:
        with patch("harness.api.tier1_tailor.make_llm_provider_for_thread", return_value=_mock_llm()):
            r = client.post(
                "/api/tier1-tailor",
                json={
                    "mode": "manual",
                    "jd": {"source": "paste", "raw_text": JD_TEXT},
                    "candidate_profile_ref": "x",
                    "target_market": "mainland-china",
                },
                # no X-User-Id → defaults to default
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "run_id" in body
        # R-18 (v0.6.1) adds `degraded_no_substance` — under shallow mock
        # LLM, post_rewrite falls back so substance check demotes; legacy
        # success path is still verdict=complete on machines with private
        # masters present. All three are acceptable for this test.
        assert body["verdict"] in ("complete", "failed", "degraded_no_substance")
    finally:
        if backup_bytes is not None:
            master_path.write_bytes(backup_bytes)
