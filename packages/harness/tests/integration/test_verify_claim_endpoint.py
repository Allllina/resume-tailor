"""Integration tests for Wave 4 D.5 — Pass 3 user-trust surface.

Covers:
- GET  /api/runs/{run_id}/pass3        — serve persisted per-bullet detail
- POST /api/runs/{run_id}/verify-claim — record decisions, flip verdict once all decided
- _derive_ui_status                    — pending_human_verify mapping for partial_pending_user
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ---------------------------- fixtures ----------------------------


@pytest.fixture
def isolated_runs_dir(monkeypatch, tmp_path):
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


def _seed_partial_run(runs_dir: Path, run_id: str, *,
                      unsourced_per_bullet: list[int]) -> Path:
    """Seed a run whose Pass 3 returned partial.

    unsourced_per_bullet: e.g. [2, 1] means bullet "b0" has 2 unsourced claims,
    bullet "b1" has 1. The state.json carries the partial_pending_user verdict
    and an aggregate pass3_trace; pass3.json carries the per-bullet detail.
    """
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    total = sum(unsourced_per_bullet)
    state = {
        "run_id": run_id,
        "input_ref": f"sha256:{run_id}-fake",
        "verdict": "partial_pending_user",
        "tier_assigned": 2,
        "matched_resume_version": "C_product_ops",
        "lens_routing": {"primary_lens": "C_product_ops"},
        "trace": {"perception_events": [], "planning_events": [], "action_events": [], "feedback_events": []},
        "metrics": {"total_tokens": 100, "total_claude_calls": 1, "elapsed_seconds": 1.0},
        "degradation_events": [],
        "tex_artifact_path": str(run_dir / "resume.tex"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pass3_trace": {
            "verdict": "partial",
            "verified_facts_count": 0,
            "unsourced_claims_count": total,
            "ask_user_count": total,
        },
    }
    (run_dir / "state.json").write_text(json.dumps(state))
    (run_dir / "resume.tex").write_text("\\documentclass{article}\\begin{document}hi\\end{document}")

    bullets = []
    for i, n_unsourced in enumerate(unsourced_per_bullet):
        bullets.append({
            "bullet_id": f"b{i}",
            "verdict": "partial" if n_unsourced > 0 else "complete",
            "verified_facts": [],
            "unsourced_claims": [
                {"claim": f"b{i}-claim-{j}", "action": "ask_user", "rationale": "stub"}
                for j in range(n_unsourced)
            ],
            "ask_user": [],
        })
    (run_dir / "pass3.json").write_text(json.dumps(bullets))
    return run_dir


# ---------------------------- ui_status mapping ----------------------------


def test_ui_status_partial_pending_user_maps_to_pending_human_verify(client, isolated_runs_dir):
    """D.5: partial_pending_user → pending_human_verify (was 'verify' under D.4c)."""
    _seed_partial_run(isolated_runs_dir, "run-partial", unsourced_per_bullet=[1])
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "pending_human_verify"


def test_ui_status_degraded_to_manual_stays_verify(client, isolated_runs_dir):
    """D.5: degraded_to_manual is operator-side fallback, not per-claim review,
    so it stays on 'verify' (no per-claim breakdown to act on)."""
    run_dir = isolated_runs_dir / "run-deg"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "run_id": "run-deg",
        "input_ref": "sha256:run-deg-fake",
        "verdict": "degraded_to_manual",
        "lens_routing": {"primary_lens": "C_product_ops"},
        "trace": {"perception_events": [], "planning_events": [], "action_events": [], "feedback_events": []},
        "metrics": {"total_tokens": 100, "total_claude_calls": 1, "elapsed_seconds": 1.0},
        "degradation_events": [],
        "tex_artifact_path": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))
    r = client.get("/api/runs")
    summary = r.json()["runs"][0]
    assert summary["ui_status"] == "verify"


# ---------------------------- GET /pass3 ----------------------------


def test_get_pass3_returns_persisted_bullets_and_log(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-p3", unsourced_per_bullet=[2, 1])
    r = client.get("/api/runs/run-p3/pass3")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    bullets = body["bullets"]
    assert len(bullets) == 2
    assert bullets[0]["bullet_id"] == "b0"
    assert len(bullets[0]["unsourced_claims"]) == 2
    assert bullets[1]["bullet_id"] == "b1"
    assert len(bullets[1]["unsourced_claims"]) == 1
    # First read: log starts empty, but the run_id is filled in so the UI
    # can render against the same shape it gets back after a decision.
    assert body["verification_log"] == {"run_id": "run-p3", "events": []}


def test_get_pass3_includes_prior_decisions(client, isolated_runs_dir):
    """After a decision, the same GET surfaces the event so a page refresh
    doesn't lose 'decided' state on the panel."""
    _seed_partial_run(isolated_runs_dir, "run-p3log", unsourced_per_bullet=[2])
    client.post(
        "/api/runs/run-p3log/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    body = client.get("/api/runs/run-p3log/pass3").json()
    assert len(body["verification_log"]["events"]) == 1
    assert body["verification_log"]["events"][0]["bullet_id"] == "b0"
    assert body["verification_log"]["events"][0]["claim_index"] == 0
    assert body["verification_log"]["events"][0]["decision"] == "approve"


def test_get_pass3_404_when_missing(client, isolated_runs_dir):
    """Legacy / non-Tier-2/3 runs have no pass3.json — endpoint 404s."""
    run_dir = isolated_runs_dir / "run-no-p3"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "run_id": "run-no-p3",
        "input_ref": "sha256:run-no-p3-fake",
        "verdict": "complete",
        "lens_routing": {"primary_lens": "C_product_ops"},
        "trace": {"perception_events": [], "planning_events": [], "action_events": [], "feedback_events": []},
        "metrics": {"total_tokens": 100, "total_claude_calls": 1, "elapsed_seconds": 1.0},
        "degradation_events": [],
        "tex_artifact_path": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))
    r = client.get("/api/runs/run-no-p3/pass3")
    assert r.status_code == 404


