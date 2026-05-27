"""Integration tests for GET /api/runs + /api/runs/{id} + /tex + /pdf."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_runs_dir(monkeypatch, tmp_path):
    """Point harness.config.config.repo_root at a temp dir with empty
    data/users/default/runs/ (per Wave 2.7 per-user namespacing)."""
    fake_root = tmp_path
    runs_dir = fake_root / "packages/harness/data/users/default/runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    from harness.config import config
    monkeypatch.setattr(config, "repo_root", fake_root)
    return runs_dir


@pytest.fixture
def client(monkeypatch, isolated_runs_dir):
    monkeypatch.setenv("HARNESS_ANTHROPIC_API_KEY", "sk-test-fake")
    from harness.api.main import app
    return TestClient(app)


_OMIT = object()  # sentinel for fields that should be absent from seeded state


def _seed_run(runs_dir: Path, run_id: str, *, verdict: str = "complete",
              degradation_count: int = 0, primary_lens: str = "C_product_ops",
              tier_assigned=1, matched_resume_version="C_product_ops",
              created_at: str | None = None, with_tex: bool = False,
              jd_context: dict | None = None) -> Path:
    """Seed a run's state.json on disk.

    Pass tier_assigned=_OMIT or matched_resume_version=_OMIT to simulate
    pre-Wave-4 runs whose state.json predates those fields. They have
    schema-relevant defaults (1, "C_product_ops") otherwise.
    """
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        # input_ref is required by harness-tailor-output schema; the
        # PATCH /lifecycle endpoint re-validates state before write so
        # seeded fixtures must be schema-conformant.
        "input_ref": f"sha256:{run_id}-fake",
        "verdict": verdict,
        "lens_routing": {"primary_lens": primary_lens},
        "trace": {"perception_events": [], "planning_events": [], "action_events": [], "feedback_events": []},
        "metrics": {"total_tokens": 100, "total_claude_calls": 1, "elapsed_seconds": 1.0},
        "degradation_events": [
            {"stage": "action", "reason": "x", "fallback_taken": "y"}
        ] * degradation_count,
        "tex_artifact_path": str(run_dir / "resume.tex") if with_tex else "",
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    if jd_context:
        state["jd_context"] = jd_context
    if tier_assigned is not _OMIT:
        state["tier_assigned"] = tier_assigned
    if matched_resume_version is not _OMIT:
        state["matched_resume_version"] = matched_resume_version
    (run_dir / "state.json").write_text(json.dumps(state))
    if with_tex:
        (run_dir / "resume.tex").write_text("\\documentclass{article}\\begin{document}hi\\end{document}")
    return run_dir


def test_list_empty(client):
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert r.json() == {"runs": [], "total": 0}


def test_list_sorted_desc_by_created_at(client, isolated_runs_dir):
    now = datetime.now(timezone.utc)
    _seed_run(isolated_runs_dir, "run-old", created_at=(now - timedelta(hours=2)).isoformat())
    _seed_run(isolated_runs_dir, "run-new", created_at=now.isoformat())
    _seed_run(isolated_runs_dir, "run-mid", created_at=(now - timedelta(hours=1)).isoformat())

    r = client.get("/api/runs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    ids = [s["run_id"] for s in body["runs"]]
    assert ids == ["run-new", "run-mid", "run-old"]


def test_list_includes_jd_hints_when_present(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-anker", jd_context={
        "company_hint": "Anker", "role_title_hint": "AIGC 内容实习生", "location_hint": "深圳",
    })
    r = client.get("/api/runs")
    assert r.status_code == 200
    summary = r.json()["runs"][0]
    assert summary["company_hint"] == "Anker"
    assert summary["role_title_hint"] == "AIGC 内容实习生"
    assert summary["location_hint"] == "深圳"


def test_list_includes_tier_assigned_and_matched_resume_version(client, isolated_runs_dir):
    """Inbox cards need tier badge + master indicator without per-card detail fetches."""
    _seed_run(isolated_runs_dir, "run-tier3", tier_assigned=3, matched_resume_version="custom")
    _seed_run(isolated_runs_dir, "run-tier1", tier_assigned=1, matched_resume_version="C_product_ops")
    r = client.get("/api/runs")
    assert r.status_code == 200
    by_id = {s["run_id"]: s for s in r.json()["runs"]}
    assert by_id["run-tier3"]["tier_assigned"] == 3
    assert by_id["run-tier3"]["matched_resume_version"] == "custom"
    assert by_id["run-tier1"]["tier_assigned"] == 1
    assert by_id["run-tier1"]["matched_resume_version"] == "C_product_ops"


def test_list_omits_tier_when_state_lacks_field(client, isolated_runs_dir):
    """Backward compat: pre-Wave-4 runs without tier_assigned still serialize."""
    _seed_run(isolated_runs_dir, "run-legacy", tier_assigned=_OMIT, matched_resume_version=_OMIT)
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    # Field is absent (not None) when the underlying state didn't carry it.
    assert "tier_assigned" not in summary
    assert "matched_resume_version" not in summary


def test_ui_status_partial_pending_user_maps_to_pending_human_verify(client, isolated_runs_dir):
    """W4 D.5: partial_pending_user surfaces tex + flagged claims; UI now
    routes this to its own ui_status so the dedicated 'Verify claims' panel
    can render. Under D.4c this mapped to plain 'verify' as a placeholder."""
    _seed_run(isolated_runs_dir, "run-partial", verdict="partial_pending_user")
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "pending_human_verify"


def test_ui_status_degraded_to_manual_maps_to_verify(client, isolated_runs_dir):
    """W4 D.5: degraded_to_manual is operator-side fallback (Pass 3 itself
    errored) — no per-claim breakdown to act on, so stays on plain 'verify'."""
    _seed_run(isolated_runs_dir, "run-degraded", verdict="degraded_to_manual")
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "verify"


def test_ui_status_failed_still_blocked(client, isolated_runs_dir):
    """Backstop: verdict=failed (not partial/degraded) is still 'blocked'."""
    _seed_run(isolated_runs_dir, "run-failed", verdict="failed")
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "blocked"


def test_detail_404_unknown(client):
    r = client.get("/api/runs/does-not-exist")
    assert r.status_code == 404


def test_detail_returns_state(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-detail", verdict="complete")
    r = client.get("/api/runs/run-detail")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "run-detail"
    assert body["verdict"] == "complete"
    assert body["lens_routing"]["primary_lens"] == "C_product_ops"


def test_every_listed_run_opens_detail_and_has_stable_artifact_state(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-with-tex", verdict="complete", with_tex=True)
    _seed_run(isolated_runs_dir, "run-without-tex", verdict="failed", with_tex=False)

    listed = client.get("/api/runs").json()["runs"]
    assert {r["run_id"] for r in listed} == {"run-with-tex", "run-without-tex"}

    for summary in listed:
        run_id = summary["run_id"]
        detail = client.get(f"/api/runs/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["run_id"] == run_id

    assert client.get("/api/runs/run-with-tex/tex").status_code == 200
    missing_tex = client.get("/api/runs/run-without-tex/tex")
    missing_pdf = client.get("/api/runs/run-without-tex/pdf")
    assert missing_tex.status_code == 404
    assert missing_pdf.status_code == 404


def test_ui_status_ready_when_clean(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-clean", verdict="complete", degradation_count=0)
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "ready"
    assert summary["degradation_count"] == 0


def test_ui_status_verify_when_degraded(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-degraded", verdict="complete", degradation_count=2)
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "verify"
    assert summary["degradation_count"] == 2


def test_ui_status_blocked_when_failed(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-failed", verdict="failed")
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "blocked"


def test_tex_endpoint_serves_file(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-tex", with_tex=True)
    r = client.get("/api/runs/run-tex/tex")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/x-tex")
    assert "documentclass" in r.text


def test_tex_endpoint_404_when_missing(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-no-tex", with_tex=False)
    r = client.get("/api/runs/run-no-tex/tex")
    assert r.status_code == 404


def test_pdf_endpoint_404_when_no_tex(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-no-tex", with_tex=False)
    r = client.get("/api/runs/run-no-tex/pdf")
    assert r.status_code == 404


# ===== Wave 2.7 per-user namespacing =====


def test_x_user_id_header_routes_to_user_runs(client, monkeypatch, tmp_path):
    """Different X-User-Id values see different runs dirs."""
    fake_root = tmp_path
    user_a_runs = fake_root / "packages/harness/data/users/aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa/runs"
    user_b_runs = fake_root / "packages/harness/data/users/bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb/runs"
    user_a_runs.mkdir(parents=True)
    user_b_runs.mkdir(parents=True)

    from harness.config import config
    monkeypatch.setattr(config, "repo_root", fake_root)

    _seed_run(user_a_runs, "run-of-a")
    _seed_run(user_b_runs, "run-of-b")

    ra = client.get("/api/runs", headers={"X-User-Id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"})
    assert ra.status_code == 200
    a_ids = [r["run_id"] for r in ra.json()["runs"]]
    assert a_ids == ["run-of-a"]

    rb = client.get("/api/runs", headers={"X-User-Id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"})
    assert rb.status_code == 200
    b_ids = [r["run_id"] for r in rb.json()["runs"]]
    assert b_ids == ["run-of-b"]


def test_no_x_user_id_defaults_to_jingwen_default(client, isolated_runs_dir):
    """Backward compat: requests without X-User-Id resolve to default."""
    _seed_run(isolated_runs_dir, "legacy-run")
    r = client.get("/api/runs")  # no header
    assert r.status_code == 200
    assert r.json()["runs"][0]["run_id"] == "legacy-run"


def test_invalid_x_user_id_returns_400(client, isolated_runs_dir):
    r = client.get("/api/runs", headers={"X-User-Id": "../etc/passwd"})
    assert r.status_code == 400


# ===== Wave 4 Step C — lifecycle PATCH endpoint =====


def test_lifecycle_patch_progresses_through_states(client, isolated_runs_dir):
    """tailored → applied → oa → interview → offer (forward chain)."""
    _seed_run(isolated_runs_dir, "run-life", verdict="complete")

    for target in ("applied", "oa", "interview", "offer"):
        r = client.patch(
            "/api/runs/run-life/lifecycle",
            json={"state": target},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["current_state"] == target

    # Final state persisted in state.json
    detail = client.get("/api/runs/run-life").json()
    assert detail["lifecycle"]["current_state"] == "offer"
    # 5 events total (initial isn't seeded by _seed_run; just the 4 transitions)
    assert len(detail["lifecycle"]["events"]) == 4


def test_lifecycle_patch_rejects_invalid_transition(client, isolated_runs_dir):
    """tailored → offer (skipping intermediate states) → 400."""
    _seed_run(isolated_runs_dir, "run-skip", verdict="complete")
    r = client.patch(
        "/api/runs/run-skip/lifecycle",
        json={"state": "offer"},
    )
    assert r.status_code == 400
    assert "tailored" in r.json()["detail"]
    assert "offer" in r.json()["detail"]


def test_lifecycle_patch_rejects_unknown_state(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-unk", verdict="complete")
    r = client.patch(
        "/api/runs/run-unk/lifecycle",
        json={"state": "won_powerball"},
    )
    assert r.status_code == 400


def test_lifecycle_patch_404_unknown_run(client, isolated_runs_dir):
    r = client.patch(
        "/api/runs/nope/lifecycle",
        json={"state": "applied"},
    )
    assert r.status_code == 404


def test_lifecycle_patch_rejects_failed_verdict_run(client, isolated_runs_dir):
    """Failed runs cannot transition through the lifecycle — there's no
    artifact to track. Without this guard the endpoint silently assumes
    current='tailored' and would accept the transition."""
    _seed_run(isolated_runs_dir, "run-failed", verdict="failed")
    r = client.patch(
        "/api/runs/run-failed/lifecycle",
        json={"state": "applied"},
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "failed" in detail
    # v0.6.1: error message updated when allowed-verdict set expanded to
    # include degraded_no_substance. Assert the new wording that lists
    # transitionable verdicts.
    assert "transitionable" in detail


def test_lifecycle_patch_allows_degraded_no_substance_verdict_run(
    client, isolated_runs_dir
):
    """Gate 1 v0.6.1: a run that R-18 demoted to degraded_no_substance still
    has a .tex artifact and may have been manually patched. The user should
    be able to mark it applied/oa/etc. through the lifecycle PATCH. Without
    this allowance the banner says 'Submit disabled' AND the lifecycle is
    bricked — user has no way to track the application at all.
    """
    _seed_run(isolated_runs_dir, "run-deg-ns", verdict="degraded_no_substance")
    r = client.patch(
        "/api/runs/run-deg-ns/lifecycle",
        json={"state": "applied", "channel": "manual"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["current_state"] == "applied"


def test_lifecycle_persists_note_and_channel(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-meta", verdict="complete")
    r = client.patch(
        "/api/runs/run-meta/lifecycle",
        json={"state": "applied", "note": "via referral", "channel": "linkedin"},
    )
    assert r.status_code == 200
    detail = client.get("/api/runs/run-meta").json()
    ev = detail["lifecycle"]["events"][-1]
    assert ev["state"] == "applied"
    assert ev["note"] == "via referral"
    assert ev["channel"] == "linkedin"


def test_lifecycle_state_surfaces_in_summary(client, isolated_runs_dir):
    _seed_run(isolated_runs_dir, "run-sum", verdict="complete")
    client.patch("/api/runs/run-sum/lifecycle", json={"state": "applied"})
    list_resp = client.get("/api/runs").json()
    summary = next(s for s in list_resp["runs"] if s["run_id"] == "run-sum")
    assert summary["lifecycle_state"] == "applied"
    # Lifecycle progression now flows ui_status → "submitted"
    assert summary["ui_status"] == "submitted"


def test_lifecycle_cross_user_isolation(client, monkeypatch, tmp_path):
    """User A cannot transition user B's run."""
    fake_root = tmp_path
    user_a_runs = fake_root / "packages/harness/data/users/aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa/runs"
    user_b_runs = fake_root / "packages/harness/data/users/bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb/runs"
    user_a_runs.mkdir(parents=True)
    user_b_runs.mkdir(parents=True)

    from harness.config import config
    monkeypatch.setattr(config, "repo_root", fake_root)

    _seed_run(user_b_runs, "run-of-b", verdict="complete")

    # User A can't see/mutate B's run.
    r = client.patch(
        "/api/runs/run-of-b/lifecycle",
        json={"state": "applied"},
        headers={"X-User-Id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"},
    )
    assert r.status_code == 404

    # User B can.
    r = client.patch(
        "/api/runs/run-of-b/lifecycle",
        json={"state": "applied"},
        headers={"X-User-Id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"},
    )
    assert r.status_code == 200


