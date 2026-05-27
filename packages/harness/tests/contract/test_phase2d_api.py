"""Phase 2.D+E contract tests — simplified substance_check gate.

These test compute_substance_check() directly to assert that:
1. The post_rewrite_method gate is gone (r18_quality_v2).
2. `diagnostic_llm_unreachable` is no longer in the output dict.
3. `method_version` is "r18_quality_v2".
4. SubSkillUnavailable propagates out of the summary_writer block in action.py.
"""
from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from harness.verdict.substance_check import compute_substance_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    *,
    rating: str = "above_mid",
    post_method: str = "llm",
    pass3_verdict: str = "complete",
    degradation_reasons: list[str] | None = None,
) -> object:
    """Duck-typed RunState for unit-testing compute_substance_check."""
    state = types.SimpleNamespace()
    state.fit_diagnosis_post_rewrite = {
        "_method": post_method,
        "competitiveness_rating": rating,
    }
    state.pass3_trace = {"verdict": pass3_verdict}
    state.competency_model = {"_method": "llm"}
    state.fit_diagnosis_pre_rewrite = {"_method": "llm"}
    state.gap_bridging = {"_method": "llm"}
    state.rewrite_engine_output = {"_method": "llm"}
    state.quality_pass_report = {"_method": "llm"}
    state.lens_routing = {"used_llm_fallback": False}
    state.change_cards = []
    # Build degradation events
    events = []
    for reason in (degradation_reasons or []):
        ev = types.SimpleNamespace()
        ev.reason = reason
        events.append(ev)
    state.degradation_events = events
    return state


# ---------------------------------------------------------------------------
# Phase 2.D — post_method gate removed
# ---------------------------------------------------------------------------


def test_fallback_no_llm_now_passes_quality_floor():
    """r18_quality_v2: post_method=fallback_no_llm no longer blocks passes.

    This is the decisive Phase 2.D change — under v1, a run where
    post_rewrite fell back would be demoted even if rating was above_mid.
    Under v2, such runs are unreachable in production (SubSkillUnavailable
    → 503), so the gate is removed. This test proves the removal.
    """
    state = _make_state(
        rating="above_mid",
        post_method="fallback_no_llm",
        pass3_verdict="complete",
    )
    result = compute_substance_check(state)
    assert result["passes"] is True, (
        "fallback_no_llm post_method must no longer block passes under r18_quality_v2"
    )


def test_passes_requires_rating_above_mid_or_high():
    for good_rating in ("above_mid", "high"):
        state = _make_state(rating=good_rating, pass3_verdict="complete")
        assert compute_substance_check(state)["passes"] is True, f"rating={good_rating} should pass"
    for bad_rating in ("mid", "below_mid", "low", "unknown"):
        state = _make_state(rating=bad_rating, pass3_verdict="complete")
        assert compute_substance_check(state)["passes"] is False, f"rating={bad_rating} should fail"


def test_passes_requires_pass3_complete_or_partial():
    for good_p3 in ("complete", "partial"):
        state = _make_state(rating="above_mid", pass3_verdict=good_p3)
        assert compute_substance_check(state)["passes"] is True, f"pass3={good_p3} should pass"
    for bad_p3 in ("failed", "absent"):
        state = _make_state(rating="above_mid", pass3_verdict=bad_p3)
        assert compute_substance_check(state)["passes"] is False, f"pass3={bad_p3} should fail"


# ---------------------------------------------------------------------------
# Phase 2.E — method_version + no diagnostic_llm_unreachable
# ---------------------------------------------------------------------------


def test_method_version_is_v2():
    result = compute_substance_check(_make_state())
    assert result["method_version"] == "r18_quality_v2"


def test_diagnostic_llm_unreachable_absent():
    """diagnostic_llm_unreachable must NOT appear in the output dict (Phase 2.E)."""
    result = compute_substance_check(_make_state())
    assert "diagnostic_llm_unreachable" not in result, (
        "diagnostic_llm_unreachable was removed in Phase 2.E; "
        "should not appear in compute_substance_check output"
    )


def test_connection_error_degradations_no_longer_affect_passes():
    """Even with many ConnectionError-reason degradation events, passes is
    determined only by rating + pass3_verdict. The LLM-down heuristic is gone.
    """
    state = _make_state(
        rating="above_mid",
        pass3_verdict="complete",
        degradation_reasons=[
            "Connection error: refused",
            "Circuit open",
            "Connection reset by peer",
        ],
    )
    result = compute_substance_check(state)
    assert result["passes"] is True
    assert "diagnostic_llm_unreachable" not in result


def test_post_rewrite_method_still_in_output():
    """post_rewrite_method is still returned for observability, just not gating."""
    state = _make_state(post_method="llm_partial")
    result = compute_substance_check(state)
    assert result["post_rewrite_method"] == "llm_partial"


def test_change_card_count_in_output():
    state = _make_state()
    state.change_cards = [{"title": "A"}, {"title": "B"}]
    result = compute_substance_check(state)
    assert result["diagnostic_change_card_count"] == 2


