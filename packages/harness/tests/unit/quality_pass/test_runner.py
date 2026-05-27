"""Unit tests for harness.quality_pass (Pass 1.5 + Pass 2).

Phase A test contract for `quality-pass-runner`:
  - Pass 1.5 Chinese readability runs before Pass 2 for Chinese markets.
  - Pass 2 enforces R-11 AI-tone cleanup with JD-native term protection.
  - LLM is optional and mocked; deterministic rules are the fallback path.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest


def _import_runner():
    from harness.quality_pass.runner import (
        build_quality_pass_report,
        run_pass_1_5,
        run_pass_2,
    )

    return build_quality_pass_report, run_pass_1_5, run_pass_2


def _ai_phrase_terms(result: dict) -> set[str]:
    return {item["original"] for item in result["replacements_applied"]}


def _readability_originals(result: dict) -> set[str]:
    return {item["original"] for item in result["flagged_phrases"]}


@pytest.mark.asyncio
async def test_pass_1_5_happy_path_rewrites_direct_translation():
    _, run_pass_1_5, _ = _import_runner()
    text = "主导技术采用曲线评估，完成TAM/SAM/SOM测算，并输出价值量提升逻辑。"

    out = await run_pass_1_5(text, target_market="mainland-china", llm=None)

    assert out["enabled"] is True
    assert out["verdict"] == "pass"
    assert "技术采用曲线评估" in _readability_originals(out)
    assert "TAM/SAM/SOM" in _readability_originals(out)
    assert "技术成熟度评估" in out["text"]
    assert "市场规模测算（总量/可服务/可获取）" in out["text"]
    assert "价值量提升逻辑" not in out["text"]


@pytest.mark.asyncio
async def test_pass_1_5_skips_non_chinese_markets():
    _, run_pass_1_5, _ = _import_runner()
    text = "Spearheaded GTM analysis and built market sizing model."

    out = await run_pass_1_5(text, target_market="north-america", llm=None)

    assert out["enabled"] is False
    assert out["verdict"] == "pass"
    assert out["text"] == text
    assert out["flagged_phrases"] == []


@pytest.mark.asyncio
async def test_pass_1_5_empty_input_returns_shape_valid_pass():
    _, run_pass_1_5, _ = _import_runner()

    out = await run_pass_1_5("", target_market="mainland-china", llm=None)

    assert out["_method"] == "fallback_no_llm"
    assert out["enabled"] is True
    assert out["text"] == ""
    assert out["flagged_phrases"] == []
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_1_5_clean_input_is_idempotent():
    _, run_pass_1_5, _ = _import_runner()
    text = "为消费品客户制定渠道增长策略，基于门店数据评估区域机会。"

    out = await run_pass_1_5(text, target_market="mainland-china", llm=None)

    assert out["text"] == text
    assert out["flagged_phrases"] == []
    assert out["preserved_english_terms"] == []
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_1_5_preserves_standard_technical_english_terms():
    _, run_pass_1_5, _ = _import_runner()
    text = "使用 Python、SQL、BERT 与 LangGraph 搭建实验流程，并跟踪 ROI。"

    out = await run_pass_1_5(text, target_market="mainland-china", llm=None)

    assert out["text"] == text
    preserved = {item["term"] for item in out["preserved_english_terms"]}
    assert {"Python", "SQL", "BERT", "LangGraph", "ROI"} <= preserved
    assert out["flagged_phrases"] == []


@pytest.mark.asyncio
async def test_pass_1_5_llm_degraded_falls_back_to_deterministic_rules():
    _, run_pass_1_5, _ = _import_runner()
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=asyncio.TimeoutError())

    out = await run_pass_1_5(
        "通过对业务需求和媒体渠道的了解制定系统和产品优化策略。",
        target_market="hong-kong",
        llm=mock,
    )

    assert out["_method"] == "fallback_no_llm"
    assert "基于业务需求和渠道特点制定优化策略" in out["text"]
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_1_5_real_readability_issue_gets_fixed():
    _, run_pass_1_5, _ = _import_runner()
    text = "完成TAM/SAM/SOM测算，识别开放进入空间并输出赛道选择建议。"

    out = await run_pass_1_5(text, target_market="mainland-china", llm=None)

    assert "TAM/SAM/SOM" not in out["text"]
    assert "开放进入空间" not in out["text"]
    assert "赛道选择建议" not in out["text"]
    assert "仍处于分散竞争阶段" in out["text"]
    assert "赛道优先级建议" in out["text"]


@pytest.mark.asyncio
async def test_pass_2_happy_path_replaces_english_ai_tone_phrases():
    _, _, run_pass_2 = _import_runner()
    text = "Spearheaded a comprehensive initiative that leveraged actionable insights."

    out = await run_pass_2(text, jd_text="", target_market="north-america", llm=None)

    assert out["verdict"] == "pass"
    assert {"Spearheaded", "comprehensive", "leveraged", "actionable insights"} <= _ai_phrase_terms(out)
    assert "Led" in out["text"]
    assert "complete" in out["text"]
    assert "Used" in out["text"]
    assert "findings" in out["text"]


@pytest.mark.asyncio
async def test_pass_2_happy_path_replaces_chinese_ai_tone_phrases():
    _, _, run_pass_2 = _import_runner()
    text = "深度赋能业务团队，打通闭环并拉齐策略颗粒度。"

    out = await run_pass_2(text, jd_text="", target_market="mainland-china", llm=None)

    assert out["verdict"] == "pass"
    assert {"深度赋能", "打通闭环", "拉齐", "颗粒度"} <= _ai_phrase_terms(out)
    assert "支持业务团队" in out["text"]
    assert "完成" in out["text"] or "覆盖全流程" in out["text"]
    assert "对齐" in out["text"]
    assert "细节" in out["text"]


@pytest.mark.asyncio
async def test_pass_2_jd_native_terms_are_protected():
    _, _, run_pass_2 = _import_runner()
    text = "Led comprehensive market analysis and used SQL."
    jd = "This role requires comprehensive market analysis and SQL."

    out = await run_pass_2(text, jd_text=jd, target_market="north-america", llm=None)

    assert out["text"] == text
    assert out["replacements_applied"] == []
    assert out["protected_skipped"] == [
        {"term": "comprehensive", "reason": "in_jd"}
    ]
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_2_empty_input_returns_shape_valid_pass():
    _, _, run_pass_2 = _import_runner()

    out = await run_pass_2("", jd_text="", target_market="north-america", llm=None)

    assert out["_method"] == "fallback_no_llm"
    assert out["text"] == ""
    assert out["replacements_applied"] == []
    assert out["protected_skipped"] == []
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_2_clean_input_is_idempotent():
    _, _, run_pass_2 = _import_runner()
    text = "Led market analysis, built a sizing model, and wrote recommendations."

    out = await run_pass_2(text, jd_text="", target_market="north-america", llm=None)

    assert out["text"] == text
    assert out["replacements_applied"] == []
    assert out["protected_skipped"] == []
    assert out["verdict"] == "pass"


@pytest.mark.asyncio
async def test_pass_2_avoids_false_positive_inside_words_and_dates():
    _, _, run_pass_2 = _import_runner()
    text = "Built a lever model for 2025.06 -- 2025.10; Pythonic helpers stayed internal."

    out = await run_pass_2(text, jd_text="", target_market="north-america", llm=None)

    assert out["text"] == text
    assert out["replacements_applied"] == []
    assert out["protected_skipped"] == []


@pytest.mark.asyncio
async def test_pass_2_real_ai_tone_phrases_are_caught():
    _, _, run_pass_2 = _import_runner()
    text = (
        "Orchestrated cross-functional synergies to drive impact; "
        "全方位助力团队跑通端到端原型!"
    )

    out = await run_pass_2(text, jd_text="", target_market="mainland-china", llm=None)

    originals = _ai_phrase_terms(out)
    assert "Orchestrated" in originals
    assert "cross-functional synergies" in originals
    assert "drive impact" in originals
    assert "全方位" in originals
    assert "助力" in originals
    assert "跑通" in originals
    assert "!" in originals
    assert "!" not in out["text"]


@pytest.mark.asyncio
async def test_pass_2_llm_degraded_falls_back_to_deterministic_rules():
    _, _, run_pass_2 = _import_runner()
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=ConnectionError("offline"))

    out = await run_pass_2(
        "Leveraged robust tooling to streamline workflows.",
        jd_text="",
        target_market="north-america",
        llm=mock,
    )

    assert out["_method"] == "fallback_no_llm"
    assert {"Leveraged", "robust", "streamline"} <= _ai_phrase_terms(out)
    assert "Used" in out["text"]
    assert "reliable" in out["text"]
    assert "improve" in out["text"]


@pytest.mark.asyncio
async def test_quality_pass_report_runs_pass_1_5_before_pass_2():
    build_quality_pass_report, _, _ = _import_runner()
    text = "技术采用曲线评估——深度赋能业务。"

    out = await build_quality_pass_report(
        rewritten_resume=text,
        target_market="mainland-china",
        jd_text="",
        competency_profile={"id": "cp"},
        experience_bank={"version": "eb"},
        llm=None,
    )

    assert out["sub_skill"] == "quality-pass-runner"
    assert out["ppaf_stage"] == "late_feedback"
    assert out["pass_1_5_chinese_readability"]["enabled"] is True
    assert "技术成熟度评估" in out["final_resume_text"]
    assert "深度赋能" not in out["final_resume_text"]
    assert out["pass_2_ai_taste_removal"]["replacements_applied"]
    assert out["aggregate_verdict"] == "pass"
    assert out["pending_user_review_flag"] is False


@pytest.mark.asyncio
async def test_quality_pass_report_non_chinese_market_skips_pass_1_5_but_runs_pass_2():
    build_quality_pass_report, _, _ = _import_runner()

    out = await build_quality_pass_report(
        rewritten_resume="Leveraged comprehensive research.",
        target_market="north-america",
        jd_text="",
        competency_profile={},
        experience_bank={},
        llm=None,
    )

    assert out["pass_1_5_chinese_readability"]["enabled"] is False
    assert "Leveraged" not in out["final_resume_text"]
    assert out["pass_2_ai_taste_removal"]["replacements_applied"]
    assert out["confidence"] in {"moderate", "low"}
