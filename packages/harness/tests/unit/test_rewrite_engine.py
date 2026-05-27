"""Unit tests for harness.rewrite.engine (Wave 4 D.2a).

The engine is the LLM-driven port of resume-rewrite-engine. Every test
mocks the LLM — no real API calls. The truthfulness pre-check is a
substring gate; Pass 3 (D.4) is the future semantic verifier and not
exercised here.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from harness.llm.protocol import CircuitOpen
from harness.exceptions import SubSkillUnavailable
from harness.rewrite import (
    RewriteOutput,
    rewrite_bullets,
)
from harness.schemas.loader import SchemaRegistry


# --------------------------- fixtures ---------------------------


@pytest.fixture
def raw_files_root(tmp_path: Path) -> Path:
    """Fake raw experience-bank directory with a few experiences."""
    root = tmp_path / "raw"
    root.mkdir()
    (root / "01-kearney.md").write_text(
        "# 科尔尼\n\nProject: OSAT 五年战略规划. Built downstream "
        "application track research, value chain analysis. Shipped 5% "
        "lift on category prioritization. Did global M&A long-list "
        "screening across capability tags.",
        encoding="utf-8",
    )
    (root / "02-ipsos.md").write_text(
        "# Ipsos Strategy3\nLed market research project. Designed "
        "consumer survey. Analyzed 1000 responses. Built segmentation.",
        encoding="utf-8",
    )
    (root / "03-desaysv.md").write_text(
        "# Desay SV\n汽车电子. 智能座舱产品规划项目. 写了 PRD. 跟硬件团队对齐.",
        encoding="utf-8",
    )
    (root / "04-mercer.md").write_text(
        "# Mercer\nHR consulting. Designed comp benchmark study. Ran "
        "salary survey across 200 firms.",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def experiences() -> list[dict]:
    return [
        {
            "id": "01-kearney",
            "company": "A.T. Kearney",
            "role": "Strategy Analyst Intern",
            "period": "Jun-Oct 2025",
            "one_line": "OSAT 五年战略规划项目, 下游应用赛道与并购 longlist.",
            "disambiguator_per_industry": {},
        },
        {
            "id": "02-ipsos",
            "company": "Ipsos",
            "role": "Strategy Intern",
            "period": "2024",
            "one_line": "Market research and consumer segmentation.",
            "disambiguator_per_industry": {
                "internet_strategic": {
                    "type": "mis_classification",
                    "text": "（益普索旗下战略咨询）",
                    "rationale": "Avoid confusion with Ipsos market-research line.",
                }
            },
        },
        {
            "id": "03-desaysv",
            "company": "Desay SV",
            "role": "Product Intern",
            "period": "2023",
            "one_line": "智能座舱 PRD 与跨团队协作.",
            "disambiguator_per_industry": {
                "internet_strategic": {
                    "type": "pure_recognition",
                    "text": "（头部汽车电子上市公司）",
                    "rationale": "招聘方可能不识别 Desay SV 品牌.",
                }
            },
        },
        {
            "id": "04-mercer",
            "company": "Mercer",
            "role": "HR Consulting Intern",
            "period": "2022",
            "one_line": "Comp benchmarking and salary survey.",
            "disambiguator_per_industry": {},
        },
    ]


@pytest.fixture
def competency_model() -> dict:
    return {
        "section_a_role_definition": "Strategy analyst role for internet platform.",
        "section_b_core_hiring_logic": [
            {
                "priority_name": "Industry analysis depth",
                "what_it_means": "Frames markets and competitors structurally.",
                "why_it_matters": "Hiring manager screens for analytical rigor.",
                "credible_proof_signals": "Issue trees; quantified comparisons.",
            }
        ],
        "section_h_strategy_implications": {
            "emphasize_most": "Quantified impact and structured analysis.",
            "top_half_content": "Lead with strategy projects; surface frameworks.",
        },
    }


def _make_trace(final_category: int, experience_id: str, lift: str = "none") -> dict:
    return {
        "experience_id": experience_id,
        "pass_a_tier": "上展开",
        "pass_b_tier": "上展开",
        "pass_b_lift": lift,
        "pass_c_tier": "上展开",
        "pass_c_ai_pressure": "none",
        "final_category": final_category,
    }


def _llm_response_for(experience_id: str, claim_text: str, *, n_bullets: int = 2) -> str:
    """Build a JSON response that the engine can parse and verify."""
    bullets = [
        {
            "id": f"{experience_id}-bullet-{i+1}",
            "text": f"{claim_text}",
            "claimed_facts": [claim_text],
        }
        for i in range(n_bullets)
    ]
    return json.dumps(
        {
            "experience_id": experience_id,
            "final_category": 1,
            "bullets": bullets,
            "disambiguator_parenthetical": None,
            "decision_rationale": "Lead with industry research depth.",
        }
    )


# --------------------------- 1. tier 1 → skipped ---------------------------


@pytest.mark.asyncio
async def test_tier_1_returns_skipped_no_llm(
    experiences, competency_model, raw_files_root
):
    """Tier 1 short-circuits: empty Section G, _method = skipped_tier_1, no LLM call."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="should not be called")

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=1,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert isinstance(out, RewriteOutput)
    assert out._method == "skipped_tier_1"
    assert out.section_g_bullets == []
    mock_llm.call.assert_not_awaited()


