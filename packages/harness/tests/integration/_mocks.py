"""Shared LLM-mock helpers for Phase 2 integration tests.

Pre-Phase-2 integration tests used `return_value="x"` or short
side_effect lists, relying on each sub-skill to silently fall back when
its LLM response didn't parse. Post-Phase-2, every sub-skill on the
critical path raises `SubSkillUnavailable` on bad responses, so tests
that want the pipeline to run end-to-end must supply realistic JSON
for *every* LLM call.

`make_phase2_llm_mock()` returns an `AsyncMock` whose `.call` dispatches
on the system prompt and returns a minimal-but-valid JSON / text
response per sub-skill. The responses are intentionally generic — tests
that need specific sub-skill outputs should mock those specific calls
directly.

The smart-mock satisfies R-18 by returning `competitiveness_rating =
"above_mid"` from the post_rewrite fit_diagnosis call so a happy-path
test reaches verdict=complete.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

# --------------- Canned responses (designed to pass normalize_*) --------------

_COMPETENCY_FULL = {
    "section_a_role_definition": "Mock role brief: PM at AIGC startup.",
    "section_b_must_have": [
        {"requirement": "AIGC delivery", "evidence_required": "Shipped LLM product"}
    ],
    "section_c_should_have": [
        {"requirement": "Python", "evidence_required": "code samples"}
    ],
    "section_d_keyword_dictionary": {
        "tier_1_must_have": ["AIGC", "LLM"],
        "tier_2_strong_signal": ["RAG", "Agent"],
        "tier_3_supporting": ["Python"],
        "tier_4_action_verbs": ["shipped", "built"],
        "tier_5_negatives": [],
    },
    "section_e_anti_patterns": ["Generic ML hand-wave"],
    "section_f_competition_intel": "Strong AIGC PM market.",
    "section_g_screen_signals": ["AIGC keyword density", "shipped product"],
    "section_h_strategy_implications": {
        "emphasize_most": "AIGC products shipped",
        "top_half_content": "AIGC project bullets",
    },
    "section_i_meta": {"confidence": "high"},
    "flat_summary": {
        "confidence": "high",
        "primary_lens": "C_product_ops",
    },
}

_FIT_DIAGNOSIS_PRE_FULL = {
    "matching_matrix": [
        {
            "jd_requirement": "AIGC delivery",
            "evidence_in_candidate": "Shipped 3 AIGC features at Anker",
            "verdict": "strong_match",
            "bridging_or_closure_plan": "n/a",
            "rewrite_lever": "highlight in Summary",
        }
    ],
    "integrated_assessment": (
        "Candidate has strong AIGC delivery evidence with shipped products. "
        "Above-mid fit for this AIGC PM role; rewrite can lift to high."
    ),
    "optimization_boundary": {
        "what_rewriting_can_solve": ["surface AIGC keywords"],
        "what_rewriting_cannot_solve": [],
        "closure_path": "ship more AIGC; no closure needed",
    },
    "competitiveness_rating": "above_mid",
}

_FIT_DIAGNOSIS_POST_FULL = {
    "hm": {
        "highlights": ["Strong AIGC delivery"],
        "concerns": [],
        "comparison_risk": "low",
    },
    "hrbp": {
        "keyword_hit_rate": 0.85,
        "hard_filter_match": {"degree": True, "years": True, "location": True},
        "advance_decision": "advance",
        "decision_rationale": "Above-mid fit with shipped AIGC products.",
    },
    "competitiveness_rating": "above_mid",
    "radar_6_axis": {
        "skill_fit": {"resume": 0.85, "jd": 0.8, "citation": "Section B"},
        "experience_fit": {"resume": 0.8, "jd": 0.8, "citation": "Section B"},
        "industry_fit": {"resume": 0.9, "jd": 0.85, "citation": "Section C"},
        "level_fit": {"resume": 0.8, "jd": 0.8, "citation": "Section A"},
        "location_fit": {"resume": 1.0, "jd": 1.0, "citation": "n/a"},
        "ats_fit": {"resume": 0.85, "jd": 0.85, "citation": "keyword density"},
    },
    "improvement_suggestions": [
        {"priority": 1, "suggestion": "Add an AIGC project to Summary",
         "effort": "low"}
    ],
}

_GAP_BRIDGING_FULL = {
    "reframe_directives": [],
    "add_suggestions": [],
    "skill_gap_advice": {"honest_gaps": [], "training_recommendations": []},
    "section_ordering": {"experience_section_order": []},
    "confidence": "high",
}

_REWRITE_FULL = {
    "experience_id": "mock-exp",
    "final_category": 1,
    "bullets": [
        {
            "id": "mock-exp-bullet-1",
            "text": "Shipped AIGC content workflow product to 10k users.",
            "claimed_facts": ["Shipped AIGC content workflow"],
        }
    ],
    "disambiguator_parenthetical": None,
    "decision_rationale": "Mock rewrite for tests.",
}


# --------------- Dispatch helper --------------------------------------------


def _route(system: str, user: str) -> str:
    """Return a canned response based on the system prompt's sub-skill identity."""
    if "role-competency analyst" in system:
        return json.dumps(_COMPETENCY_FULL, ensure_ascii=False)
    if "pre_rewrite mode" in system:
        return json.dumps(_FIT_DIAGNOSIS_PRE_FULL, ensure_ascii=False)
    if "post_rewrite mode" in system:
        return json.dumps(_FIT_DIAGNOSIS_POST_FULL, ensure_ascii=False)
    if "gap-bridging-planner" in system:
        return json.dumps(_GAP_BRIDGING_FULL, ensure_ascii=False)
    if "senior resume writer" in system:
        return json.dumps(_REWRITE_FULL, ensure_ascii=False)
    if "BA resume Summary writer" in system:
        return "兼具 BA 思维与 AI 工具实操，3 项目落地 AIGC 内容工作流。"
    if "label" in system.lower() or "tier 1 label" in system.lower():
        return json.dumps({"new_label": "测试标签"}, ensure_ascii=False)
    # Default: text response (covers any remaining LLM caller like pass3
    # verifier which receives per-claim prompts).
    return "ok"