def test_get_pass3_404_unknown_run(client):
    r = client.get("/api/runs/nope/pass3")
    assert r.status_code == 404


# ---------------------------- POST /verify-claim ----------------------------


def test_verify_claim_approve_records_event(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v1", unsourced_per_bullet=[2])
    r = client.post(
        "/api/runs/run-v1/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decided_count"] == 1
    assert body["total_unsourced"] == 2
    assert body["all_decided"] is False
    assert body["verdict"] == "partial_pending_user"
    assert body["ui_status"] == "pending_human_verify"

    log = json.loads((isolated_runs_dir / "run-v1" / "verification_log.json").read_text())
    assert log["run_id"] == "run-v1"
    assert len(log["events"]) == 1
    evt = log["events"][0]
    assert evt["bullet_id"] == "b0"
    assert evt["claim_index"] == 0
    assert evt["decision"] == "approve"
    assert evt["claim_snapshot"] == "b0-claim-0"


def test_verify_claim_all_decided_flips_verdict(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v2", unsourced_per_bullet=[2])
    # First decision: still partial.
    r1 = client.post(
        "/api/runs/run-v2/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    assert r1.json()["verdict"] == "partial_pending_user"

    # Second decision: all decided → flips to complete.
    r2 = client.post(
        "/api/runs/run-v2/verify-claim",
        json={"bullet_id": "b0", "claim_index": 1, "decision": "reject"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["all_decided"] is True
    assert body["verdict"] == "complete"
    assert body["ui_status"] in {"ready", "verify", "needs_rewrite"}  # whatever the tier says

    # state.json should now reflect the flip.
    state = json.loads((isolated_runs_dir / "run-v2" / "state.json").read_text())
    assert state["verdict"] == "complete"
    assert state["pass3_trace"]["verdict"] == "complete"
    # A feedback event recording the user-verify completion should be present.
    fb = state.get("trace", {}).get("feedback_events", [])
    assert any(e.get("kind") == "pass3_user_verified" for e in fb)


def test_verify_claim_edit_requires_edited_text(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v3", unsourced_per_bullet=[1])
    r = client.post(
        "/api/runs/run-v3/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "edit"},
    )
    assert r.status_code == 400
    assert "edited_text" in r.json()["detail"]


def test_verify_claim_edit_records_edited_text(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v4", unsourced_per_bullet=[1])
    r = client.post(
        "/api/runs/run-v4/verify-claim",
        json={
            "bullet_id": "b0",
            "claim_index": 0,
            "decision": "edit",
            "edited_text": "rewritten claim text",
            "note": "softened the 20% number",
        },
    )
    assert r.status_code == 200
    log = json.loads((isolated_runs_dir / "run-v4" / "verification_log.json").read_text())
    assert log["events"][0]["edited_text"] == "rewritten claim text"
    assert log["events"][0]["note"] == "softened the 20% number"


def test_verify_claim_unknown_bullet_400(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v5", unsourced_per_bullet=[1])
    r = client.post(
        "/api/runs/run-v5/verify-claim",
        json={"bullet_id": "no-such-bullet", "claim_index": 0, "decision": "approve"},
    )
    assert r.status_code == 400


def test_verify_claim_claim_index_out_of_range_400(client, isolated_runs_dir):
    _seed_partial_run(isolated_runs_dir, "run-v6", unsourced_per_bullet=[1])
    r = client.post(
        "/api/runs/run-v6/verify-claim",
        json={"bullet_id": "b0", "claim_index": 99, "decision": "approve"},
    )
    assert r.status_code == 400


def test_verify_claim_unknown_decision_422(client, isolated_runs_dir):
    """Pydantic rejects decision values outside the enum at body parse time."""
    _seed_partial_run(isolated_runs_dir, "run-v7", unsourced_per_bullet=[1])
    r = client.post(
        "/api/runs/run-v7/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve_with_caveat"},
    )
    assert r.status_code == 422


def test_verify_claim_404_unknown_run(client):
    r = client.post(
        "/api/runs/nope/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    assert r.status_code == 404


def test_verify_claim_404_when_pass3_missing(client, isolated_runs_dir):
    """Run exists but has no pass3.json → can't verify what's not flagged."""
    run_dir = isolated_runs_dir / "run-v8"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "run_id": "run-v8",
        "input_ref": "sha256:run-v8-fake",
        "verdict": "complete",
        "lens_routing": {"primary_lens": "C_product_ops"},
        "trace": {"perception_events": [], "planning_events": [], "action_events": [], "feedback_events": []},
        "metrics": {"total_tokens": 100, "total_claude_calls": 1, "elapsed_seconds": 1.0},
        "degradation_events": [],
        "tex_artifact_path": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }))
    r = client.post(
        "/api/runs/run-v8/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    assert r.status_code == 404


def test_verify_claim_replay_same_decision_is_idempotent_but_logged(client, isolated_runs_dir):
    """User re-clicks Approve on a claim they already decided. The log records
    both events (audit trail), but verdict / decided_count reflect unique
    (bullet_id, claim_index) pairs only."""
    _seed_partial_run(isolated_runs_dir, "run-v9", unsourced_per_bullet=[2])
    client.post(
        "/api/runs/run-v9/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "approve"},
    )
    # Same claim again — log appends, but decided_count stays at 1 of 2.
    r2 = client.post(
        "/api/runs/run-v9/verify-claim",
        json={"bullet_id": "b0", "claim_index": 0, "decision": "reject"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["decided_count"] == 1
    assert body["total_unsourced"] == 2
    log = json.loads((isolated_runs_dir / "run-v9" / "verification_log.json").read_text())
    assert len(log["events"]) == 2