# --------------------------- 2. tier 2 → top-2 cat 1/2 only ---------------------------


@pytest.mark.asyncio
async def test_tier_2_only_top_2_cat_1_2_rewritten(
    experiences, competency_model, raw_files_root
):
    """4 Cat 1/2 experiences in trace → engine calls LLM exactly 2 times."""
    mock_llm = AsyncMock()
    # Each LLM call gets a response that matches its experience.
    responses = {
        "01-kearney": _llm_response_for("01-kearney", "OSAT 五年战略规划"),
        "02-ipsos": _llm_response_for("02-ipsos", "consumer survey"),
        "03-desaysv": _llm_response_for("03-desaysv", "智能座舱"),
        "04-mercer": _llm_response_for("04-mercer", "comp benchmark"),
    }

    async def call_side_effect(*, system, user, max_tokens, temperature):
        for exp_id, resp in responses.items():
            if exp_id in user:
                return resp
        return responses["01-kearney"]

    mock_llm.call = AsyncMock(side_effect=call_side_effect)

    trace = [
        _make_trace(1, "01-kearney"),
        _make_trace(2, "02-ipsos", lift="mis_classification"),
        _make_trace(2, "03-desaysv"),
        _make_trace(1, "04-mercer"),
    ]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    # Only 2 LLM calls (top-2 of 4 Cat 1/2 entries).
    assert mock_llm.call.await_count == 2
    # Bullets came back from those 2 experiences.
    rewritten_ids = {b.experience_id for b in out.section_g_bullets}
    assert len(rewritten_ids) == 2


# --------------------------- 3. tier 3 → all cat 1/2/3 ---------------------------


@pytest.mark.asyncio
async def test_tier_3_rewrites_all_cat_123(
    experiences, competency_model, raw_files_root
):
    """Tier 3: 2 Cat 1/2 (LLM calls) + 1 Cat 3 (deterministic) + 1 Cat 4 (dropped)."""
    # Per-experience response so each claim verifies against its own raw file.
    responses = {
        "01-kearney": _llm_response_for("01-kearney", "OSAT 五年战略规划"),
        "02-ipsos": _llm_response_for("02-ipsos", "consumer survey"),
    }

    async def call_side_effect(*, system, user, max_tokens, temperature):
        for exp_id, resp in responses.items():
            if exp_id in user:
                return resp
        return responses["01-kearney"]

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=call_side_effect)

    trace = [
        _make_trace(1, "01-kearney"),
        _make_trace(2, "02-ipsos"),
        _make_trace(3, "03-desaysv"),
        _make_trace(4, "04-mercer"),
    ]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    # 2 LLM calls (Cat 1 + Cat 2). Cat 3 deterministic, Cat 4 dropped.
    assert mock_llm.call.await_count == 2
    ids = {b.experience_id for b in out.section_g_bullets}
    assert "01-kearney" in ids
    assert "02-ipsos" in ids
    assert "03-desaysv" in ids
    assert "04-mercer" not in ids


# --------------------------- 4. cat 4 silently dropped ---------------------------


@pytest.mark.asyncio
async def test_cat_4_silently_dropped(
    experiences, competency_model, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for("01-kearney", "OSAT 五年战略规划")
    )

    trace = [
        _make_trace(1, "01-kearney"),
        _make_trace(4, "04-mercer"),
    ]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    ids = {b.experience_id for b in out.section_g_bullets}
    assert "04-mercer" not in ids
    log_ids = {entry.experience_id for entry in out.section_j_decision_log}
    assert "04-mercer" not in log_ids


# --------------------------- 5. cat 3 backup line deterministic ---------------------------


