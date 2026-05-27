"""Unit tests for harness.gap_bridging (gap-bridging-planner backend).

Contract-first tests for SKILL.md Step 5 + 7-1/7-2. All LLM calls are
mocked with AsyncMock; no assets or real backend are used.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from harness.exceptions import SubSkillUnavailable
from harness.gap_bridging import build_gap_bridging_plan, fallback_gap_bridging_plan


def _stub_fit_diagnosis() -> dict:
    return {
        "sub_skill": "fit-diagnosis-engine",
        "mode": "pre_rewrite",
        "target_market": "north-america",
        "ppaf_stage": "planning",
        "invoked_at": "2026-05-10T00:00:00+00:00",
        "inputs_signature": {
            "jd_analysis_id": "jd123",
            "competency_profile_id": "cp123",
            "current_resume_hash": None,
        },
        "multi_jd": False,
        "confidence": "moderate",
        "competitiveness_rating": "mid",
        "_method": "llm",
        "matching_matrix": [
            {
                "text": "Industry research",
                "evidence": "01-kearney.md project 1 covers downstream applications.",
                "verdict": "transferable",
                "source": "section_b_priority",
                "bridging_or_closure": "preferred; reframe industry research angle",
            },
            {
                "text": "Local services growth",
                "evidence": "",
                "verdict": "missing",
                "source": "section_c_tier_2",
                "bridging_or_closure": "preferred; short_term",
            },
        ],
        "integrated_assessment": "Partial fit with one supplement gap.",
        "optimization_boundary": {
            "rewriting_can_solve": ["关键词显化: 行业研究显化"],
            "rewriting_cannot_solve": [
                "本地生活: 缺少本地生活业务经验; supplement",
            ],
        },
        "multi_jd_coverage": None,
        "spread_flag": None,
    }


def _stub_competency_profile(multi_jd: bool = False) -> dict:
    notes = "multi-JD scope: jd_a and jd_b" if multi_jd else "single JD"
    return {
        "flat": {
            "primary_lens": "C_product_ops",
            "scoring_notes": notes,
        },
        "section_b_core_hiring_logic": [{"priority_name": "Industry research"}],
        "section_c_qualification_model": {
            "tier_1_must_have": [{"name": "SQL"}],
            "tier_2_strongly_preferred": [{"name": "local services"}],
            "tier_3_nice_to_have": [],
        },
    }


def _stub_candidate_assets() -> dict:
    return {
        "profile": {"name": "Candidate"},
        "experience_bank_index": {
            "experiences": [
                {"id": "01-kearney.md project 1", "title": "Strategy project"},
                {"id": "02-ai-agent.md", "title": "AI agent project"},
            ]
        },
    }


def _valid_plan_obj() -> dict:
    return {
        "reframe_directives": [
            {
                "matrix_row_id": "4a_row_01",
                "target_experience": "01-kearney.md project 1",
                "target_bullet_id": "kearney_1.1",
                "keyword_to_inject": "industry research",
                "framing_directive": "Surface downstream application research as industry research.",
                "source_evidence": "01-kearney.md project 1 covers downstream applications.",
            }
        ],
        "add_suggestions": [
            {
                "gap_label": "local services",
                "horizon": "short_term",
                "action": "plan_now",
                "suggestion": "Spend 5-7 days writing one local-services case for interview use.",
            },
            {
                "gap_label": "formal internship",
                "horizon": "mid_term",
                "action": "defer",
                "suggestion": "Defer a 1-3 month internship plan beyond this application cycle.",
            },
        ],
        "skill_bar_adjustments": {
            "add_to_bar": [
                {
                    "skill": "SQL",
                    "tier": "A",
                    "placement_row": "technical",
                    "rationale": "Experience trace cites analytics work using SQL.",
                }
            ],
            "remove_from_bar": [{"skill": "Unrelated Tool", "reason": "Low JD relevance."}],
            "do_not_add": [{"skill": "Rust", "reason": "Tier C -- no evidence."}],
        },
        "section_ordering": {
            "experience_section_order": ["01-kearney.md project 1", "02-ai-agent.md"],
            "experience_section_emphasis": [
                {
                    "exp_id": "01-kearney.md project 1",
                    "bullet_count_recommendation": 3,
                    "rationale": "Closest evidence for industry research.",
                }
            ],
            "missing_sections": [
                {
                    "section_name": "language_proficiency",
                    "action": "add",
                    "rationale": "JD asks for bilingual work.",
                }
            ],
        },
        "multi_jd_conflict": {
            "conflicting_directives": [],
            "proposed_resolution": "master_with_jd_specific",
            "rationale": "",
        },
    }


def _valid_plan_json() -> str:
    return json.dumps(_valid_plan_obj(), ensure_ascii=False)


async def _build_with_response(response: str, **overrides: object) -> dict:
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=response)
    params = {
        "fit_diagnosis_pre_rewrite": _stub_fit_diagnosis(),
        "competency_profile": _stub_competency_profile(),
        "candidate_assets": _stub_candidate_assets(),
        "target_market": "north-america",
        "application_timeline": "immediate",
        "llm": mock,
    }
    params.update(overrides)
    return await build_gap_bridging_plan(**params)


@pytest.mark.asyncio
async def test_happy_path_returns_full_valid_plan():
    out = await _build_with_response(_valid_plan_json())
    assert out["_method"] == "llm"
    assert out["sub_skill"] == "gap-bridging-planner"
    assert out["target_market"] == "north-america"
    assert out["ppaf_stage"] == "planning"
    assert out["application_timeline"] == "immediate"
    assert out["inputs_signature"]["fit_diagnosis_id"] != "unknown"
    assert out["inputs_signature"]["competency_profile_id"] != "unknown"
    assert out["confidence"] == "moderate"
    assert out["multi_jd_conflict_flag"] is False
    assert len(out["reframe_directives"]) == 1
    assert out["add_suggestions"][0]["action"] == "plan_now"
    assert out["skill_bar_adjustments"]["add_to_bar"][0]["tier"] == "A"
    assert out["section_ordering"]["experience_section_emphasis"][0]["bullet_count_recommendation"] == 3
    assert out["multi_jd_conflict"]["proposed_resolution"] == "master_with_jd_specific"


@pytest.mark.asyncio
async def test_happy_path_strips_markdown_fences():
    out = await _build_with_response("```json\n" + _valid_plan_json() + "\n```")
    assert out["_method"] == "llm"
    assert out["reframe_directives"][0]["matrix_row_id"] == "4a_row_01"


@pytest.mark.asyncio
async def test_llm_circuitopen_raises_sub_skill_unavailable():
    """Phase 2: transport errors raise SubSkillUnavailable (llm_unreachable=True)."""
    from harness.llm.protocol import CircuitOpen

    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=CircuitOpen("open"))
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_gap_bridging_plan(
            fit_diagnosis_pre_rewrite=_stub_fit_diagnosis(),
            competency_profile=_stub_competency_profile(),
            candidate_assets=_stub_candidate_assets(),
            target_market="north-america",
            llm=mock,
        )
    assert exc.value.sub_skill == "gap_bridging_planner"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_unexpected_runtime_error_propagates():
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await build_gap_bridging_plan(
            fit_diagnosis_pre_rewrite=_stub_fit_diagnosis(),
            competency_profile=_stub_competency_profile(),
            candidate_assets=_stub_candidate_assets(),
            target_market="north-america",
            llm=mock,
        )


@pytest.mark.asyncio
async def test_malformed_json_raises_sub_skill_unavailable():
    """Phase 2: malformed JSON from LLM is a fail-fast (llm_unreachable=False)."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await _build_with_response("not json")
    assert exc.value.sub_skill == "gap_bridging_planner"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_empty_response_raises_sub_skill_unavailable():
    """Phase 2: empty LLM response is a fail-fast (llm_unreachable=False)."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await _build_with_response("")
    assert exc.value.sub_skill == "gap_bridging_planner"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_llm_none_raises_sub_skill_unavailable():
    """Phase 2: missing LLM provider is a fail-fast (llm_unreachable=True)."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_gap_bridging_plan(
            fit_diagnosis_pre_rewrite=_stub_fit_diagnosis(),
            competency_profile=_stub_competency_profile(),
            candidate_assets=_stub_candidate_assets(),
            target_market="mainland-china",
            application_timeline="near",
            llm=None,
        )
    assert exc.value.sub_skill == "gap_bridging_planner"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_invalid_enums_repaired_marked_partial():
    obj = _valid_plan_obj()
    obj["add_suggestions"][0]["horizon"] = "tomorrow"
    obj["add_suggestions"][0]["action"] = "maybe"
    obj["skill_bar_adjustments"]["add_to_bar"][0]["tier"] = "C"
    obj["skill_bar_adjustments"]["add_to_bar"][0]["placement_row"] = "magic"
    obj["section_ordering"]["missing_sections"][0]["action"] = "invent"
    obj["multi_jd_conflict"]["proposed_resolution"] = "split_the_difference"
    out = await _build_with_response(json.dumps(obj))
    assert out["_method"] == "llm_partial"
    assert out["add_suggestions"][0]["horizon"] == "not_closeable"
    assert out["add_suggestions"][0]["action"] == "accept"
    assert out["skill_bar_adjustments"]["add_to_bar"] == []
    assert out["section_ordering"]["missing_sections"][0]["action"] == "acknowledge_absence"
    assert out["multi_jd_conflict"]["proposed_resolution"] == "accept_compromise"


