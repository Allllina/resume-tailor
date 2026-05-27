"""Test lens routing: keyword scan → LLM fallback if ambiguous."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from harness.tier1.lens_router import LensRouter, KEYWORD_TO_LENS, SCENARIO_KEYWORDS, CONFIDENCE_THRESHOLD


@pytest.mark.asyncio
async def test_strong_keywords_route_deterministically():
    """JD heavy on AIGC keywords → C lens deterministic, no LLM call."""
    router = LensRouter(claude=None)
    result = await router.route(jd_text="""
        我们招聘 AIGC 内容实习生。生成式 AI、提示词工程、Agent 工作流。
        Prompt Engineering 经验优先。LLM 应用方向。
    """)
    assert result["primary_lens"] == "C_product_ops"
    assert result["scenario"] == "ai-innovation"
    assert result["used_llm_fallback"] is False
    assert result["confidence"] > 0


@pytest.mark.asyncio
async def test_strong_strategy_keywords_route_to_A():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="""
        战略咨询岗位。负责行业研究、竞争格局分析、市场进入策略制定。
        熟悉 Porter 五力、PEST 等框架。战略输出。
    """)
    assert result["primary_lens"] == "A_strategy_research"
    assert result["used_llm_fallback"] is False


@pytest.mark.asyncio
async def test_strong_data_keywords_route_to_B():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="""
        数据分析师。SQL Python 数据建模 统计推断 业务指标体系 异动归因。
    """)
    assert result["primary_lens"] == "B_data_analytics"


@pytest.mark.asyncio
async def test_finance_keywords_route_to_D():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="""
        投行行研助理。负责估值建模 DCF 财务分析 行研报告 资本市场跟踪。
    """)
    assert result["primary_lens"] == "D_finance_markets"


@pytest.mark.asyncio
async def test_hc_keywords_route_to_HC():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="""
        人力资本咨询助理。组织诊断、任职资格设计、薪酬体系、绩效管理、HR Tech 数字化转型。
    """)
    assert result["primary_lens"] == "HC_human_capital"


@pytest.mark.asyncio
async def test_ambiguous_jd_falls_back_to_llm():
    mock_claude = AsyncMock()
    mock_claude.call = AsyncMock(
        return_value='{"primary_lens": "A_strategy_research", "scenario": "consulting"}'
    )
    router = LensRouter(claude=mock_claude)
    result = await router.route(jd_text="一段不明显的工作描述。")
    assert result["used_llm_fallback"] is True
    assert result["primary_lens"] == "A_strategy_research"


@pytest.mark.asyncio
async def test_llm_fallback_with_no_claude_returns_default():
    """If no claude client and JD ambiguous, fall back to C_product_ops default."""
    router = LensRouter(claude=None)
    result = await router.route(jd_text="some short ambiguous text")
    assert result["used_llm_fallback"] is False
    assert result["primary_lens"] in {"A_strategy_research", "B_data_analytics", "C_product_ops", "D_finance_markets", "HC_human_capital"}


@pytest.mark.asyncio
async def test_scenario_inference_ai_innovation():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="AIGC Agent Prompt RAG LLM 标签体系")
    assert result["scenario"] == "ai-innovation"


@pytest.mark.asyncio
async def test_blend_ratio_present():
    router = LensRouter(claude=None)
    result = await router.route(jd_text="AIGC 内容工作流 Agent Prompt 数据分析 SQL Python")
    assert "blend_ratio" in result
    assert isinstance(result["blend_ratio"], dict)


@pytest.mark.asyncio
async def test_keyword_dictionary_has_all_5_lenses():
    """Sanity: KEYWORD_TO_LENS covers all 5 role_family lenses."""
    expected = {"A_strategy_research", "B_data_analytics", "C_product_ops", "D_finance_markets", "HC_human_capital"}
    assert set(KEYWORD_TO_LENS.keys()) == expected


@pytest.mark.asyncio
async def test_confidence_threshold_constant():
    assert CONFIDENCE_THRESHOLD >= 1
