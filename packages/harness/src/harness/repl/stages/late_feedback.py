"""Late FEEDBACK stage: Pass 3 verify + artifact write + lifecycle seed + state.json persist."""
import json
import time
from pathlib import Path

from loguru import logger

from ..eval import Tier1Tools
from ..print import assemble_output
from ..state import RunState
from harness.fit_diagnosis import build_diagnosis
from harness.lifecycle import seed_initial
from harness.quality_pass import build_quality_pass_report
from harness.verdict import compute_substance_check
from harness.verify import verify_bullets


async def run_late_feedback(
    state: RunState,
    final_tex: str,
    repo_root: Path,
    runs_root: Path | None,
    started: float,
    tools: Tier1Tools | None = None,
) -> dict:
    """Late FEEDBACK: run Pass 3 (Tier 2/3 only), write resume.tex, seed lifecycle.

    `tools` is optional for backward compat with callers that don't have an
    LLM handle; when None, Pass 3 is skipped and the run proceeds straight
    to artifact write.
    """
    new_tex = final_tex
    if runs_root is None:
        out_dir = repo_root / "packages/harness/data/runs" / str(state.run_id)
    else:
        out_dir = Path(runs_root) / str(state.run_id)

    # Wave 5 P2 — quality-pass-runner Pass 1.5 + Pass 2.
    # Runs before downstream review and Pass 3 so those consumers see the
    # cleaned resume text, per the Step 6.5 pass order.
    if state.jd_context is not None:
        target_market = state.jd_context.get("target_market") or "north-america"
        state.quality_pass_report = await build_quality_pass_report(
            rewritten_resume=new_tex,
            target_market=target_market,
            jd_text=state.jd_context.get("raw_text", ""),
            competency_profile=state.competency_model,
            experience_bank={"experience_selection_trace": state.experience_selection_trace},
            llm=tools.llm if tools is not None else None,
        )
        new_tex = state.quality_pass_report["final_resume_text"]
        state.add_event("feedback", "quality_pass_completed", {
            "aggregate_verdict": state.quality_pass_report.get("aggregate_verdict"),
            "confidence": state.quality_pass_report.get("confidence"),
            "method": state.quality_pass_report.get("_method"),
        })

    # Wave 5 F3 — fit_diagnosis post_rewrite (consumes resume artifact for HM/HRBP review).
    # Per Rule 1.3: build_diagnosis returns shape-valid fallback on every documented LLM
    # failure path; no outer try/except so programmer bugs surface.
    if state.competency_model and state.jd_context and tools is not None:
        state.fit_diagnosis_post_rewrite = await build_diagnosis(
            mode="post_rewrite",
            target_market=(state.jd_context.get("target_market") or "north-america"),
            jd_text=state.jd_context.get("raw_text", ""),
            competency_profile=state.competency_model,
            experience_selection_trace=state.experience_selection_trace,
            lens=(state.lens_routing or {}).get("primary_lens", "C_product_ops"),
            current_resume=new_tex,  # the rewritten .tex available at this point
            llm=tools.llm,
        )
        state.add_event("feedback", "fit_diagnosis_post_rewrite_built", {
            "method": state.fit_diagnosis_post_rewrite.get("_method"),
            "rating": state.fit_diagnosis_post_rewrite.get("competitiveness_rating"),
            "decision": (state.fit_diagnosis_post_rewrite.get("hrbp") or {}).get("advance_decision"),
        })

    # Pass 3 (Wave 4 D.4c) — verify rewritten bullets against raw experience-bank
    # markdown. Skipped when no rewrite_engine_output (Tier 1) or empty
    # section_g_bullets (rewrite engine fell back / Tier 1 stub). Runs BEFORE
    # artifact write so the verdict (partial_pending_user / degraded_to_manual)
    # is part of the run output and lifecycle seeding can branch on it.
    rewrite_out = state.rewrite_engine_output or {}
    bullets = rewrite_out.get("section_g_bullets") or []
    if bullets and tools is not None:
        await _run_pass3(state, bullets, repo_root, out_dir, tools)

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        tex_path = out_dir / "resume.tex"
        tex_path.write_text(new_tex)
        state.tex_artifact_path = str(tex_path)
        # Pass 3 may have already set verdict to partial_pending_user or
        # degraded_to_manual — don't overwrite. Only stamp "complete" when
        # nothing else has claimed the verdict.
        if state.verdict is None:
            state.verdict = "complete"
        state.add_event("feedback", "artifact_written", {"path": str(tex_path)})
    except Exception as e:
        state.add_degradation("feedback", f"artifact write failed: {e}", "no artifact emitted")
        state.verdict = "failed"

    # Gate 1 / R-18 substance floor (v0.6.1) — applied AFTER Pass 3 + artifact
    # write so post_rewrite + pass3 verdicts are both known. Demotes verdict
    # to "degraded_no_substance" when the quality floor isn't met (LLM
    # fallback / competitiveness_rating below above_mid / pass3 absent).
    # Crucially runs only when verdict is currently "complete" — partial_pending_user
    # (Pass 3 partial) and degraded_to_manual (Pass 3 failed) and failed
    # (artifact write crash) are already explicit failure modes and stay as-is.
    substance = compute_substance_check(state)
    state.substance_check = substance
    if not substance["passes"] and state.verdict == "complete":
        state.verdict = "degraded_no_substance"
        state.add_event("feedback", "verdict_demoted_quality_floor", {
            "competitiveness_rating": substance["competitiveness_rating"],
            "post_rewrite_method": substance["post_rewrite_method"],
            "pass3_verdict": substance["pass3_verdict"],
        })

    # Lifecycle seed for completed AND partial_pending_user runs (both go to
    # the Inbox; user reviews + transitions). degraded_to_manual /
    # degraded_no_substance / failed skip the seed — those runs need
    # attention before they belong in the tailored funnel.
    if state.verdict in ("complete", "partial_pending_user") and state.lifecycle is None:
        state.lifecycle = seed_initial("tailored")

    state.metrics["elapsed_seconds"] = time.monotonic() - started
    logger.debug(f"Tier 1 run {state.run_id} verdict={state.verdict} elapsed={state.metrics['elapsed_seconds']:.2f}s")

    output = assemble_output(state)

    # Persist state.json so /api/runs and /api/runs/{id} can serve historical
    # runs without re-running the loop. Best-effort — failure here doesn't
    # invalidate the run; the caller still gets the output dict.
    try:
        if out_dir.exists():
            (out_dir / "state.json").write_text(
                json.dumps(output, ensure_ascii=False, indent=2)
            )
    except Exception as e:
        logger.warning(f"state.json persistence failed for run {state.run_id}: {e}")

    return output