def make_phase2_llm_mock(
    *,
    competency: str | None = None,
    fit_pre: str | None = None,
    fit_post: str | None = None,
    gap_bridging: str | None = None,
    rewrite: str | None = None,
    summary: str | None = None,
    label: str | None = None,
    default: str | None = None,
) -> AsyncMock:
    """Smart LLM mock that returns sub-skill-appropriate responses.

    Use as a drop-in replacement for `AsyncMock()` + `return_value=...` in
    integration tests that want the pipeline to run end-to-end under
    Phase-2 fail-fast rules.

    Optional keyword overrides let a test supply its own canned response
    for a specific sub-skill (e.g. a competency JSON with confidence=low
    to test that the propagated confidence reaches the trace event).
    Unrecognized sub-skill prompts get `default` (or the built-in
    fallback `"ok"`) so unexpected call sites don't fail-fast.
    """
    mock = AsyncMock()

    async def _call(*, system: str, user: str, max_tokens: int, temperature: float):
        # Override-first dispatch; fall through to built-in router.
        if competency is not None and "role-competency analyst" in system:
            return competency
        if fit_pre is not None and "pre_rewrite mode" in system:
            return fit_pre
        if fit_post is not None and "post_rewrite mode" in system:
            return fit_post
        if gap_bridging is not None and "gap-bridging-planner" in system:
            return gap_bridging
        if rewrite is not None and "senior resume writer" in system:
            return rewrite
        if summary is not None and "BA resume Summary writer" in system:
            return summary
        if label is not None and "label" in system.lower():
            return label
        routed = _route(system, user)
        if routed == "ok" and default is not None:
            return default
        return routed

    mock.call = AsyncMock(side_effect=_call)
    return mock


def patched_side_effect_list(
    explicit: list, padding_count: int = 20
) -> list:
    """Wrap an explicit response list with smart-mock padding.

    Use when a test sets `side_effect=[r1, r2, ...]` for the first N
    specific calls and the rest of the pipeline should use defaults.
    The returned list has the explicit responses first, then `padding_count`
    repetitions of a generic valid JSON. Note: this is a less precise
    helper than `make_phase2_llm_mock()` because it can't dispatch on
    sub-skill identity — use the smart mock when possible.
    """
    return list(explicit) + [json.dumps(_COMPETENCY_FULL, ensure_ascii=False)] * padding_count