# ---------------------------------------------------------------------------
# Phase 2.E — SubSkillUnavailable propagates from summary_writer (action.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_writer_sub_skill_unavailable_propagates(repo_root):
    """action.py must re-raise SubSkillUnavailable from the summary_writer block.

    Previously the catch was `except Exception → add_degradation`, which
    swallowed SubSkillUnavailable. Phase 2.E narrows the catch to re-raise it.
    """
    from harness.exceptions import SubSkillUnavailable
    from harness.repl.eval import Tier1Tools
    from harness.repl.loop import run_tier1
    import json

    # Build a mock LLM that passes early sub-skills (competency + pre + gap +
    # rewrite + pass3) but fails on summary_writer. We detect summary_writer
    # by checking if the prompt mentions "summary" without any of the earlier
    # discriminators.
    _POST = json.dumps({
        "sub_skill": "fit-diagnosis-engine",
        "mode": "post_rewrite",
        "target_market": "mainland-china",
        "ppaf_stage": "late_feedback",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {"jd_analysis_id": "jd-1", "competency_profile_id": "cp-1", "current_resume_hash": "h1"},
        "multi_jd": False,
        "confidence": "high",
        "competitiveness_rating": "above_mid",
        "_method": "llm",
        "hm_review": {"highlights": [], "concerns": [], "comparison_risk": "low"},
        "hrbp_review": {"keyword_hit_rate": 0.8, "hard_filter_match": "pass", "advance_decision": "advance", "rationale": "ok"},
        "radar_chart": {"dims": [
            {"axis": "industry_fit", "score": 0.7, "citation": "B"},
            {"axis": "skill_fit", "score": 0.8, "citation": "C"},
            {"axis": "seniority_fit", "score": 0.7, "citation": "G"},
            {"axis": "ai_fluency", "score": 0.7, "citation": "skills"},
            {"axis": "market_fit", "score": 0.7, "citation": "market"},
            {"axis": "truthfulness", "score": 0.9, "citation": "Pass 3"},
        ]},
        "improvement_suggestions": [],
    })

    _COMPETENCY = json.dumps({
        "section_a_role_overview": {"summary": "Analyst"},
        "section_b_critical_responsibilities": {"priorities": ["analysis"]},
        "section_c_required_capabilities": {
            "tier_1_must_have": ["Python"],
            "tier_2_strong_advantage": [],
            "tier_3_nice_to_have": [],
            "tier_4_red_flags": [],
            "tier_5_ats_keywords": ["python"],
        },
        "section_d_ats_keywords_5_tier": {
            "tier_1_industry_specific": [],
            "tier_2_skill_specific": ["python"],
            "tier_3_action_verbs": ["built"],
            "tier_4_credentials": [],
            "tier_5_buzzwords": [],
        },
        "section_e_disambiguator_signals": {"signals": []},
        "section_f_role_archetype": {"archetype": "analyst"},
        "section_g_market_seniority_signals": {"seniority": "mid"},
        "section_h_resume_strategy_implications": {
            "emphasize_most": ["impact"],
            "top_half_content": [],
            "de_emphasize": [],
        },
        "section_i_limitations_confidence": {"confidence": "high"},
        "flat_summary": "Analyst role",
        "_method": "llm",
    })

    _PRE = json.dumps({
        "sub_skill": "fit-diagnosis-engine",
        "mode": "pre_rewrite",
        "target_market": "mainland-china",
        "ppaf_stage": "planning",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {"jd_analysis_id": "jd-1", "competency_profile_id": "cp-1", "current_resume_hash": None},
        "multi_jd": False,
        "confidence": "high",
        "competitiveness_rating": "above_mid",
        "_method": "llm",
        "matching_matrix": [],
        "integrated_assessment": "ok",
        "optimization_boundary": {"rewriting_can_solve": [], "rewriting_cannot_solve": []},
    })

    _QUALITY = json.dumps({
        "_method": "llm",
        "schema_version": "1.0",
        "sub_skill": "quality-pass-runner",
        "target_market": "mainland-china",
        "ppaf_stage": "late_feedback",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {"resume_hash": "abc"},
        "final_resume_text": "...",
        "aggregate_verdict": "complete",
        "pending_user_review_flag": False,
        "confidence": "high",
        "pass_1_keyword_injection": {"verdict": "pass", "_method": "deterministic"},
        "pass_1_5_chinese_readability": {"verdict": "pass", "_method": "llm"},
        "pass_2_ai_taste_removal": {"verdict": "pass", "_method": "llm"},
        "pass_3_truthfulness": {
            "verified_claims_count": 3,
            "unsourced_claims": [],
            "identity_lock_check": "pass",
            "identity_lock_violations": [],
            "verdict": "pass",
        },
    })

    async def dispatch(*args, **kwargs):
        prompt = (kwargs.get("system") or "") + " " + (kwargs.get("user") or "")
        s = prompt.lower()
        if "post_rewrite" in s or "hm_review" in s or "hrbp" in s:
            return _POST
        if "matching matrix" in s or "matching_matrix" in s or "pre_rewrite" in s or "fit_diagnosis" in s:
            return _PRE
        if "competency" in s or "9-section" in s or "section_a" in s:
            return _COMPETENCY
        if "quality" in s and "pass" in s:
            return _QUALITY
        if "label" in s or "project title" in s:
            return '{"new_label": "Test"}'
        # Summary writer — raise SubSkillUnavailable
        raise SubSkillUnavailable(
            sub_skill="summary_writer",
            reason="Connection refused",
            llm_unreachable=True,
        )

    mock = MagicMock()
    mock.call = AsyncMock(side_effect=dispatch)

    tools = Tier1Tools(
        repo_root=repo_root,
        llm_client=mock,
        policy_gateway=MagicMock(),
    )

    JD = "data analyst role requiring Python and SQL experience"
    with pytest.raises(SubSkillUnavailable) as exc:
        await run_tier1(
            jd_text=JD,
            target_market="mainland-china",
            repo_root=repo_root,
            tools=tools,
            candidate_names=[],
            jd_context={
                "raw_text": JD,
                "target_market": "mainland-china",
                "company_hint": "",
                "role_title_hint": "Data Analyst",
                "location_hint": "",
            },
        )
    assert exc.value.sub_skill == "summary_writer"
