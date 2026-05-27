"""Gate 1 / R-18 quality-floor contract tests.

These tests assert PRODUCT BEHAVIOR (per STATUS.md Rule 7), not function
behavior. They drive `run_tier1` end-to-end with the LLM provider mocked at
the LLMProvider.call level so every sub-skill in the PPAF pipeline gets the
same treatment a real LLM outage / a real healthy LLM would produce.

Failure of these tests = the product violates R-18.

Acceptance criteria (sourced from SKILL.md R-18 + 2026-05-12 user decision
to switch from count-based to quality-based):

1. **Healthy LLM run** — `verdict="complete"` ONLY when:
   - `fit_diagnosis_post_rewrite._method ∈ {"llm","llm_partial"}`
   - `fit_diagnosis_post_rewrite.competitiveness_rating ∈ {"above_mid","high"}`
   - `pass3_trace.verdict ∈ {"complete","partial"}`

2. **LLM unreachable run** — every LLM call raises ConnectionError →
   `verdict="degraded_no_substance"` + `substance_check.passes=false` +
   `substance_check.post_rewrite_method="fallback_no_llm"`.

Both tests today are EXPECTED TO FAIL because R-18 implementation
(`compute_substance_check` + loop wiring) is not shipped yet. They become
the regression gate for Gate 1 Phase A.

Mock LLM strategy (per user 2026-05-12 OK on option `f`): inline
`_healthy_llm_dispatcher()` returns realistic JSON keyed on prompt content.
A stub LLM HTTP service would be more faithful but is deferred to a future
test-infra refactor.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from harness.repl.eval import Tier1Tools
from harness.repl.loop import run_tier1


# ---------------------------------------------------------------------------
# Realistic mock LLM dispatcher
# ---------------------------------------------------------------------------


_REALISTIC_RESPONSES = {
    # role-competency-extractor — 9-section A-I model
    "competency": json.dumps({
        "section_a_role_overview": {"summary": "Mid-level analyst"},
        "section_b_critical_responsibilities": {"priorities": ["data analysis"]},
        "section_c_required_capabilities": {
            "tier_1_must_have": ["Python", "SQL", "Excel"],
            "tier_2_strong_advantage": ["Tableau"],
            "tier_3_nice_to_have": ["Looker"],
            "tier_4_red_flags": [],
            "tier_5_ats_keywords": ["python", "sql", "data"],
        },
        "section_d_ats_keywords_5_tier": {
            "tier_1_industry_specific": ["fintech"],
            "tier_2_skill_specific": ["sql", "python", "tableau"],
            "tier_3_action_verbs": ["analyzed", "built"],
            "tier_4_credentials": [],
            "tier_5_buzzwords": ["data-driven"],
        },
        "section_e_disambiguator_signals": {"signals": []},
        "section_f_role_archetype": {"archetype": "data_analyst"},
        "section_g_market_seniority_signals": {"seniority": "mid"},
        "section_h_resume_strategy_implications": {
            "emphasize_most": ["quantitative impact"],
            "top_half_content": ["recent ML projects"],
            "de_emphasize": ["unrelated work"],
        },
        "section_i_limitations_confidence": {"confidence": "high"},
        "flat_summary": "Data analyst role with strong SQL/Python ask",
        "_method": "llm",
    }),
    # fit-diagnosis-engine — pre_rewrite matching matrix
    "fit_diagnosis_pre": json.dumps({
        "sub_skill": "fit-diagnosis-engine",
        "mode": "pre_rewrite",
        "target_market": "mainland-china",
        "ppaf_stage": "planning",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {
            "jd_analysis_id": "jd-1",
            "competency_profile_id": "comp-1",
            "current_resume_hash": None,
        },
        "multi_jd": False,
        "confidence": "high",
        "competitiveness_rating": "above_mid",
        "_method": "llm",
        "matching_matrix": [
            {
                "text": "Python data analysis",
                "evidence": "Built Reddit toxicity pipeline",
                "verdict": "strong_match",
                "source": "section_c_tier_1",
                "bridging_or_closure": "",
            },
        ],
        "integrated_assessment": "Candidate matches well on core data skills",
        "optimization_boundary": {
            "rewriting_can_solve": ["Reframe BERT project as production ML"],
            "rewriting_cannot_solve": [],
        },
    }),
    # fit-diagnosis-engine — post_rewrite (HM + HRBP + radar) — THE key signal for R-18
    "fit_diagnosis_post": json.dumps({
        "sub_skill": "fit-diagnosis-engine",
        "mode": "post_rewrite",
        "target_market": "mainland-china",
        "ppaf_stage": "late_feedback",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {
            "jd_analysis_id": "jd-1",
            "competency_profile_id": "comp-1",
            "current_resume_hash": "abc123",
        },
        "multi_jd": False,
        "confidence": "high",
        "competitiveness_rating": "above_mid",  # KEY — passes R-18 quality floor
        "_method": "llm",
        "hm_review": {
            "highlights": ["Strong Python + data engineering"],
            "concerns": ["Could emphasize stakeholder management more"],
            "comparison_risk": "low",
        },
        "hrbp_review": {
            "keyword_hit_rate": 0.85,
            "hard_filter_match": "pass",
            "advance_decision": "advance",
            "rationale": "Resume hits core ATS terms.",
        },
        "radar_chart": {
            "dims": [
                {"axis": "industry_fit", "score": 0.75, "citation": "Section B"},
                {"axis": "skill_fit", "score": 0.85, "citation": "Section C"},
                {"axis": "seniority_fit", "score": 0.70, "citation": "Section G"},
                {"axis": "ai_fluency", "score": 0.80, "citation": "skills row"},
                {"axis": "market_fit", "score": 0.75, "citation": "market context"},
                {"axis": "truthfulness", "score": 0.95, "citation": "Pass 3"},
            ],
        },
        "improvement_suggestions": ["Add stakeholder mgmt bullet"],
    }),
    # resume-rewrite-engine — 10-section A-J output
    "rewrite": json.dumps({
        "_method": "llm",
        "section_a_anchor_decision": {"anchor": "data-analyst"},
        "section_g_bullets": [
            {
                "experience_id": "06.1-reddit-toxicity",
                "text": "Built Reddit toxicity NLP pipeline processing 3.58M comments",
                "disambiguator_parenthetical": "",
            },
        ],
    }),
    "quality_pass": json.dumps({
        "_method": "llm",
        "schema_version": "1.0",
        "sub_skill": "quality-pass-runner",
        "target_market": "mainland-china",
        "ppaf_stage": "late_feedback",
        "invoked_at": "2026-05-12T00:00:00Z",
        "inputs_signature": {"resume_hash": "abc"},
        "final_resume_text": "...rewritten resume tex...",
        "aggregate_verdict": "complete",
        "pending_user_review_flag": False,
        "confidence": "high",
        "pass_1_keyword_injection": {"verdict": "pass", "_method": "deterministic"},
        "pass_1_5_chinese_readability": {"verdict": "pass", "_method": "llm"},
        "pass_2_ai_taste_removal": {"verdict": "pass", "_method": "llm"},
        "pass_3_truthfulness": {
            "verified_claims_count": 5,
            "unsourced_claims": [],
            "identity_lock_check": "pass",
            "identity_lock_violations": [],
            "verdict": "pass",
        },
    }),
    # summary writer expects a plain string
    "summary": "Data analyst with hands-on Python + SQL building production data pipelines.",
    # label rewriter
    "label": '{"new_label": "Reddit 评论数据治理"}',
}


def _healthy_llm_dispatcher() -> MagicMock:
    """Build an AsyncMock whose .call(system=, user=, ...) inspects prompts
    to pick a realistic response. THE KEY MOCK for the R-18 healthy test:
    fit_diagnosis post_rewrite must return competitiveness_rating='above_mid'
    + _method='llm' for the run to legally pass R-18."""

    async def dispatch(*args, **kwargs):
        prompt = (kwargs.get("system") or "") + " " + (kwargs.get("user") or "")
        s = prompt.lower()
        # Order matters: more specific prompts first
        if "post_rewrite" in s or "post-rewrite" in s or "hm_review" in s or "hrbp" in s:
            return _REALISTIC_RESPONSES["fit_diagnosis_post"]
        if ("matching matrix" in s or "matching_matrix" in s or
                "pre_rewrite" in s or "fit_diagnosis" in s):
            return _REALISTIC_RESPONSES["fit_diagnosis_pre"]
        if "competency" in s or "9-section" in s or "section_a" in s:
            return _REALISTIC_RESPONSES["competency"]
        if "rewrite" in s and "bullet" in s:
            return _REALISTIC_RESPONSES["rewrite"]
        if "quality" in s and "pass" in s:
            return _REALISTIC_RESPONSES["quality_pass"]
        if "label" in s or "project title" in s:
            return _REALISTIC_RESPONSES["label"]
        return _REALISTIC_RESPONSES["summary"]

    mock = MagicMock()
    mock.call = AsyncMock(side_effect=dispatch)
    return mock


def _unreachable_llm() -> MagicMock:
    """Every LLM call raises ConnectionError, matching the dogfood scenario
    that triggered Gate 1 (runs ad16cb31, 8b03dc7e on 2026-05-12)."""
    mock = MagicMock()
    mock.call = AsyncMock(side_effect=ConnectionError("Connection refused"))
    return mock


JD_AIGC = (
    "AIGC 内容产品运营实习生招聘. "
    "生成式 AI / Prompt Engineering / Agent 工作流 / LLM / RAG. "
    "需熟悉用户增长、AB 实验、数据驱动决策、内容审核流程。"
) * 2


# ---------------------------------------------------------------------------
# Contract test 1 — healthy LLM passes R-18 quality floor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
async def test_healthy_llm_run_passes_quality_floor(repo_root):
    """Per R-18 (quality-based, user decision 2026-05-12): a healthy run
    where the LLM is up + fit_diagnosis_post_rewrite emits
    competitiveness_rating='above_mid' + Pass 3 passes → verdict='complete'.

    This is the canonical happy path. If THIS fails, either R-18 logic is
    wrong OR the mock dispatcher isn't covering enough prompts to keep
    post_rewrite on the LLM path.

    NOTE on jd_context: late_feedback.py:60 gates post_rewrite invocation
    on `state.jd_context` being truthy. The production endpoint
    (api/tier1_tailor.py:127) always passes jd_context; tests that drive
    run_tier1 directly must do the same or post_rewrite is skipped (which
    would make this test miss the actual R-18 signal).
    """
    tools = Tier1Tools(
        repo_root=repo_root,
        llm_client=_healthy_llm_dispatcher(),
        policy_gateway=MagicMock(),
    )
    output = await run_tier1(
        jd_text=JD_AIGC,
        target_market="mainland-china",
        repo_root=repo_root,
        tools=tools,
        candidate_names=[],
        jd_context={
            "raw_text": JD_AIGC,
            "target_market": "mainland-china",
            "company_hint": "",
            "role_title_hint": "AIGC 内容产品运营实习生",
            "location_hint": "",
        },
    )

    # Core assertion
    assert output["verdict"] == "complete", (
        f"healthy run should be 'complete' under R-18 quality floor, got "
        f"{output['verdict']!r}. degradation_events: "
        f"{output.get('degradation_events')}"
    )

    # The three R-18 quality signals must read healthy
    post = output.get("fit_diagnosis_post_rewrite") or {}
    assert post.get("_method") in ("llm", "llm_partial"), (
        f"fit_diagnosis_post_rewrite._method must be llm/llm_partial; "
        f"got {post.get('_method')!r}"
    )
    assert post.get("competitiveness_rating") in ("above_mid", "high"), (
        f"competitiveness_rating must be above_mid/high; "
        f"got {post.get('competitiveness_rating')!r}"
    )
    pass3_v = (output.get("pass3_trace") or {}).get("verdict")
    assert pass3_v in ("complete", "partial"), (
        f"pass3_trace.verdict must be complete/partial; got {pass3_v!r}"
    )

    # Post-Gate-1 (v0.6.1) wiring MUST emit substance_check on every run
    # that reaches assemble_output. An absent field means the wiring is
    # broken — fail loud rather than vacuously pass.
    substance = output.get("substance_check")
    assert substance is not None, (
        "Gate 1 wiring must write substance_check to harness-tailor-output. "
        "Missing field = late_feedback.py never called compute_substance_check "
        "OR print.py never plumbed the field."
    )
    assert substance["passes"] is True
    assert substance["post_rewrite_method"] in ("llm", "llm_partial")
    assert substance["competitiveness_rating"] in ("above_mid", "high")
    assert substance["pass3_verdict"] in ("complete", "partial")


# ---------------------------------------------------------------------------
# Contract test 2 — LLM unreachable triggers degraded_no_substance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_unreachable_raises_sub_skill_unavailable(repo_root):
    """Phase 2 (v0.7.0): LLM unreachable is intercepted at the sub-skill
    layer — the first critical sub-skill on the planning path raises
    SubSkillUnavailable, run_tier1 propagates the raise, and the API
    converts it to HTTP 503. The substance_check `degraded_no_substance`
    path no longer handles this case (it was the Gate 1 transitional
    protection; Phase 2 makes it impossible for the LLM-unreachable run
    to reach substance_check).

    Pre-Phase-2 contract (R-18 catches LLM-unreachable via fallback
    detection): preserved in commit history; the v0.6.1 / Gate 1 ship
    point. See docs/plans/2026-05-12-phase2-remove-per-subskill-fallback.md
    Phase 2.E.
    """
    from harness.exceptions import SubSkillUnavailable

    tools = Tier1Tools(
        repo_root=repo_root,
        llm_client=_unreachable_llm(),
        policy_gateway=MagicMock(),
    )
    with pytest.raises(SubSkillUnavailable) as exc:
        await run_tier1(
            jd_text=JD_AIGC,
            target_market="mainland-china",
            repo_root=repo_root,
            tools=tools,
            candidate_names=[],
            jd_context={
                "raw_text": JD_AIGC,
                "target_market": "mainland-china",
                "company_hint": "",
                "role_title_hint": "AIGC 内容产品运营实习生",
                "location_hint": "",
            },
        )
    # The first critical sub-skill on the planning path raises; which one
    # wins depends on the gather() race (competency_extractor or
    # fit_diagnosis_pre_rewrite). Both signal the same condition.
    assert exc.value.sub_skill in {
        "competency_extractor",
        "fit_diagnosis_pre_rewrite",
    }
    assert exc.value.llm_unreachable is True