async def _run_pass3(
    state: RunState,
    bullets: list[dict],
    repo_root: Path,
    out_dir: Path,
    tools: Tier1Tools,
) -> None:
    """Run Pass 3 verifier on rewritten bullets; populate state.pass3_trace
    + state.verdict + persist runs/<id>/pass3.json.

    Failure-tolerant: on Pass3VerifyError or any other exception from the
    verifier, sets state.verdict = "degraded_to_manual" and records a
    degradation event but does NOT raise to the orchestrator — the rest
    of FEEDBACK (artifact write, lifecycle decision) still runs.
    """
    state.add_event("feedback", "pass3_started", {"bullet_count": len(bullets)})

    # D11 — prefer the private gitignored raw/ when present; fall through to
    # raw.sample/ on a fresh clone with no real seed.
    raw_real = repo_root / "assets/experience-bank/raw"
    raw_sample = repo_root / "assets/experience-bank/raw.sample"
    raw_dir = raw_real if raw_real.is_dir() and any(raw_real.glob("*.md")) else raw_sample
    source_files = sorted(raw_dir.glob("*.md"))
    rubric_path = repo_root / "assets/knowledge-base/references/workflow/quality-pass.md"

    try:
        results = await verify_bullets(
            bullets=bullets,
            source_files=source_files,
            rubric_path=rubric_path,
            llm=tools.llm,
        )
    except Exception as e:
        state.add_degradation(
            "feedback",
            f"pass 3 verifier failed: {e}",
            "fall back to degraded_to_manual; user must verify the .tex by hand",
        )
        state.verdict = "degraded_to_manual"
        state.pass3_trace = {
            "verdict": "failed",
            "verified_facts_count": 0,
            "unsourced_claims_count": 0,
            "ask_user_count": 0,
        }
        return

    # Aggregate per-bullet verdicts to a run-level verdict.
    run_verdict = _aggregate_pass3(results)
    verified_count = sum(len(r.get("verified_facts", [])) for r in results)
    unsourced_count = sum(len(r.get("unsourced_claims", [])) for r in results)
    ask_user_count = sum(len(r.get("ask_user", [])) for r in results)

    state.pass3_trace = {
        "verdict": run_verdict,
        "verified_facts_count": verified_count,
        "unsourced_claims_count": unsourced_count,
        "ask_user_count": ask_user_count,
    }

    state.add_event(
        "feedback",
        "pass3_completed",
        {
            "verdict": run_verdict,
            "verified_facts_count": verified_count,
            "unsourced_claims_count": unsourced_count,
            "ask_user_count": ask_user_count,
        },
    )

    if run_verdict == "partial":
        state.verdict = "partial_pending_user"
        state.add_event(
            "feedback",
            f"pass3_partial_{ask_user_count}_claims",
            {"ask_user_count": ask_user_count},
        )

    # Persist detailed per-bullet output for UI / audit consumers.
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "pass3.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        # Non-fatal: pass3_trace summary is already on state; just no detail file.
        logger.warning(f"pass3.json persistence failed for run {state.run_id}: {e}")


def _aggregate_pass3(results: list[dict]) -> str:
    """Run-level verdict: failed > partial > complete.

    Empty list → "complete" (vacuously: no bullets to verify means nothing
    to flag). Caller is responsible for not invoking Pass 3 with an empty
    bullet set; this is a safety net.
    """
    if not results:
        return "complete"
    verdicts = [r.get("verdict", "complete") for r in results]
    if "failed" in verdicts:
        return "failed"
    if "partial" in verdicts:
        return "partial"
    return "complete"
