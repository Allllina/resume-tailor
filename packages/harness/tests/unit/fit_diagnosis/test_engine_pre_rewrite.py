"""Unit tests for harness.fit_diagnosis (Wave 5 F1 backend, pre_rewrite mode).

Mirrors the test style of `tests/unit/forecast/test_matrix.py`. All
tests use AsyncMock for the LLM — no real backend, no fixtures, no
assets/ access.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from harness.exceptions import SubSkillUnavailable
from harness.fit_diagnosis import build_diagnosis, fallback_diagnosis
from harness.fit_diagnosis._shared import compute_confidence


# ----------------------------- fixtures -----------------------------


def _valid_section_4_obj(num_rows: int = 8, multi_jd: bool = False) -> dict:
    """Build a Section 4 dict that conforms to the pre_rewrite contract."""
    rows: list[dict] = []
    for i in range(num_rows):
        if i % 3 == 0:
            verdict = "strong_match"
            bridging = ""
        elif i % 3 == 1:
            verdict = "transferable"
            bridging = "preferred; 面试侧重 Columbia + GPA 3.9 抵消专业差异"
        else:
            verdict = "missing"
            bridging = "preferred; long_term"
        rows.append({
            "text": f"Requirement {i + 1}: ship LLM features end-to-end",
            "evidence": f"Past role {i + 1} demonstrates direct experience.",
            "verdict": verdict,
            "source": "section_b_priority" if i < 4 else "section_c_tier_1",
            "bridging_or_closure": bridging,
        })
    obj: dict = {
        "matching_matrix": rows,
        "integrated_assessment": (
            "Strong overall match for the AIGC product role. Biggest "
            "strength is shipped LLM tooling experience. Biggest gap is "
            "limited large-team coordination. Estimated above-mid pool position."
        ),
        "optimization_boundary": {
            "rewriting_can_solve": [
                "关键词显化: 行业研究 / 市场参与者等 4 个核心 keyword 注入 bullet 标题",
                "结构调整: Skills 行重排，prompt engineering 优先",
            ],
            "rewriting_cannot_solve": [
                "无大厂战略 returner: 用 AI Agent 项目对冲差异化; accept",
                "教育背景: 非顶尖商学院; supplement",
            ],
        },
    }
    if multi_jd:
        obj["multi_jd_coverage"] = [
            {"jd_id": "jd_1", "jd_title": "Strategy Manager", "coverage_pct": 80, "note": ""},
            {"jd_id": "jd_2", "jd_title": "Product Lead",     "coverage_pct": 65, "note": "scope mismatch"},
            {"jd_id": "jd_3", "jd_title": "BizOps",           "coverage_pct": 70, "note": ""},
            {"jd_id": "jd_4", "jd_title": "Strategy Lead",    "coverage_pct": 75, "note": ""},
        ]
    return obj


def _valid_section_4_json(num_rows: int = 8, multi_jd: bool = False) -> str:
    return json.dumps(_valid_section_4_obj(num_rows, multi_jd), ensure_ascii=False)


def _stub_competency_profile() -> dict:
    """A 9-section profile (keys-only) — used to mark `competency_complete`."""
    base: dict = {
        "section_b_core_hiring_logic": [
            {
                "priority_name": "Prompt engineering depth",
                "what_it_means": "Designs prompts and evaluates outputs.",
                "why_it_matters": "Quality of LLM features depends on craft.",
                "credible_proof_signals": "Shipped LLM features.",
            }
        ],
        "section_c_qualification_model": {
            "tier_1_must_have": [
                {
                    "name": "Prompt Engineering",
                    "practical_meaning": "Iterates structured prompts.",
                    "credible_proof_signals": "Documented prompt libraries.",
                }
            ],
            "tier_2_strongly_preferred": [],
            "tier_3_nice_to_have": [],
        },
    }
    # Pad to 9 section_* keys for completeness signal.
    for letter in ("a", "d", "e", "f", "g", "h", "i"):
        base[f"section_{letter}_stub"] = {}
    return base


def _stub_experience_trace() -> list[dict]:
    return [
        {
            "experience_id": "exp_aigc_2024",
            "pass_a_tier": "必上展开",
            "pass_b_tier": "必上展开",
            "pass_c_tier": "必上展开",
            "final_category": 1,
        }
    ]


# --------------------------- happy path ---------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_full_valid_diagnosis():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_section_4_json(num_rows=9))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="AIGC 内容产品 招聘. Prompt Engineering Agent LLM RAG.",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm"
    assert out["sub_skill"] == "fit-diagnosis-engine"
    assert out["mode"] == "pre_rewrite"
    assert out["ppaf_stage"] == "planning"
    assert out["target_market"] == "north-america"
    assert out["multi_jd"] is False
    assert out["inputs_signature"]["current_resume_hash"] is None
    assert out["inputs_signature"]["jd_analysis_id"] != "unknown"
    assert out["inputs_signature"]["competency_profile_id"] != "unknown"
    assert len(out["matching_matrix"]) >= 8
    assert "rewriting_can_solve" in out["optimization_boundary"]
    assert "rewriting_cannot_solve" in out["optimization_boundary"]
    assert out["multi_jd_coverage"] is None
    assert out["spread_flag"] is None

    # Spot-check bridging_or_closure constraints.
    for row in out["matching_matrix"]:
        verdict = row["verdict"]
        bridging = row["bridging_or_closure"]
        if verdict == "strong_match":
            assert bridging == ""
        else:
            assert bridging.startswith(("hard;", "preferred;"))


@pytest.mark.asyncio
async def test_happy_path_strips_markdown_fences():
    fenced = "```json\n" + _valid_section_4_json() + "\n```"
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=fenced)
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="mainland-china",
        jd_text="某岗 招聘",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm"
    assert out["target_market"] == "mainland-china"


# --------------------------- failure modes ---------------------------


@pytest.mark.asyncio
async def test_llm_circuitopen_returns_fallback_diagnosis():
    from harness.llm.protocol import CircuitOpen

    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=CircuitOpen("circuit open"))
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_diagnosis(
            mode="pre_rewrite",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=mock,
        )
    assert exc.value.sub_skill == "fit_diagnosis_pre_rewrite"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_unexpected_exception_propagates():
    """RuntimeError / programmer bugs MUST surface — Rule 1.1."""
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await build_diagnosis(
            mode="pre_rewrite",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=mock,
        )


@pytest.mark.asyncio
async def test_malformed_json_returns_fallback():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="Sorry, I cannot comply.")
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_diagnosis(
            mode="pre_rewrite",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=mock,
        )
    assert exc.value.sub_skill == "fit_diagnosis_pre_rewrite"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_empty_response_returns_fallback():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="")
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_diagnosis(
            mode="pre_rewrite",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=mock,
        )
    assert exc.value.sub_skill == "fit_diagnosis_pre_rewrite"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_no_llm_returns_fallback():
    """Passing llm=None goes straight to fallback (defensive)."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await build_diagnosis(
            mode="pre_rewrite",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=None,
        )
    assert exc.value.sub_skill == "fit_diagnosis_pre_rewrite"
    assert exc.value.llm_unreachable is True


