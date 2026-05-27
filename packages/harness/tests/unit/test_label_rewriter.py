"""Test bullet 标签 rewriter (LLM, mocked)."""
import pytest
from unittest.mock import AsyncMock
from harness.tier1.label_rewriter import LabelRewriter


@pytest.mark.asyncio
async def test_rewrites_label_from_json():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value='{"new_label": "AI 内容工作流设计"}')
    rw = LabelRewriter(mock)
    out = await rw.rewrite(
        bullet="结构化研究：承担五年战略规划下游应用与并购筛选模块...",
        jd_keywords=["AIGC", "内容", "工作流", "Prompt"],
    )
    assert out == "AI 内容工作流设计"


@pytest.mark.asyncio
async def test_handles_invalid_json_gracefully():
    """LLM returned non-JSON garbage → fall back to original label."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="not json at all")
    rw = LabelRewriter(mock)
    out = await rw.rewrite(bullet="结构化研究：bar baz", jd_keywords=[])
    # Falls back to extracting label part before "："
    assert out == "结构化研究"


@pytest.mark.asyncio
async def test_handles_missing_new_label_key():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value='{"unrelated": "value"}')
    rw = LabelRewriter(mock)
    out = await rw.rewrite(bullet="行业研究：项目内容", jd_keywords=[])
    assert out == "行业研究"


@pytest.mark.asyncio
async def test_bullet_with_no_colon_falls_back_to_empty():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="not json")
    rw = LabelRewriter(mock)
    out = await rw.rewrite(bullet="No colon in this bullet", jd_keywords=[])
    assert out == ""


@pytest.mark.asyncio
async def test_empty_keywords_still_calls_claude():
    """Even with empty keywords list, the call still goes through."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value='{"new_label": "通用标签"}')
    rw = LabelRewriter(mock)
    out = await rw.rewrite(bullet="任何 bullet", jd_keywords=[])
    assert out == "通用标签"
    mock.call.assert_called_once()


@pytest.mark.asyncio
async def test_keywords_passed_to_prompt():
    """JD keywords (top 10) should appear in the user prompt."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value='{"new_label": "x"}')
    rw = LabelRewriter(mock)
    await rw.rewrite(
        bullet="任何 bullet",
        jd_keywords=["AIGC", "Agent", "Prompt", "RAG"] * 5,  # 20 items
    )
    call_args = mock.call.call_args
    user_prompt = call_args.kwargs.get("user") or (call_args.args[1] if len(call_args.args) > 1 else "")
    assert "AIGC" in user_prompt
    # Should be capped at 10 items
    assert user_prompt.count("AIGC") <= 5  # at most 5 AIGC tokens since [:10]


@pytest.mark.asyncio
async def test_max_tokens_kept_small():
    """Label rewriter should request at most ~100 tokens — single label."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value='{"new_label": "x"}')
    rw = LabelRewriter(mock)
    await rw.rewrite(bullet="x：y", jd_keywords=[])
    call_args = mock.call.call_args
    max_tokens = call_args.kwargs.get("max_tokens")
    assert max_tokens is not None and max_tokens <= 200
