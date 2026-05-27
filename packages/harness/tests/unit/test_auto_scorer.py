"""Unit tests for harness.users.auto_scorer."""
from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from harness.users.auto_scorer import (
    AI_VALUES,
    INDUSTRIES,
    INDUSTRY_VALUES,
    LENSES,
    LENS_VALUES,
    fallback_score,
    score_experience,
)


def _full_payload(
    *,
    rec_overrides: dict | None = None,
    fit_overrides: dict | None = None,
    ai: str = "moderate",
) -> dict:
    rec = {k: "medium" for k in INDUSTRIES}
    if rec_overrides:
        rec.update(rec_overrides)
    fit = {k: "adjacent" for k in LENSES}
    if fit_overrides:
        fit.update(fit_overrides)
    return {
        "recognition_per_industry": rec,
        "vertical_fit_per_lens": fit,
        "ai_digital_fluency": ai,
    }


def _mock_llm(text: str | Exception) -> MagicMock:
    llm = MagicMock()
    if isinstance(text, Exception):
        llm.call = AsyncMock(side_effect=text)
    else:
        llm.call = AsyncMock(return_value=text)
    return llm


@pytest.mark.asyncio
async def test_happy_path_passes_through():
    payload = _full_payload(ai="strong")
    llm = _mock_llm(json.dumps(payload))
    result = await score_experience("Did consulting at Bain.", llm)
    assert result["ai_digital_fluency"] == "strong"
    assert all(v == "medium" for v in result["recognition_per_industry"].values())
    assert all(v == "adjacent" for v in result["vertical_fit_per_lens"].values())
    # No fallback marker on happy path
    assert "_fallback" not in result


@pytest.mark.asyncio
async def test_fence_wrapped_json_handled():
    payload = _full_payload()
    fenced = "```json\n" + json.dumps(payload) + "\n```"
    llm = _mock_llm(fenced)
    result = await score_experience("content", llm)
    assert "recognition_per_industry" in result
    assert result["ai_digital_fluency"] == "moderate"
    assert "_fallback" not in result


@pytest.mark.asyncio
async def test_malformed_json_returns_fallback():
    llm = _mock_llm("this is not json at all {{{{")
    result = await score_experience("content", llm)
    assert result.get("_fallback") is True
    assert result["ai_digital_fluency"] == "none"


@pytest.mark.asyncio
async def test_llm_raises_returns_fallback():
    llm = _mock_llm(RuntimeError("upstream blew up"))
    result = await score_experience("content", llm)
    assert result.get("_fallback") is True
    # Fallback shape is full
    assert set(result["recognition_per_industry"].keys()) == set(INDUSTRIES)
    assert set(result["vertical_fit_per_lens"].keys()) == set(LENSES)


@pytest.mark.asyncio
async def test_missing_columns_backfilled():
    # Drop one industry and one lens; scorer should backfill
    payload = _full_payload()
    del payload["recognition_per_industry"]["finance"]
    del payload["vertical_fit_per_lens"]["B_data_analytics"]
    llm = _mock_llm(json.dumps(payload))
    result = await score_experience("content", llm)
    assert result["recognition_per_industry"]["finance"] is None
    assert result["vertical_fit_per_lens"]["B_data_analytics"] == "missing"
    # Other columns preserved
    assert result["recognition_per_industry"]["consulting"] == "medium"
    assert result["vertical_fit_per_lens"]["A_strategy_research"] == "adjacent"


@pytest.mark.asyncio
async def test_invalid_enum_values_normalized():
    payload = _full_payload()
    payload["recognition_per_industry"]["consulting"] = "extreme"  # invalid
    payload["vertical_fit_per_lens"]["C_product_ops"] = "perfect"  # invalid
    payload["ai_digital_fluency"] = "wizard"  # invalid
    llm = _mock_llm(json.dumps(payload))
    result = await score_experience("content", llm)
    # Bad industry → None (default for that axis)
    assert result["recognition_per_industry"]["consulting"] is None
    # Bad lens → missing (default)
    assert result["vertical_fit_per_lens"]["C_product_ops"] == "missing"
    # Bad AI → none
    assert result["ai_digital_fluency"] == "none"


@pytest.mark.asyncio
async def test_empty_content_returns_fallback_without_calling_llm():
    llm = _mock_llm("anything")
    result = await score_experience("", llm)
    assert result.get("_fallback") is True
    llm.call.assert_not_called()


def test_fallback_score_has_full_shape():
    fb = fallback_score()
    assert set(fb["recognition_per_industry"].keys()) == set(INDUSTRIES)
    assert set(fb["vertical_fit_per_lens"].keys()) == set(LENSES)
    # Lens defaults are valid enum values
    assert all(v in LENS_VALUES for v in fb["vertical_fit_per_lens"].values())
    # Industry defaults are all None (valid in INDUSTRY_VALUES)
    assert all(v in INDUSTRY_VALUES for v in fb["recognition_per_industry"].values())
    assert fb["ai_digital_fluency"] in AI_VALUES
    assert fb["_fallback"] is True