# --------------------------- mode handling ---------------------------


@pytest.mark.asyncio
async def test_invalid_mode_raises_value_error():
    mock = AsyncMock()
    with pytest.raises(ValueError, match="pre_rewrite"):
        await build_diagnosis(
            mode="bogus",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_profile(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            llm=mock,
        )


# --------------------------- partial / degraded shapes ---------------------------


@pytest.mark.asyncio
async def test_missing_top_level_matching_matrix_marked_partial():
    obj = _valid_section_4_obj()
    del obj["matching_matrix"]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    assert out["matching_matrix"] == []


@pytest.mark.asyncio
async def test_invalid_verdict_repaired_marked_partial():
    obj = _valid_section_4_obj()
    obj["matching_matrix"][0]["verdict"] = "supercalifragilistic"
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    assert out["matching_matrix"][0]["verdict"] in {
        "strong_match",
        "transferable",
        "missing",
    }


@pytest.mark.asyncio
async def test_missing_bridging_on_transferable_filled_with_placeholder():
    obj = _valid_section_4_obj()
    # Find a transferable row and strip its bridging field.
    target_idx = next(
        i for i, r in enumerate(obj["matching_matrix"]) if r["verdict"] == "transferable"
    )
    obj["matching_matrix"][target_idx]["bridging_or_closure"] = ""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    repaired = out["matching_matrix"][target_idx]["bridging_or_closure"]
    assert repaired.startswith(("hard;", "preferred;"))
    assert len(repaired) > len("preferred;")


@pytest.mark.asyncio
async def test_bridging_on_strong_match_cleared_marked_partial():
    obj = _valid_section_4_obj()
    target_idx = next(
        i for i, r in enumerate(obj["matching_matrix"]) if r["verdict"] == "strong_match"
    )
    obj["matching_matrix"][target_idx]["bridging_or_closure"] = "should be empty"
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    assert out["matching_matrix"][target_idx]["bridging_or_closure"] == ""


@pytest.mark.asyncio
async def test_cannot_solve_missing_closure_path_filled_default():
    obj = _valid_section_4_obj()
    obj["optimization_boundary"]["rewriting_cannot_solve"] = [
        "credential_gap: 缺少顶尖商学院学位",  # no `; supplement|accept`
    ]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    repaired = out["optimization_boundary"]["rewriting_cannot_solve"][0]
    assert repaired.endswith("; accept")


# --------------------------- multi_jd handling ---------------------------


@pytest.mark.asyncio
async def test_multi_jd_true_with_empty_coverage_marked_partial():
    obj = _valid_section_4_obj(multi_jd=False)
    obj["multi_jd_coverage"] = []  # explicitly empty despite multi_jd=True
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        multi_jd=True,
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    assert out["multi_jd"] is True
    assert out["multi_jd_coverage"] == []


@pytest.mark.asyncio
async def test_multi_jd_false_with_coverage_present_cleared_to_none():
    obj = _valid_section_4_obj(multi_jd=True)  # has coverage rows
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        multi_jd=False,
        llm=mock,
    )
    assert out["_method"] == "llm_partial"
    assert out["multi_jd_coverage"] is None
    assert out["spread_flag"] is None