@pytest.mark.asyncio
async def test_missing_top_level_key_repaired_marked_partial():
    obj = _valid_plan_obj()
    del obj["reframe_directives"]
    out = await _build_with_response(json.dumps(obj))
    assert out["_method"] == "llm_partial"
    assert out["reframe_directives"] == []


@pytest.mark.asyncio
async def test_reframe_directive_requires_source_evidence():
    obj = _valid_plan_obj()
    obj["reframe_directives"][0]["source_evidence"] = ""
    out = await _build_with_response(json.dumps(obj))
    assert out["_method"] == "llm_partial"
    assert out["reframe_directives"] == []


@pytest.mark.asyncio
async def test_add_suggestion_action_derived_from_horizon_and_timeline():
    obj = _valid_plan_obj()
    obj["add_suggestions"] = [
        {
            "gap_label": "mid project",
            "horizon": "mid_term",
            "action": "accept",
            "suggestion": "Build a 1-3 month project.",
        }
    ]
    immediate = await _build_with_response(json.dumps(obj), application_timeline="immediate")
    near = await _build_with_response(json.dumps(obj), application_timeline="near")
    assert immediate["_method"] == "llm_partial"
    assert immediate["add_suggestions"][0]["action"] == "defer"
    assert near["add_suggestions"][0]["action"] == "plan_now"


