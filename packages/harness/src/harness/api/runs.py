"""GET /api/runs + /api/runs/{run_id} + /tex + /pdf endpoints.

Reads run snapshots from data/users/{user_id}/runs/<run_id>/state.json
(harness-tailor-output shape) and serves list/detail/artifact views.
ui_status pre-computed per run-summary.schema.json rule so the UI does
not need to interpret events.

Wave 2.7: per-user namespacing via X-User-Id header (default
default for backward compat).
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from harness.api._validators import (
    validate_state_for_persist,
    validate_verification_log_for_persist,
)
from harness.config import config
from harness.lifecycle import LIFECYCLE_STATES, apply_transition
from harness.pdf.compiler import CompileError, PdfToolchainUnavailable, compile_tex_to_pdf
from harness.repl.narration import generate_narration
from harness.users.storage import InvalidUserIdError, UserStorage


router = APIRouter()

_DEFAULT_USER_ID = "default"


def _resolve_runs_dir(x_user_id: Optional[str]) -> Path:
    user_id = x_user_id or _DEFAULT_USER_ID
    storage = UserStorage(config.repo_root)
    try:
        return storage.runs_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _derive_ui_status(state: dict) -> str:
    """Derive UI status per run-summary.schema.json rule.

    Wave 4 Step C: lifecycle progression takes precedence — once the user
    marks a run as applied/oa/interview/etc. it renders as "submitted" in
    the inbox regardless of underlying tier.

    Wave 4 Step A: prefers confidence_tier (which already factors in
    degradations + lens routing confidence). Falls back to legacy
    degradation-based logic when match_scores absent (older runs).

    lifecycle ∈ {applied,oa,interview,rejected,offer,archived} → submitted
    lifecycle = dismissed                       → blocked
    submit_audit.outcome=submitted              → submitted (Wave 3)
    verdict=failed                              → blocked
    confidence_tier=ready_to_go                 → ready
    confidence_tier=review_recommended          → verify
    confidence_tier=needs_deep_rewrite          → needs_rewrite
    no match_scores: complete + degradations=[] → ready
    no match_scores: complete + degradations>0  → verify
    """
    lifecycle_state = (state.get("lifecycle") or {}).get("current_state")
    if lifecycle_state in {"applied", "oa", "interview", "rejected", "offer", "archived"}:
        return "submitted"
    if lifecycle_state == "dismissed":
        return "blocked"  # discarded; render same as failed for now

    if state.get("submit_audit", {}).get("outcome") == "submitted":
        return "submitted"
    verdict = state.get("verdict")
    if verdict == "failed":
        return "blocked"
    # Wave 4 D.5: partial_pending_user gets its own ui_status so the run-detail
    # page renders the per-claim verify panel (and the Inbox card icon reads as
    # a user action, not a generic "verify" caution). degraded_to_manual stays
    # on plain "verify" — Pass 3 itself errored, so there's no per-claim
    # breakdown to act on; user just inspects the .tex by hand.
    if verdict == "partial_pending_user":
        return "pending_human_verify"
    # Gate 1 v0.6.1 / R-18: degraded_no_substance means the run produced .tex
    # but failed the substance floor (LLM fallback / low competitiveness_rating
    # / pass3 absent). UI must render the dedicated banner + disable Submit.
    if verdict == "degraded_no_substance":
        return "degraded_no_substance"
    if verdict == "degraded_to_manual":
        return "verify"
    if verdict != "complete":
        return "blocked"

    tier = (state.get("match_scores") or {}).get("confidence_tier")
    if tier == "ready_to_go":
        return "ready"
    if tier == "review_recommended":
        return "verify"
    if tier == "needs_deep_rewrite":
        return "needs_rewrite"

    # Legacy fallback: no match_scores in state.json (older runs)
    return "verify" if state.get("degradation_events") else "ready"


def _load_state(runs_dir: Path, run_id: str) -> dict | None:
    state_path = runs_dir / run_id / "state.json"
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"corrupt state.json for {run_id}: {e}")
        return None


def _to_summary(state: dict) -> dict:
    jd = state.get("jd_context") or {}
    summary = {
        "run_id": state["run_id"],
        "created_at": state.get("created_at", ""),
        "verdict": state.get("verdict", "failed"),
        "ui_status": _derive_ui_status(state),
        "narration": generate_narration(state),
        "degradation_count": len(state.get("degradation_events") or []),
    }
    primary_lens = (state.get("lens_routing") or {}).get("primary_lens")
    if primary_lens:
        summary["primary_lens"] = primary_lens
    # Wave 4 D.3 / 2026-05-07 dogfood — Inbox cards need tier badge + master
    # indicator without per-card detail fetches.
    if state.get("tier_assigned") is not None:
        summary["tier_assigned"] = state["tier_assigned"]
    if state.get("matched_resume_version"):
        summary["matched_resume_version"] = state["matched_resume_version"]
    for k in ("role_title_hint", "company_hint", "location_hint"):
        if jd.get(k):
            summary[k] = jd[k]
    match = state.get("match_scores") or {}
    if match.get("confidence_tier"):
        summary["confidence_tier"] = match["confidence_tier"]
    if match.get("resume_match_score") is not None:
        summary["resume_match_score"] = match["resume_match_score"]
    lifecycle_state = (state.get("lifecycle") or {}).get("current_state")
    if lifecycle_state:
        summary["lifecycle_state"] = lifecycle_state
    return summary


@router.get("/api/runs")
async def list_runs(x_user_id: Optional[str] = Header(default=None)):
    runs_dir = _resolve_runs_dir(x_user_id)
    if not runs_dir.exists():
        return {"runs": [], "total": 0}
    summaries = []
    for state_file in runs_dir.glob("*/state.json"):
        state = _load_state(runs_dir, state_file.parent.name)
        if state is not None:
            try:
                summaries.append(_to_summary(state))
            except Exception as e:
                logger.warning(f"summary failed for {state_file.parent.name}: {e}")
    summaries.sort(key=lambda s: s.get("created_at") or "", reverse=True)
    return {"runs": summaries, "total": len(summaries)}


@router.get("/api/runs/{run_id}")
async def get_run(
    run_id: str,
    x_user_id: Optional[str] = Header(default=None),
):
    runs_dir = _resolve_runs_dir(x_user_id)
    state = _load_state(runs_dir, run_id)
    if state is None:
        raise HTTPException(404, f"run {run_id} not found")
    return state


@router.get("/api/runs/{run_id}/tex")
async def get_tex(
    run_id: str,
    x_user_id: Optional[str] = Header(default=None),
):
    runs_dir = _resolve_runs_dir(x_user_id)
    tex_path = runs_dir / run_id / "resume.tex"
    if not tex_path.exists():
        raise HTTPException(404, f"resume.tex not found for run {run_id}")
    return FileResponse(str(tex_path), media_type="text/x-tex; charset=utf-8")


@router.get("/api/runs/{run_id}/pdf")
async def get_pdf(
    run_id: str,
    x_user_id: Optional[str] = Header(default=None),
):
    runs_dir = _resolve_runs_dir(x_user_id)
    tex_path = runs_dir / run_id / "resume.tex"
    if not tex_path.exists():
        raise HTTPException(404, f"resume.tex not found for run {run_id}")
    try:
        pdf_path = await compile_tex_to_pdf(tex_path)
    except PdfToolchainUnavailable as e:
        # 503: environmental, not a bad .tex. UI shows a clear setup hint +
        # .tex download instead of rendering the error body as garbage.
        logger.warning(f"pdf toolchain unavailable for {run_id}: {e}")
        raise HTTPException(
            503, detail={"code": "pdf_toolchain_unavailable", "message": str(e)}
        )
    except CompileError as e:
        logger.warning(f"pdf compile failed for {run_id}: {e}")
        raise HTTPException(
            500, detail={"code": "pdf_compile_failed", "message": f"PDF compile failed: {e}"}
        )
    return FileResponse(str(pdf_path), media_type="application/pdf")


# ===== Wave 4 Step C — lifecycle PATCH endpoint =====


class LifecycleTransitionRequest(BaseModel):
    """User-driven transition payload for PATCH /api/runs/{run_id}/lifecycle.

    `state` must be a member of LIFECYCLE_STATES. Cross-state validity is
    enforced by harness.lifecycle.apply_transition; invalid transitions
    return HTTP 400.
    """

    state: str
    note: str | None = None
    channel: str | None = None


@router.patch("/api/runs/{run_id}/lifecycle")
async def update_lifecycle(
    run_id: str,
    req: LifecycleTransitionRequest,
    x_user_id: Optional[str] = Header(default=None),
):
    if req.state not in LIFECYCLE_STATES:
        raise HTTPException(
            400,
            f"unknown lifecycle state: {req.state!r}. "
            f"Allowed: {list(LIFECYCLE_STATES)}",
        )

    runs_dir = _resolve_runs_dir(x_user_id)
    state = _load_state(runs_dir, run_id)
    if state is None:
        raise HTTPException(404, f"run {run_id} not found")

    # WHY: runs that produced a .tex artifact AND that the user has had a
    # chance to inspect can be transitioned through the lifecycle. That
    # includes both "complete" (R-18 passed) AND "degraded_no_substance"
    # (R-18 failed but .tex exists; user may have manually patched the
    # .tex and still want to track the application). Failed / user_aborted
    # have no .tex and are NOT transitionable. partial_pending_user must
    # be resolved via /verify-claim first (which flips verdict to complete
    # once all unsourced claims are decided); degraded_to_manual means
    # Pass 3 itself crashed and the run needs human intervention before
    # it belongs in the tailored funnel.
    _TRANSITIONABLE_VERDICTS = {"complete", "degraded_no_substance"}
    if state.get("verdict") not in _TRANSITIONABLE_VERDICTS:
        raise HTTPException(
            409,
            f"cannot transition lifecycle for run with verdict={state.get('verdict')!r}; "
            f"only verdicts {sorted(_TRANSITIONABLE_VERDICTS)} are transitionable",
        )

    current = (state.get("lifecycle") or {}).get("current_state", "tailored")
    try:
        event = apply_transition(
            current,  # type: ignore[arg-type]
            req.state,  # type: ignore[arg-type]
            note=req.note,
            channel=req.channel,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    lifecycle = state.get("lifecycle") or {"events": []}
    lifecycle["current_state"] = event["state"]
    lifecycle["events"] = lifecycle.get("events", []) + [event]
    state["lifecycle"] = lifecycle

    # Re-validate the mutated dict against harness-tailor-output before
    # persistence — guards against a backend bug producing a state shape
    # that the UI / summary derivation can't read. 500 on violation;
    # see api/_validators.py for rationale.
    validate_state_for_persist(state, run_id)

    # Atomic write back: write to temp + rename so a crash mid-write doesn't
    # corrupt state.json.
    state_path = runs_dir / run_id / "state.json"
    tmp = runs_dir / run_id / f"state.json.{secrets.token_hex(4)}.tmp"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(state_path)

    return {"ok": True, "current_state": event["state"], "event": event}


# ===== Wave 4 D.5 — Pass 3 user-trust surface =====


def _load_pass3(runs_dir: Path, run_id: str) -> list[dict] | None:
    pass3_path = runs_dir / run_id / "pass3.json"
    if not pass3_path.exists():
        return None
    try:
        data = json.loads(pass3_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"corrupt pass3.json for {run_id}: {e}")
        return None
    return data if isinstance(data, list) else None


def _load_verification_log(runs_dir: Path, run_id: str) -> dict:
    log_path = runs_dir / run_id / "verification_log.json"
    if not log_path.exists():
        return {"run_id": run_id, "events": []}
    try:
        data = json.loads(log_path.read_text())
        if isinstance(data, dict) and "events" in data:
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"corrupt verification_log.json for {run_id}: {e}")
    return {"run_id": run_id, "events": []}


def _atomic_write_json(path: Path, payload: dict | list) -> None:
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(path)


@router.get("/api/runs/{run_id}/pass3")
async def get_pass3(
    run_id: str,
    x_user_id: Optional[str] = Header(default=None),
):
    """Serve per-bullet Pass 3 detail + the user's verification log.

    Returns `{bullets, verification_log}`. The log is empty on first read;
    the UI joins on (bullet_id, claim_index) to render decided rows as
    "✓ approved 2m ago by you" so revisiting a run after refresh stays
    consistent. 404 when pass3.json is absent (legacy / Tier-1 runs)."""
    runs_dir = _resolve_runs_dir(x_user_id)
    if _load_state(runs_dir, run_id) is None:
        raise HTTPException(404, f"run {run_id} not found")
    bullets = _load_pass3(runs_dir, run_id)
    if bullets is None:
        raise HTTPException(404, f"pass3.json not found for run {run_id}")
    log = _load_verification_log(runs_dir, run_id)
    return {"bullets": bullets, "verification_log": log}


class VerifyClaimRequest(BaseModel):
    """Body for POST /api/runs/{run_id}/verify-claim.

    bullet_id + claim_index together identify which unsourced claim the
    user is deciding on. decision must be one of approve / reject / edit.
    edit additionally requires edited_text (validated at endpoint entry,
    not in pydantic, to give a clearer 400).
    """

    bullet_id: str
    claim_index: int
    decision: Literal["approve", "reject", "edit"]
    edited_text: str | None = None
    note: str | None = None


@router.post("/api/runs/{run_id}/verify-claim")
async def verify_claim(
    run_id: str,
    req: VerifyClaimRequest,
    x_user_id: Optional[str] = Header(default=None),
):
    """Record a user decision against a single unsourced claim.

    Appends to runs/<run_id>/verification_log.json. When the unique set of
    decided (bullet_id, claim_index) pairs covers every unsourced claim in
    pass3.json, flips state.verdict from partial_pending_user → complete
    + state.pass3_trace.verdict → complete + emits a feedback event."""
    runs_dir = _resolve_runs_dir(x_user_id)
    state = _load_state(runs_dir, run_id)
    if state is None:
        raise HTTPException(404, f"run {run_id} not found")
    bullets = _load_pass3(runs_dir, run_id)
    if bullets is None:
        raise HTTPException(
            404,
            f"pass3.json not found for run {run_id}; nothing to verify",
        )

    bullet = next(
        (b for b in bullets if isinstance(b, dict) and b.get("bullet_id") == req.bullet_id),
        None,
    )
    if bullet is None:
        raise HTTPException(
            400,
            f"bullet_id {req.bullet_id!r} not present in pass3.json for run {run_id}",
        )
    unsourced = bullet.get("unsourced_claims") or []
    if not (0 <= req.claim_index < len(unsourced)):
        raise HTTPException(
            400,
            f"claim_index {req.claim_index} out of range for bullet {req.bullet_id!r} "
            f"(0..{len(unsourced) - 1 if unsourced else -1})",
        )
    if req.decision == "edit" and not (req.edited_text and req.edited_text.strip()):
        raise HTTPException(400, "decision=edit requires non-empty edited_text")

    claim_obj = unsourced[req.claim_index]
    claim_snapshot = ""
    if isinstance(claim_obj, dict):
        claim_snapshot = str(claim_obj.get("claim") or "")

    log = _load_verification_log(runs_dir, run_id)
    event = {
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "bullet_id": req.bullet_id,
        "claim_index": req.claim_index,
        "claim_snapshot": claim_snapshot,
        "decision": req.decision,
    }
    if req.edited_text is not None:
        event["edited_text"] = req.edited_text
    if req.note is not None:
        event["note"] = req.note
    log["events"] = list(log.get("events") or []) + [event]
    validate_verification_log_for_persist(log, run_id)
    _atomic_write_json(runs_dir / run_id / "verification_log.json", log)

    total_unsourced = sum(
        len(b.get("unsourced_claims") or []) for b in bullets if isinstance(b, dict)
    )
    decided_pairs = {
        (e["bullet_id"], e["claim_index"])
        for e in log["events"]
        if isinstance(e, dict) and "bullet_id" in e and "claim_index" in e
    }
    decided_count = len(decided_pairs)
    all_decided = decided_count >= total_unsourced > 0

    if all_decided and state.get("verdict") == "partial_pending_user":
        state["verdict"] = "complete"
        pass3_trace = state.get("pass3_trace") or {}
        pass3_trace["verdict"] = "complete"
        state["pass3_trace"] = pass3_trace
        trace = state.get("trace") or {}
        feedback_events = list(trace.get("feedback_events") or [])
        feedback_events.append({
            "kind": "pass3_user_verified",
            "decided_count": decided_count,
            "total_unsourced": total_unsourced,
            "at": event["decided_at"],
        })
        trace["feedback_events"] = feedback_events
        state["trace"] = trace
        validate_state_for_persist(state, run_id)
        _atomic_write_json(runs_dir / run_id / "state.json", state)

    return {
        "run_id": run_id,
        "decided_count": decided_count,
        "total_unsourced": total_unsourced,
        "all_decided": all_decided,
        "verdict": state.get("verdict", "failed"),
        "ui_status": _derive_ui_status(state),
    }