@pytest.mark.asyncio
async def test_cat_3_backup_line_no_llm_call(
    experiences, competency_model, raw_files_root
):
    """Cat 3 experiences emit one bullet from `experience.one_line` — no LLM call."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="should not be called")

    trace = [_make_trace(3, "03-desaysv")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    mock_llm.call.assert_not_awaited()
    assert len(out.section_g_bullets) == 1
    bullet = out.section_g_bullets[0]
    assert bullet.experience_id == "03-desaysv"
    assert bullet.final_category == 3
    assert "智能座舱" in bullet.text  # from one_line
    # R-7: Cat 3 backup line gets no disambiguator
    assert bullet.disambiguator_parenthetical is None


# --------------------------- 6. R-7 disambiguator on Cat 1 with mis_classification ---------------------------


@pytest.mark.asyncio
async def test_r7_disambiguator_applied_for_cat_1_mis_classification(
    experiences, competency_model, raw_files_root
):
    """Cat 1/2 with pass_b_lift = mis_classification → disambiguator present on bullet."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for("02-ipsos", "consumer survey")
    )

    trace = [_make_trace(1, "02-ipsos", lift="mis_classification")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert len(out.section_g_bullets) >= 1
    for bullet in out.section_g_bullets:
        assert bullet.disambiguator_parenthetical == "（益普索旗下战略咨询）"


# --------------------------- 7. R-7 disambiguator NOT applied for Cat 3 ---------------------------


@pytest.mark.asyncio
async def test_r7_disambiguator_skipped_for_cat_3(
    experiences, competency_model, raw_files_root
):
    """Even with disambiguator data on the experience, Cat 3 bullet gets no parenthetical."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="should not be called")

    # 03-desaysv has pure_recognition disambiguator, but as Cat 3 → no R-7 tag.
    trace = [_make_trace(3, "03-desaysv", lift="pure_recognition")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert len(out.section_g_bullets) == 1
    assert out.section_g_bullets[0].disambiguator_parenthetical is None


# --------------------------- 8. truthfulness pre-check happy path ---------------------------


@pytest.mark.asyncio
async def test_truthfulness_pre_check_passes_when_claim_in_raw(
    experiences, competency_model, raw_files_root
):
    mock_llm = AsyncMock()
    # `OSAT 五年战略规划` IS in the raw markdown for 01-kearney.
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for("01-kearney", "OSAT 五年战略规划")
    )

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert len(out.section_g_bullets) >= 1
    assert out._method == "llm"


# --------------------------- 9. truthfulness pre-check: granular drop, not whole-rewrite abort ---------------------------


def _llm_response_mixed_claims(experience_id: str) -> str:
    """One bullet with a SOURCED claim, one with an UNSOURCED claim."""
    return json.dumps(
        {
            "experience_id": experience_id,
            "final_category": 1,
            "bullets": [
                {
                    "id": f"{experience_id}-bullet-1",
                    "text": "Led value chain analysis across downstream tracks.",
                    "claimed_facts": ["value chain analysis"],  # present in raw
                },
                {
                    "id": f"{experience_id}-bullet-2",
                    "text": "Led $50M acquisition of an unrelated company.",
                    "claimed_facts": ["led $50M acquisition of unrelated company"],  # not in raw
                },
            ],
            "disambiguator_parenthetical": None,
            "decision_rationale": "Lead with industry research depth.",
        }
    )


@pytest.mark.asyncio
async def test_unsourced_claim_drops_bullet_keeps_sourced(
    experiences, competency_model, raw_files_root
):
    """An unsourced claim drops ONLY that bullet (granular fallback); the sourced
    bullet survives and the whole rewrite is NOT aborted. Previously the engine
    raised UnsourcedClaimError, which made action.py discard the entire deep
    rewrite and fall back to light tailoring (→ no bullets → Pass 3 skipped →
    R-18 demote). See live-smoke 2026-05-23."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_llm_response_mixed_claims("01-kearney"))

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    texts = [b.text for b in out.section_g_bullets]
    assert any("value chain analysis" in t for t in texts), "sourced bullet must survive"
    assert not any("$50M acquisition" in t for t in texts), "unsourced bullet must be dropped"
    assert out._method == "llm_partial"


@pytest.mark.asyncio
async def test_all_unsourced_yields_empty_bullets_without_raising(
    experiences, competency_model, raw_files_root
):
    """If every bullet for an experience is unsourced, that experience contributes
    zero bullets and the engine does NOT raise — partial recovery, llm_partial."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for(
            "01-kearney", "led $50M acquisition of unrelated company"
        )
    )

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert all("$50M acquisition" not in b.text for b in out.section_g_bullets)
    assert out._method == "llm_partial"


# --------------------------- 10. LLM CircuitOpen → fallback ---------------------------


@pytest.mark.asyncio
async def test_llm_circuit_open_raises_SubSkillUnavailable(
    experiences, competency_model, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=CircuitOpen("circuit open"))

    trace = [_make_trace(1, "01-kearney")]
    with pytest.raises(SubSkillUnavailable) as excinfo:
        await rewrite_bullets(
            experiences=experiences,
            selection_trace=trace,
            competency_model=competency_model,
            jd_text="JD",
            primary_lens="A_strategy_research",
            target_industry="internet_strategic",
            tier_assigned=2,
            raw_files_root=raw_files_root,
            llm=mock_llm,
        )

    assert excinfo.value.sub_skill == "resume_rewrite_engine"
    assert excinfo.value.llm_unreachable is True
    assert "circuit open" in str(excinfo.value)


# --------------------------- 11. malformed JSON → llm_partial ---------------------------


@pytest.mark.asyncio
async def test_malformed_json_marks_method_partial(
    experiences, competency_model, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="Sorry, I cannot comply.")

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert out._method == "llm_partial"
    # Section J still records the attempt, even if no bullets came through.
    assert any(
        e.experience_id == "01-kearney" for e in out.section_j_decision_log
    )


# --------------------------- 12. schema validation ---------------------------


@pytest.mark.asyncio
async def test_output_validates_against_schema(
    experiences, competency_model, raw_files_root, repo_root
):
    """Happy-path output must pass `rewrite-engine-output` schema validation."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for("01-kearney", "OSAT 五年战略规划")
    )

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    reg = SchemaRegistry(repo_root)
    payload = out.model_dump_jsonable()
    reg.validate("rewrite-engine-output", payload)  # raises if invalid