@pytest.mark.asyncio
async def test_multi_jd_true_with_valid_coverage_returns_llm():
    obj = _valid_section_4_obj(multi_jd=True)
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        multi_jd=True,
        llm=mock,
    )
    assert out["_method"] == "llm"
    assert out["multi_jd"] is True
    assert isinstance(out["multi_jd_coverage"], list)
    assert len(out["multi_jd_coverage"]) == 4
    assert out["spread_flag"] is False  # 80-65 = 15, ≤ 30


# --------------------------- confidence ---------------------------


def test_confidence_high_when_all_signals_strong():
    assert (
        compute_confidence(
            jd_count=4,
            competency_complete=True,
            market_loaded=True,
            method="llm",
        )
        == "high"
    )


def test_confidence_moderate_when_partial_signals():
    assert (
        compute_confidence(
            jd_count=2,
            competency_complete=True,
            market_loaded=True,
            method="llm",
        )
        == "moderate"
    )


def test_confidence_low_when_method_is_fallback():
    assert (
        compute_confidence(
            jd_count=4,
            competency_complete=True,
            market_loaded=True,
            method="fallback_no_llm",
        )
        == "low"
    )


def test_confidence_low_when_single_jd_and_no_market():
    assert (
        compute_confidence(
            jd_count=1,
            competency_complete=True,
            market_loaded=False,
            method="llm",
        )
        == "low"
    )


# --------------------------- prompt assembly ---------------------------


@pytest.mark.asyncio
async def test_prompt_includes_jd_lens_section_b_section_c_and_trace():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_section_4_json())
    await build_diagnosis(
        mode="pre_rewrite",
        target_market="mainland-china",
        jd_text="数据分析师岗位 SQL Python",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="B_data_analytics",
        llm=mock,
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    system_prompt = mock.call.call_args.kwargs.get("system", "")
    assert "B_data_analytics" in user_prompt
    assert "数据分析师" in user_prompt
    assert "Prompt engineering depth" in user_prompt          # Section B JSON
    assert "Prompt Engineering" in user_prompt                # Section C JSON
    assert "exp_aigc_2024" in user_prompt                     # experience trace
    assert "mainland-china" in user_prompt                    # target_market
    assert "STRICT JSON" in system_prompt
    assert "fit-diagnosis-engine" in system_prompt


@pytest.mark.asyncio
async def test_prompt_includes_multi_jd_section_when_multi_jd_true():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_section_4_json(multi_jd=True))
    await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="jd",
        competency_profile=_stub_competency_profile(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        multi_jd=True,
        llm=mock,
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    assert "multi_jd_coverage" in user_prompt


# --------------------------- fallback_diagnosis ---------------------------


def test_fallback_diagnosis_shape_pre_rewrite():
    fb = fallback_diagnosis(mode="pre_rewrite", target_market="north-america")
    assert fb["_method"] == "fallback_no_llm"
    assert fb["sub_skill"] == "fit-diagnosis-engine"
    assert fb["mode"] == "pre_rewrite"
    assert fb["ppaf_stage"] == "planning"
    assert fb["matching_matrix"] == []
    assert fb["multi_jd"] is False
    assert fb["multi_jd_coverage"] is None
    assert fb["confidence"] == "low"
    assert fb["competitiveness_rating"] == "mid"
    assert fb["inputs_signature"]["current_resume_hash"] is None


def test_fallback_diagnosis_invalid_mode_raises_value_error():
    with pytest.raises(ValueError, match="pre_rewrite"):
        fallback_diagnosis(mode="bogus", target_market="north-america")