# ===== Pre-D.4 hardening — schema gate on PATCH /lifecycle =====


def test_lifecycle_patch_succeeds_with_valid_state(client, isolated_runs_dir):
    """The schema-validation gate on PATCH /lifecycle does not false-positive
    on a normally-seeded run (regression guard for the validate-before-persist
    helper added in api/_validators.py)."""
    _seed_run(isolated_runs_dir, "run-valid", verdict="complete")
    r = client.patch(
        "/api/runs/run-valid/lifecycle",
        json={"state": "applied"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["current_state"] == "applied"


def test_lifecycle_patch_500s_on_corrupted_state(client, isolated_runs_dir):
    """If a state.json is missing required fields (here: `verdict`), the
    PATCH endpoint must refuse to persist further mutations. The pre-write
    schema gate raises 500 — this is a backend-bug signal, not a client
    error, so we surface it loudly.

    Realistically this happens when (a) someone hand-edits state.json,
    (b) a backend bug strips required fields, or (c) D.5's verify-claim
    handler produces a malformed dict. Without the gate the corruption
    silently spreads.
    """
    run_dir = isolated_runs_dir / "run-corrupt"
    run_dir.mkdir(parents=True, exist_ok=True)
    # Hand-write a state with verdict='complete' (so the lifecycle guard at
    # 409 passes) but missing the required `input_ref` field. The endpoint
    # mutates `lifecycle` and then must trip schema validation on write.
    bad_state = {
        "run_id": "run-corrupt",
        "verdict": "complete",
        "tier_assigned": 1,
        "matched_resume_version": "C_product_ops",
        "trace": {
            "perception_events": [],
            "planning_events": [],
            "action_events": [],
            "feedback_events": [],
        },
        "metrics": {"total_tokens": 0, "total_claude_calls": 0, "elapsed_seconds": 0.0},
        "tex_artifact_path": "",
        # NB: no `input_ref` (required by harness-tailor-output)
    }
    (run_dir / "state.json").write_text(json.dumps(bad_state))

    r = client.patch(
        "/api/runs/run-corrupt/lifecycle",
        json={"state": "applied"},
    )
    assert r.status_code == 500, r.text
    assert "invalid state" in r.json()["detail"].lower()
