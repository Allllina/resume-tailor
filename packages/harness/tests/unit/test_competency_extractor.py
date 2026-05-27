"""Unit tests for harness.competency.extractor (Wave 4 Step B.1)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from harness.exceptions import SubSkillUnavailable
from harness.competency.extractor import (
    SECTION_KEYS,
    extract_competencies,
    fallback_model,
    section_d_keywords,
    section_h_strategy_hints,
)


def _valid_model_json() -> str:
    """Build a JSON string that conforms to the 9-section contract."""
    obj = {
        "section_a_role_definition": (
            "AIGC content product role focused on prompt engineering and "
            "agent workflows; hires for a builder who can ship LLM-driven "
            "internal tooling."
        ),
        "section_b_core_hiring_logic": [
            {
                "priority_name": "Prompt engineering depth",
                "what_it_means": "Designs prompts and evaluates output quality.",
                "why_it_matters": "Quality of LLM features depends on prompt craft.",
                "credible_proof_signals": "Shipped LLM features; A/B tested prompts.",
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
        "section_d_keyword_architecture": {
            "tier_1_core_role": ["AIGC", "内容运营"],
            "tier_2_capability": ["Prompt Engineering", "Agent 工作流"],
            "tier_3_tools_methods": ["LangGraph", "RAG", "Claude API"],
            "tier_4_action_verbs": ["搭建", "优化", "评估"],
            "tier_5_semantic_equivalents": ["生成式 AI", "LLM"],
        },
        "section_e_shared_patterns": {
            "cross_company_consensus": "single-JD; cross-company patterns not derivable",
            "company_specific_variations": "",
        },
        "section_f_hidden_screening": [
            {
                "criterion": "Owns ambiguous LLM problems end-to-end",
                "signal_in_jd": "JD says '独立负责...生成式 AI 工作流'",
                "implication": "Show one E2E shipped LLM project on resume.",
            }
        ],
        "section_g_market_interpretation": {
            "priorities": "China internet: shipping speed + measurable ROI.",
            "experience_framing": "Quantify business impact in CNY/% terms.",
            "proof_signals": "Internal tool adoption; lift in DAU.",
            "resume_style": "Concise Chinese bullets; verbs first.",
            "cultural_conventions": "Direct, outcome-first phrasing.",
        },
        "section_h_strategy_implications": {
            "emphasize_most": "Shipped LLM tooling; prompt iteration discipline.",
            "de_emphasize": "Generic data analytics work without LLM angle.",
            "top_half_content": "Lead summary with AIGC + prompt engineering.",
            "natural_keyword_placement": "Place 'Prompt Engineering' in Skills first row.",
            "common_mistakes": [
                "Listing models without showing what was shipped.",
                "Vague 'AI literacy' phrases without specifics.",
            ],
        },
        "section_i_limitations_confidence": {
            "summary": "Single JD; conclusions provisional.",
            "confidence": "low",
        },
        "flat_summary": {
            "primary_lens": "C_product_ops",
            "role_family": "C_product_ops",
            "target_market": "mainland-china",
            "confidence": "moderate",
            "competency_tags": ["product", "AIGC"],
            "evidence_requirements": ["shipped LLM feature"],
            "scoring_notes": "single-JD; AIGC-heavy",
        },
    }
    return json.dumps(obj)


# --------------------------- happy path ---------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_all_9_sections():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_model_json())
    out = await extract_competencies(
        jd_text="AIGC 内容实习生 招聘. Prompt Engineering Agent LLM RAG.",
        lens="C_product_ops",
        llm=mock,
    )
    for key in SECTION_KEYS:
        assert key in out, f"missing section {key}"
    assert "flat_summary" in out
    assert out["_method"] == "llm"
    # Section D shape preserved
    assert "tier_1_core_role" in out["section_d_keyword_architecture"]


@pytest.mark.asyncio
async def test_happy_path_strips_markdown_fences():
    """LLM may wrap JSON in ```json fences; extractor should strip them."""
    fenced = "```json\n" + _valid_model_json() + "\n```"
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=fenced)
    out = await extract_competencies("jd text", "C_product_ops", mock)
    assert out["_method"] == "llm"
    assert out["flat_summary"]["primary_lens"] == "C_product_ops"


@pytest.mark.asyncio
async def test_prompt_includes_jd_and_lens():
    """Snapshot-ish: the user prompt should mention both JD and lens."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_model_json())
    await extract_competencies(
        jd_text="数据分析师岗位 SQL Python",
        lens="B_data_analytics",
        llm=mock,
    )
    user_prompt = mock.call.call_args.kwargs.get("user", "")
    system_prompt = mock.call.call_args.kwargs.get("system", "")
    assert "B_data_analytics" in user_prompt
    assert "数据分析师" in user_prompt
    assert "9-section" in system_prompt or "9 sections" in user_prompt or "9-section" in user_prompt


# --------------------------- failure modes ---------------------------


@pytest.mark.asyncio
async def test_llm_raises_fail_fast():
    """Expected LLM failure modes (timeout, connection, circuit open) → raise SubSkillUnavailable."""
    from harness.llm.protocol import CircuitOpen

    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=CircuitOpen("circuit open"))
    with pytest.raises(SubSkillUnavailable) as exc:
        await extract_competencies("jd", "C_product_ops", mock)
    assert exc.value.sub_skill == "competency_extractor"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_malformed_json_fail_fast():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="Sorry, I cannot comply.")
    with pytest.raises(SubSkillUnavailable) as exc:
        await extract_competencies("jd", "C_product_ops", mock)
    assert exc.value.sub_skill == "competency_extractor"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_empty_response_fail_fast():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="")
    with pytest.raises(SubSkillUnavailable) as exc:
        await extract_competencies("jd", "C_product_ops", mock)
    assert exc.value.sub_skill == "competency_extractor"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_injection_detected_fail_fast():
    from harness.llm.pii_filtering_provider import InjectionDetectedError

    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=InjectionDetectedError("injection"))
    with pytest.raises(SubSkillUnavailable) as exc:
        await extract_competencies("jd", "C_product_ops", mock)
    assert exc.value.sub_skill == "competency_extractor"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_missing_sections_filled_in_and_marked_partial():
    """LLM returns JSON missing some sections → defaults filled, marked degraded."""
    partial = json.dumps({
        "section_a_role_definition": "stub",
        # 8 of 9 sections missing
        "flat_summary": {
            "primary_lens": "C_product_ops",
            "confidence": "low",
        },
    })
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=partial)
    out = await extract_competencies("jd", "C_product_ops", mock)
    # All 9 sections must be present
    for key in SECTION_KEYS:
        assert key in out
    # Marker indicates the LLM ran but the result was incomplete
    assert out["_method"] == "llm_partial"
    # Provided section preserved verbatim
    assert out["section_a_role_definition"] == "stub"
    # Missing sections filled with placeholders (default shape)
    assert isinstance(out["section_d_keyword_architecture"], dict)
    assert "tier_1_core_role" in out["section_d_keyword_architecture"]


@pytest.mark.asyncio
async def test_no_llm_fail_fast():
    """Passing llm=None goes straight to fail-fast."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await extract_competencies("jd", "C_product_ops", llm=None)
    assert exc.value.sub_skill == "competency_extractor"
    assert exc.value.llm_unreachable is True


# --------------------------- fallback_model() ---------------------------


def test_fallback_model_shape():
    fb = fallback_model("C_product_ops")
    for key in SECTION_KEYS:
        assert key in fb
    assert fb["flat_summary"]["primary_lens"] == "C_product_ops"
    assert fb["flat_summary"]["confidence"] == "low"
    assert fb["section_i_limitations_confidence"]["confidence"] == "low"
    assert fb["_method"] == "fallback_no_llm"
    # Section D keys present
    sec_d = fb["section_d_keyword_architecture"]
    for tier_key in (
        "tier_1_core_role",
        "tier_2_capability",
        "tier_3_tools_methods",
        "tier_4_action_verbs",
        "tier_5_semantic_equivalents",
    ):
        assert tier_key in sec_d
        assert sec_d[tier_key] == []


# --------------------------- helpers ---------------------------


def test_section_d_keywords_flattens_tiers_1_2_3_5_skipping_4():
    """Tier 4 (action verbs) is skipped — Skills rows are nouns."""
    model = {
        "section_d_keyword_architecture": {
            "tier_1_core_role": ["AIGC", "内容"],
            "tier_2_capability": ["Prompt Engineering"],
            "tier_3_tools_methods": ["LangGraph"],
            "tier_4_action_verbs": ["搭建", "优化"],
            "tier_5_semantic_equivalents": ["LLM"],
        }
    }
    out = section_d_keywords(model)
    assert "AIGC" in out
    assert "Prompt Engineering" in out
    assert "LangGraph" in out
    assert "LLM" in out
    # Tier 4 verbs excluded
    assert "搭建" not in out
    assert "优化" not in out


def test_section_d_keywords_dedupes():
    model = {
        "section_d_keyword_architecture": {
            "tier_1_core_role": ["AIGC", "Prompt"],
            "tier_2_capability": ["Prompt", "PROMPT"],  # dup case-insensitive
            "tier_3_tools_methods": [],
            "tier_4_action_verbs": [],
            "tier_5_semantic_equivalents": [],
        }
    }
    out = section_d_keywords(model)
    # Only one Prompt-shaped term, original casing preserved
    lowered = [s.lower() for s in out]
    assert lowered.count("prompt") == 1


def test_section_d_keywords_handles_none_model():
    assert section_d_keywords(None) == []


def test_section_d_keywords_handles_missing_section():
    assert section_d_keywords({"flat_summary": {}}) == []


def test_section_h_strategy_hints_extracts_compact_dict():
    model = {
        "section_h_strategy_implications": {
            "emphasize_most": "Shipped LLM tooling.",
            "top_half_content": "Lead with AIGC + prompt engineering.",
            "de_emphasize": "Generic analytics.",
            "natural_keyword_placement": "First Skills row.",
            "common_mistakes": ["a", "b"],
        }
    }
    hints = section_h_strategy_hints(model)
    assert hints is not None
    assert "emphasize_most" in hints
    assert "top_half_content" in hints
    assert hints["emphasize_most"].startswith("Shipped")


def test_section_h_strategy_hints_truncates_long_strings():
    model = {
        "section_h_strategy_implications": {
            "emphasize_most": "x" * 1000,
            "top_half_content": "y" * 50,
        }
    }
    hints = section_h_strategy_hints(model, max_chars=100)
    assert hints is not None
    assert len(hints["emphasize_most"]) <= 100


def test_section_h_strategy_hints_returns_none_when_empty():
    model = {
        "section_h_strategy_implications": {
            "emphasize_most": "",
            "top_half_content": "",
        }
    }
    assert section_h_strategy_hints(model) is None


def test_section_h_strategy_hints_handles_missing_section():
    assert section_h_strategy_hints(None) is None
    assert section_h_strategy_hints({"flat_summary": {}}) is None