# --------------------------- 13. integration-style with real raw file ---------------------------


@pytest.mark.asyncio
@pytest.mark.skip(reason="requires user-specific experience data — adapt IDs to your own data after `make seed-sample`")
async def test_real_raw_kearney_with_in_raw_claim(
    experiences, competency_model, repo_root
):
    """End-to-end: real raw/01-kearney.md + a claim that IS substring of raw → passes."""
    real_raw_root = repo_root / "assets" / "experience-bank" / "raw"
    assert real_raw_root.is_dir()
    kearney_text = (real_raw_root / "01-kearney.md").read_text(encoding="utf-8")
    # Pick a phrase that is provably in the file (substring match).
    assert "战略规划" in kearney_text

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response_for(
            "01-kearney", "战略规划"  # short claim that is in raw
        )
    )

    trace = [_make_trace(1, "01-kearney")]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=real_raw_root,
        llm=mock_llm,
    )

    assert out._method == "llm"
    assert len(out.section_g_bullets) >= 1


# --------------------------- 14. None LLM → fallback ---------------------------


@pytest.mark.asyncio
async def test_none_llm_raises_SubSkillUnavailable(
    experiences, competency_model, raw_files_root
):
    trace = [_make_trace(1, "01-kearney")]
    with pytest.raises(SubSkillUnavailable) as excinfo:
        await rewrite_bullets(
            experiences=experiences,
            selection_trace=trace,
            competency_model=competency_model,
            jd_text="JD",
            primary_lens="A_strategy_research",
            target_industry="internet_strategic",
            tier_assigned=2,
            raw_files_root=raw_files_root,
            llm=None,
        )

    assert excinfo.value.sub_skill == "resume_rewrite_engine"
    assert excinfo.value.llm_unreachable is True
    assert "LLM provider not configured" in str(excinfo.value)


# --------------------------- 15. Tier 2 ordering: lifted disambiguator first ---------------------------


@pytest.mark.asyncio
async def test_tier_2_picks_lifted_disambiguator_first(
    experiences, competency_model, raw_files_root
):
    """Among equal-category Cat 2 entries, pass_b_lift != none sorts first."""
    responses = {
        "01-kearney": _llm_response_for("01-kearney", "OSAT 五年战略规划"),
        "02-ipsos": _llm_response_for("02-ipsos", "consumer survey"),
        "04-mercer": _llm_response_for("04-mercer", "comp benchmark"),
    }

    async def call_side_effect(*, system, user, max_tokens, temperature):
        for exp_id, resp in responses.items():
            if exp_id in user:
                return resp
        return responses["01-kearney"]

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=call_side_effect)

    # Three Cat 2 entries: ipsos has lift, others do not. Tier 2 should
    # pick ipsos + one of the others.
    trace = [
        _make_trace(2, "01-kearney"),
        _make_trace(2, "02-ipsos", lift="mis_classification"),
        _make_trace(2, "04-mercer"),
    ]
    out = await rewrite_bullets(
        experiences=experiences,
        selection_trace=trace,
        competency_model=competency_model,
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=2,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    rewritten_ids = {b.experience_id for b in out.section_g_bullets}
    assert "02-ipsos" in rewritten_ids  # lifted entry must be picked
    assert mock_llm.call.await_count == 2
