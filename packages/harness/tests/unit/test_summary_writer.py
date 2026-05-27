"""Test Summary writer (LLM, mocked)."""
import pytest
from unittest.mock import AsyncMock

from harness.exceptions import SubSkillUnavailable
from harness.llm.protocol import CircuitOpen
from harness.tier1.summary_writer import SummaryWriter


@pytest.mark.asyncio
async def test_writes_summary():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="兼具 BA 思维与 AI 工具实操，3 项目落地 AIGC 内容工作流。")
    sw = SummaryWriter(mock)
    out = await sw.write(
        jd_excerpt="AIGC 内容实习生 招聘",
        lens="C_product_ops",
        candidate_tags=["AIGC", "Agent", "数据分析"],
    )
    assert "BA 思维" in out


@pytest.mark.asyncio
async def test_returns_stripped_text():
    """Should strip leading/trailing whitespace."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="   summary text   \n")
    sw = SummaryWriter(mock)
    out = await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    assert out == "summary text"


@pytest.mark.asyncio
async def test_jd_excerpt_capped_at_500_chars():
    """Long JD should be truncated to 500 chars in prompt."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    long_jd = "A" * 1000
    await sw.write(jd_excerpt=long_jd, lens="A_strategy_research", candidate_tags=["x"])
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    # JD should be capped — count of As in user prompt no greater than 500
    # (small buffer for 'A' chars in fixed prompt boilerplate / lens name)
    assert user_prompt.count("A") <= 510


@pytest.mark.asyncio
async def test_tags_capped_at_8():
    """Only top-8 candidate tags appear in prompt."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    tags = [f"tag{i}" for i in range(20)]
    await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=tags)
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    # tag0..tag7 should appear; tag8+ should not
    assert "tag0" in user_prompt
    assert "tag7" in user_prompt
    assert "tag8" not in user_prompt
    assert "tag19" not in user_prompt


@pytest.mark.asyncio
async def test_max_tokens_kept_under_300():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    max_tokens = mock.call.call_args.kwargs.get("max_tokens")
    assert max_tokens is not None and max_tokens <= 300


@pytest.mark.asyncio
async def test_lens_passed_to_prompt():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    await sw.write(jd_excerpt="x", lens="HC_human_capital", candidate_tags=[])
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    assert "HC_human_capital" in user_prompt


# ============ Wave 4 Step B: strategy_hints (Section H) ============


@pytest.mark.asyncio
async def test_strategy_hints_injected_into_prompt():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    await sw.write(
        jd_excerpt="some JD",
        lens="C_product_ops",
        candidate_tags=["AIGC"],
        strategy_hints={
            "emphasize_most": "Shipped LLM tooling",
            "top_half_content": "Lead with AIGC + prompt engineering",
        },
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    assert "策略提示" in user_prompt
    assert "Shipped LLM tooling" in user_prompt
    assert "AIGC + prompt engineering" in user_prompt


@pytest.mark.asyncio
async def test_strategy_hints_none_omits_block():
    """No strategy hints → no 策略提示 block in the prompt."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    assert "策略提示" not in user_prompt


@pytest.mark.asyncio
async def test_strategy_hints_empty_dict_omits_block():
    """Hints with all-empty values → no 策略提示 block."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="ok")
    sw = SummaryWriter(mock)
    await sw.write(
        jd_excerpt="x",
        lens="C_product_ops",
        candidate_tags=[],
        strategy_hints={"emphasize_most": "", "top_half_content": ""},
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    assert "策略提示" not in user_prompt


# ----------------- Phase 2 (R-18 / fail-fast) failure-path tests -----------------


@pytest.mark.asyncio
async def test_missing_llm_raises_sub_skill_unavailable():
    """Phase 2: no LLM configured → raise instead of silent empty string."""
    sw = SummaryWriter(None)
    with pytest.raises(SubSkillUnavailable) as exc:
        await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    assert exc.value.sub_skill == "summary_writer"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_transport_error_raises_sub_skill_unavailable():
    """Phase 2: transport-level LLM failure raises with llm_unreachable=True."""
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=CircuitOpen("open"))
    sw = SummaryWriter(mock)
    with pytest.raises(SubSkillUnavailable) as exc:
        await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    assert exc.value.sub_skill == "summary_writer"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_empty_response_raises_sub_skill_unavailable():
    """Phase 2: empty / non-string LLM response is a fail-fast (llm_unreachable=False)."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="")
    sw = SummaryWriter(mock)
    with pytest.raises(SubSkillUnavailable) as exc:
        await sw.write(jd_excerpt="x", lens="C_product_ops", candidate_tags=[])
    assert exc.value.sub_skill == "summary_writer"
    assert exc.value.llm_unreachable is False