@pytest.mark.asyncio
async def test_section_ordering_boundary_repairs_bad_bullet_count():
    obj = _valid_plan_obj()
    obj["section_ordering"]["experience_section_emphasis"][0]["bullet_count_recommendation"] = 0
    out = await _build_with_response(json.dumps(obj))
    assert out["_method"] == "llm_partial"
    assert out["section_ordering"]["experience_section_emphasis"][0]["bullet_count_recommendation"] == 1


@pytest.mark.asyncio
async def test_multi_jd_conflict_flag_follows_profile_notes_and_conflicts():
    obj = _valid_plan_obj()
    obj["multi_jd_conflict"]["conflicting_directives"] = [
        {"jd_a": "jd_a", "jd_b": "jd_b", "conflict_summary": "Different keyword emphasis."}
    ]
    out = await _build_with_response(
        json.dumps(obj),
        competency_profile=_stub_competency_profile(multi_jd=True),
    )
    assert out["multi_jd_conflict_flag"] is True
    assert out["multi_jd_conflict"]["conflicting_directives"][0]["jd_a"] == "jd_a"


def test_fallback_gap_bridging_plan_shape():
    out = fallback_gap_bridging_plan(
        target_market="hong-kong",
        application_timeline="mid",
        fit_diagnosis_pre_rewrite=_stub_fit_diagnosis(),
        competency_profile=_stub_competency_profile(),
    )
    assert out["_method"] == "fallback_no_llm"
    assert out["sub_skill"] == "gap-bridging-planner"
    assert out["ppaf_stage"] == "planning"
    assert out["target_market"] == "hong-kong"
    assert out["application_timeline"] == "mid"
    assert out["confidence"] == "low"
    assert out["reframe_directives"] == []
    assert out["add_suggestions"] == []
    assert out["skill_bar_adjustments"] == {
        "add_to_bar": [],
        "remove_from_bar": [],
        "do_not_add": [],
    }
    assert out["section_ordering"] == {
        "experience_section_order": [],
        "experience_section_emphasis": [],
        "missing_sections": [],
    }
    assert out["multi_jd_conflict"] == {
        "conflicting_directives": [],
        "proposed_resolution": "accept_compromise",
        "rationale": "",
    }


@pytest.mark.asyncio
async def test_prompt_includes_inputs_timeline_and_schema_terms():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_plan_json())
    await build_gap_bridging_plan(
        fit_diagnosis_pre_rewrite=_stub_fit_diagnosis(),
        competency_profile=_stub_competency_profile(multi_jd=True),
        candidate_assets=_stub_candidate_assets(),
        target_market="mainland-china",
        application_timeline="mid",
        llm=mock,
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    system_prompt = mock.call.call_args.kwargs.get("system", "")
    assert "mainland-china" in user_prompt
    assert "mid" in user_prompt
    assert "matching_matrix" in user_prompt
    assert "01-kearney.md project 1" in user_prompt
    assert "reframe_directives" in user_prompt
    assert "skill_bar_adjustments" in user_prompt
    assert "STRICT JSON" in system_prompt
    assert "gap-bridging-planner" in system_prompt
