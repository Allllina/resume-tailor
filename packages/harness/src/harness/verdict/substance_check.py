"""Gate 1 / R-18 quality-floor computation.

Reads PPAF run state, returns a `substance_check` dict matching the
`harness-tailor-output.schema.json` substance_check object spec.

Per R-18 (r18_quality_v2), `passes=True` requires:
- `fit_diagnosis_post_rewrite.competitiveness_rating ∈ {"above_mid", "high"}`
- `pass3_trace.verdict ∈ {"complete", "partial"}`

The `post_rewrite._method` gate (r18_quality_v1) is removed: Phase 2.A-C
already raises SubSkillUnavailable → 503 before a run reaches this check,
so `_method="fallback_no_llm"` is unreachable in production.

Diagnostic fields (surfaced for UI banner copy):
- `diagnostic_failed_sub_skills`: sub-skills with `_method="fallback_no_llm"` (legacy; always [] post-Phase-2)
- `diagnostic_change_card_count`: len(state.change_cards) for transparency
"""
from __future__ import annotations

from typing import Any


# Canonical 6 sub-skills R-18 diagnostic surface tracks. The 3 in the actual
# verdict gate (post_rewrite, pass3, competency dependency) plus the rest as
# diagnostic context for the banner.
_SUB_SKILL_FIELDS: tuple[tuple[str, str], ...] = (
    ("competency_model", "role_competency_extractor"),
    ("fit_diagnosis_pre_rewrite", "fit_diagnosis_pre_rewrite"),
    ("fit_diagnosis_post_rewrite", "fit_diagnosis_post_rewrite"),
    ("gap_bridging", "gap_bridging_planner"),
    ("rewrite_engine_output", "resume_rewrite_engine"),
    ("quality_pass_report", "quality_pass_runner"),
)

def _safe_get_method(obj: Any) -> str:
    """Read `_method` from a sub-skill output dict.

    Returns "absent" when the sub-skill didn't run (output is None / not a
    dict). Returns the literal `_method` value otherwise (which may itself
    be "fallback_no_llm" / "llm" / "llm_partial" / "deterministic" / ...).
    """
    if not isinstance(obj, dict):
        return "absent"
    val = obj.get("_method")
    if isinstance(val, str) and val:
        return val
    return "absent"


def compute_substance_check(state: Any) -> dict:
    """Apply R-18 quality floor against the run state.

    Returns a dict shaped per `substance_check` in
    `contracts/schemas/harness-tailor-output.schema.json`. Caller (the
    REPL loop) inspects `passes` and demotes verdict accordingly.

    `state` is the harness.repl.state.RunState pydantic model OR (in
    tests) a duck-typed object exposing the same fields. Both paths read
    via attribute access; integrate-time wiring goes through RunState.
    """
    post = getattr(state, "fit_diagnosis_post_rewrite", None) or {}
    pass3 = getattr(state, "pass3_trace", None) or {}

    post_method = _safe_get_method(post)
    rating = (
        post.get("competitiveness_rating", "unknown")
        if isinstance(post, dict) and post
        else "unknown"
    )
    if rating not in {"high", "above_mid", "mid", "below_mid", "low"}:
        rating = "unknown"

    pass3_verdict_raw = (
        pass3.get("verdict") if isinstance(pass3, dict) and pass3 else None
    )
    if pass3_verdict_raw in {"complete", "partial", "failed"}:
        pass3_verdict = pass3_verdict_raw
    else:
        pass3_verdict = "absent"

    # R-18 gate (v2) — two AND conditions; post_method gate removed (Phase 2.D)
    passes = (
        rating in {"above_mid", "high"}
        and pass3_verdict in {"complete", "partial"}
    )

    # Diagnostic: which canonical sub-skills had _method=fallback_no_llm?
    # Post-Phase-2, critical sub-skills raise SubSkillUnavailable → 503 before
    # reaching here. Infrastructural sub-skills (quality_pass Pass 1.5 / Pass 2,
    # lens_router) intentionally retain graceful-degradation fallback (heuristic
    # output is valid). So this list is [] for critical failures, but may contain
    # "quality_pass_runner" / "lens_router" on LLM-down for infrastructural paths.
    failed_sub_skills: list[str] = []
    for attr, label in _SUB_SKILL_FIELDS:
        value = getattr(state, attr, None)
        if _safe_get_method(value) == "fallback_no_llm":
            failed_sub_skills.append(label)
    lens_routing_obj = getattr(state, "lens_routing", None) or {}
    if isinstance(lens_routing_obj, dict) and lens_routing_obj.get("used_llm_fallback") is True:
        failed_sub_skills.append("lens_router")

    change_card_count = len(getattr(state, "change_cards", None) or [])

    return {
        "passes": passes,
        "competitiveness_rating": rating,
        "post_rewrite_method": post_method,
        "pass3_verdict": pass3_verdict,
        "method_version": "r18_quality_v2",
        "diagnostic_failed_sub_skills": failed_sub_skills,
        "diagnostic_change_card_count": change_card_count,
    }


__all__ = ["compute_substance_check"]
