"""F2c Phase A — test contract for rewrite-engine consuming fit_diagnosis_pre_rewrite.

These tests are part of Wave 5 F2c (rewrite-engine consumes the
PLANNING-stage `fit_diagnosis_pre_rewrite` matrix). They are written
BEFORE the engine implementation lands (two-phase TDD) — every assertion
in this module is expected to fail today with::

    TypeError: rewrite_bullets() got an unexpected keyword argument
    'fit_diagnosis_pre_rewrite'

Phase B (next commit) modifies `harness/rewrite/engine.py` so
`rewrite_bullets(...)` accepts the new optional kwarg
`fit_diagnosis_pre_rewrite: dict | None = None` and uses its
`matching_matrix` verdicts + `optimization_boundary` closure paths to
shape `section_g_bullets` and `section_j_decision_log`.

================================================================
TEST PLAN
================================================================

Behavioral contract under test
-------------------------------
1. Backward compatibility (CRITICAL):
   * `fit_diagnosis_pre_rewrite=None` → identical output to today's engine.
   * Kwarg omitted entirely → identical output to today's engine.
   * `matching_matrix == []` → identical output to None case.
   * `_method == "fallback_no_llm"` on the diagnosis → identical to None
     (don't trust priorities synthesised from a fallback diagnosis).

2. Verdict-driven prioritization:
   * `verdict == "strong_match"` whose evidence cites a Cat 1/2/3
     experience id → that experience appears in `section_g_bullets`
     (and may be boosted into the top slots).
   * `verdict == "transferable"` whose evidence cites an experience →
     that experience still appears, AND `section_j_decision_log` carries
     an entry mentioning the `bridging_or_closure` plan for it.
   * `verdict == "missing"` whose `bridging_or_closure` ends in
     `not_closeable` → engine MUST NOT invent a synthetic bullet for
     that JD requirement. Cat 4 exclusion already handles this.

3. Optimization boundary closure paths:
   * Items in `optimization_boundary.rewriting_cannot_solve` ending in
     `; supplement` → `section_j_decision_log` carries a
     "supplement opportunity" entry.
   * Items ending in `; accept` → `section_j_decision_log` carries a
     "known gap, accepted" entry.

4. Cat 4 still wins:
   * Even when a `strong_match` matrix item references a Cat 4
     experience, the Cat 4 exclusion overrides; bullet stays out.

5. Operator surfacing (bonus):
   * `competitiveness_rating == "low"` → an operator-visible warning
     entry appears in `section_j_decision_log`.
   * `section_j_decision_log` carries a count of strong_match items
     consumed.

Mocking strategy
----------------
* LLM: `unittest.mock.AsyncMock`. Per-experience JSON responses built by
  the same `_llm_response_for(...)` shape that `test_rewrite_engine.py`
  uses, so `claimed_facts` substring-verifies against the synthetic raw
  markdown shipped by `_raw_files_root(tmp_path)`.
* `selection_trace` + `competency_model` + `experiences`: real-shape
  fixtures built by module-level `_stub_*()` helpers (mirrors the
  helper pattern in `tests/unit/fit_diagnosis/test_engine_pre_rewrite.py`).
* `fit_diagnosis_pre_rewrite`: built per-test by `_stub_fit_diagnosis(...)`
  matching the production shape from `harness.fit_diagnosis.engine`
  (`build_diagnosis(mode="pre_rewrite", ...)`).

Out of scope
------------
* No UI, no Playwright. Backend behavior only.
* No real LLM, no real backend, no `assets/` reads (raw files are
  written into `tmp_path`).
* No Pass-3 semantic verification — substring gate only (Wave 4 D.4
  will replace it).
* No caller wiring — F2.5 / dogfood iteration will hook the new kwarg
  into `harness/repl/stages/action.py`.

CRITICAL — Phase A constraints
------------------------------
* Phase A ships TESTS ONLY. `harness/rewrite/engine.py` is NOT modified
  in this commit.
* The existing `tests/unit/test_rewrite_engine.py` is NOT modified —
  this file is purely additive.
* Every assertion below SHOULD fail today (expected) once the
  `fit_diagnosis_pre_rewrite=` kwarg is added to the call sites — the
  engine doesn't accept that kwarg yet, so tests trip on a TypeError
  at import-time of the call. That is the documented starting state.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from harness.exceptions import SubSkillUnavailable
from harness.rewrite import RewriteOutput, rewrite_bullets


# ============================================================
# Module-level stub helpers (mirrors fit_diagnosis test style)
# ============================================================


def _stub_experiences() -> list[dict]:
    """4 experiences spanning Cat 1/2/3/4. Mirrors test_rewrite_engine.py shape."""
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
            "disambiguator_per_industry": {},
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


def _stub_selection_trace() -> list[dict]:
    """4-row selection trace covering Cat 1, Cat 2, Cat 3, Cat 4."""
    return [
        {
            "experience_id": "01-kearney",
            "pass_a_tier": "上展开",
            "pass_b_tier": "上展开",
            "pass_b_lift": "none",
            "pass_c_tier": "上展开",
            "pass_c_ai_pressure": "none",
            "final_category": 1,
        },
        {
            "experience_id": "02-ipsos",
            "pass_a_tier": "上展开",
            "pass_b_tier": "上展开",
            "pass_b_lift": "mis_classification",
            "pass_c_tier": "上展开",
            "pass_c_ai_pressure": "none",
            "final_category": 2,
        },
        {
            "experience_id": "03-desaysv",
            "pass_a_tier": "上展开",
            "pass_b_tier": "上展开",
            "pass_b_lift": "none",
            "pass_c_tier": "上展开",
            "pass_c_ai_pressure": "none",
            "final_category": 3,
        },
        {
            "experience_id": "04-mercer",
            "pass_a_tier": "上展开",
            "pass_b_tier": "上展开",
            "pass_b_lift": "none",
            "pass_c_tier": "上展开",
            "pass_c_ai_pressure": "none",
            "final_category": 4,
        },
    ]


def _stub_competency_model() -> dict:
    """Minimal 9-section competency model — same shape as test_rewrite_engine.py."""
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
        "section_c_qualification_model": {
            "tier_1_must_have": [],
            "tier_2_strongly_preferred": [],
            "tier_3_nice_to_have": [],
        },
        "section_h_strategy_implications": {
            "emphasize_most": "Quantified impact and structured analysis.",
            "top_half_content": "Lead with strategy projects; surface frameworks.",
        },
    }


def _stub_fit_diagnosis(
    *,
    matrix: list[dict] | None = None,
    can_solve: list[str] | None = None,
    cannot_solve: list[str] | None = None,
    method: str = "llm",
    competitiveness_rating: str = "above_mid",
) -> dict:
    """Build a fit_diagnosis_pre_rewrite dict matching production shape.

    Mirrors `harness/fit_diagnosis/engine.py:build_diagnosis(mode="pre_rewrite")`
    output. All knobs are individually overridable per-test.
    """
    return {
        "sub_skill": "fit-diagnosis-engine",
        "mode": "pre_rewrite",
        "ppaf_stage": "planning",
        "target_market": "north-america",
        "competitiveness_rating": competitiveness_rating,
        "matching_matrix": matrix if matrix is not None else [],
        "integrated_assessment": "stub assessment",
        "optimization_boundary": {
            "rewriting_can_solve": can_solve or [],
            "rewriting_cannot_solve": cannot_solve or [],
        },
        "multi_jd": False,
        "multi_jd_coverage": None,
        "spread_flag": None,
        "confidence": "high",
        "inputs_signature": {
            "current_resume_hash": None,
            "jd_analysis_id": "test_jd",
            "competency_profile_id": "test_profile",
        },
        "_method": method,
    }


def _llm_response_for(
    experience_id: str,
    claim_text: str,
    *,
    n_bullets: int = 1,
) -> str:
    """JSON response that the engine can parse + verify via substring gate.

    `claim_text` MUST appear verbatim in the experience's raw markdown
    (the substring truthfulness gate). Helpers below write raw files
    that contain `claim_text` for each experience referenced here.
    """
    bullets = [
        {
            "id": f"{experience_id}-bullet-{i + 1}",
            "text": claim_text,
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
            "decision_rationale": "stub rationale",
        }
    )


def _stub_llm() -> AsyncMock:
    """Happy-path AsyncMock LLM. Routes per-experience by inspecting `user` prompt."""
    responses = {
        "01-kearney": _llm_response_for("01-kearney", "OSAT 五年战略规划"),
        "02-ipsos": _llm_response_for("02-ipsos", "consumer survey"),
        "04-mercer": _llm_response_for("04-mercer", "comp benchmark"),
    }

    async def call_side_effect(*, system, user, max_tokens, temperature):
        for exp_id, resp in responses.items():
            if exp_id in user:
                return resp
        # Safe default — Cat 1 response is verifiable against 01-kearney raw.
        return responses["01-kearney"]

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=call_side_effect)
    return mock_llm


# ============================================================
# Pytest fixtures (raw markdown root reuses the same shape as test_rewrite_engine.py)
# ============================================================


@pytest.fixture
def raw_files_root(tmp_path: Path) -> Path:
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


# ============================================================
# Section 2 — required test cases (12 total)
# ============================================================


# --- 1. backward compat: explicit None ---


@pytest.mark.asyncio
async def test_backward_compat_when_fit_diagnosis_is_None(raw_files_root):
    """fit_diagnosis_pre_rewrite=None → identical output to today's engine.

    Asserts the kwarg is accepted AND when None has no effect on
    section_g_bullets / section_j_decision_log shape.
    """
    mock_llm = _stub_llm()
    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=None,
    )

    assert isinstance(out, RewriteOutput)
    # Cat 1 + Cat 2 (LLM) + Cat 3 (deterministic). Cat 4 dropped.
    ids = {b.experience_id for b in out.section_g_bullets}
    assert "01-kearney" in ids
    assert "02-ipsos" in ids
    assert "03-desaysv" in ids
    assert "04-mercer" not in ids
    # Decision log entries match today's engine pattern.
    log_ids = {entry.experience_id for entry in out.section_j_decision_log}
    assert "04-mercer" not in log_ids


# --- 2. backward compat: kwarg omitted entirely ---


@pytest.mark.asyncio
async def test_backward_compat_when_fit_diagnosis_omitted(raw_files_root):
    """Omitting the kwarg entirely must work — defaults to None."""
    mock_llm = _stub_llm()
    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
    )

    assert isinstance(out, RewriteOutput)
    ids = {b.experience_id for b in out.section_g_bullets}
    assert "01-kearney" in ids
    assert "02-ipsos" in ids
    assert "03-desaysv" in ids
    assert "04-mercer" not in ids


# --- 3. strong_match → experience appears in bullets ---


@pytest.mark.asyncio
async def test_strong_match_experience_appears_in_bullets(raw_files_root):
    """A strong_match matrix item citing a Cat 1 experience id → that experience
    is in section_g_bullets.
    """
    matrix = [
        {
            "text": "Lead industry research with structured frameworks",
            "evidence": "01-kearney: OSAT 五年战略规划 demonstrates this directly",
            "verdict": "strong_match",
            "source": "section_b_priority",
            "bridging_or_closure": "",
        },
    ]
    fit = _stub_fit_diagnosis(matrix=matrix)
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    ids = {b.experience_id for b in out.section_g_bullets}
    assert "01-kearney" in ids


# --- 4. transferable → decision_log notes the bridge plan ---


@pytest.mark.asyncio
async def test_transferable_experience_decision_log_notes_bridge(raw_files_root):
    """A transferable matrix item → section_j_decision_log mentions the
    bridging_or_closure plan for the cited experience.
    """
    bridge_text = "preferred; surface SQL via skills row"
    matrix = [
        {
            "text": "Hands-on SQL for ad-hoc data pulls",
            "evidence": "02-ipsos consumer survey work involved data analysis",
            "verdict": "transferable",
            "source": "section_c_tier_2",
            "bridging_or_closure": bridge_text,
        },
    ]
    fit = _stub_fit_diagnosis(matrix=matrix)
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    # Some entry in decision_log mentions the bridge plan for 02-ipsos.
    found = False
    for entry in out.section_j_decision_log:
        rationale = (entry.rationale or "").lower()
        if entry.experience_id == "02-ipsos" and (
            "bridge" in rationale
            or "transferable" in rationale
            or "sql" in rationale
            or "surface sql" in rationale
        ):
            found = True
            break
    assert found, (
        f"Expected a decision_log entry for 02-ipsos mentioning the bridge plan "
        f"{bridge_text!r}; got entries: "
        f"{[(e.experience_id, e.decision, e.rationale) for e in out.section_j_decision_log]}"
    )


# --- 5. missing + not_closeable → no synthetic bullet invented ---


@pytest.mark.asyncio
async def test_missing_with_not_closeable_does_not_invent_bullet(raw_files_root):
    """A missing matrix item with `; not_closeable` closure must NOT cause
    the engine to invent a synthetic Section G bullet.
    """
    matrix = [
        {
            "text": "Direct people-management of >5 ICs",
            "evidence": "(no prior IC-management experience in candidate's bank)",
            "verdict": "missing",
            "source": "section_c_tier_1",
            "bridging_or_closure": "preferred; not_closeable",
        },
    ]
    fit = _stub_fit_diagnosis(matrix=matrix)
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    # No bullet text should reference "Direct people-management" nor any
    # other JD-requirement language fabricated from the missing item.
    for bullet in out.section_g_bullets:
        assert "Direct people-management" not in bullet.text
        assert "not_closeable" not in bullet.text
    # Every bullet must trace to one of the actual experience ids in the
    # candidate's experience bank — no synthetic experience_id fabricated.
    real_ids = {e["id"] for e in _stub_experiences()}
    for bullet in out.section_g_bullets:
        assert bullet.experience_id in real_ids


# --- 6. optimization_boundary supplement → decision_log entry ---


@pytest.mark.asyncio
async def test_optimization_boundary_supplement_logged(raw_files_root):
    """`rewriting_cannot_solve` items ending in `; supplement` must show up
    in section_j_decision_log as a 'supplement opportunity' style entry.
    """
    fit = _stub_fit_diagnosis(
        cannot_solve=["ML rigor: no applied-ML cases; supplement"],
    )
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    found = False
    for entry in out.section_j_decision_log:
        decision = (entry.decision or "").lower()
        rationale = (entry.rationale or "").lower()
        if "supplement" in decision or "supplement" in rationale:
            found = True
            break
    assert found, (
        "Expected a decision_log entry surfacing the 'supplement' opportunity "
        "from optimization_boundary.rewriting_cannot_solve; got: "
        f"{[(e.experience_id, e.decision, e.rationale) for e in out.section_j_decision_log]}"
    )


# --- 7. optimization_boundary accept → decision_log entry ---


@pytest.mark.asyncio
async def test_optimization_boundary_accept_logged(raw_files_root):
    """`rewriting_cannot_solve` items ending in `; accept` must show up in
    section_j_decision_log as a 'known gap, accepted' style entry.
    """
    fit = _stub_fit_diagnosis(
        cannot_solve=["education tier: non-target MBA; accept"],
    )
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    found = False
    for entry in out.section_j_decision_log:
        decision = (entry.decision or "").lower()
        rationale = (entry.rationale or "").lower()
        if "accept" in decision or "accepted" in decision or "accept" in rationale:
            found = True
            break
    assert found, (
        "Expected a decision_log entry surfacing the 'accept' gap from "
        "optimization_boundary.rewriting_cannot_solve; got: "
        f"{[(e.experience_id, e.decision, e.rationale) for e in out.section_j_decision_log]}"
    )


# --- 8. Cat 4 still dropped even when strong_match cites it ---


@pytest.mark.asyncio
async def test_cat_4_still_dropped_even_if_strong_match(raw_files_root):
    """Cat 4 exclusion overrides matrix prioritization. A strong_match item
    referencing 04-mercer (Cat 4) must NOT cause it to land in section_g.
    """
    matrix = [
        {
            "text": "Compensation benchmarking expertise",
            "evidence": "04-mercer comp benchmark study is a perfect fit",
            "verdict": "strong_match",
            "source": "section_c_tier_1",
            "bridging_or_closure": "",
        },
    ]
    fit = _stub_fit_diagnosis(matrix=matrix)
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    ids = {b.experience_id for b in out.section_g_bullets}
    assert "04-mercer" not in ids, (
        "Cat 4 exclusion must override fit_diagnosis prioritization. "
        f"Got bullets for: {ids}"
    )


# --- 9. empty matching_matrix is a no-op (== None case) ---


@pytest.mark.asyncio
async def test_empty_matching_matrix_no_op(raw_files_root):
    """fit_diagnosis present but matching_matrix=[] → behaviour matches
    the None case (no priority shift, no extra log entries from matrix).
    """
    fit_empty = _stub_fit_diagnosis(matrix=[])
    mock_llm_a = _stub_llm()
    mock_llm_b = _stub_llm()

    out_with = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm_a,
        fit_diagnosis_pre_rewrite=fit_empty,
    )
    out_none = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm_b,
        fit_diagnosis_pre_rewrite=None,
    )

    ids_with = {b.experience_id for b in out_with.section_g_bullets}
    ids_none = {b.experience_id for b in out_none.section_g_bullets}
    assert ids_with == ids_none


# --- 10. fallback _method → treated as None ---


@pytest.mark.asyncio
async def test_fallback_fit_diagnosis_raises_SubSkillUnavailable(raw_files_root):
    """fit_diagnosis with `_method == "fallback_no_llm"` → engine raises SubSkillUnavailable.

    We don't trust priorities derived from a fallback diagnosis.
    """
    matrix = [
        {
            "text": "Lead industry research with structured frameworks",
            "evidence": "01-kearney: OSAT 五年战略规划",
            "verdict": "strong_match",
            "source": "section_b_priority",
            "bridging_or_closure": "",
        },
    ]
    fit_fallback = _stub_fit_diagnosis(matrix=matrix, method="fallback_no_llm")
    mock_llm = _stub_llm()

    with pytest.raises(SubSkillUnavailable) as excinfo:
        await rewrite_bullets(
            experiences=_stub_experiences(),
            selection_trace=_stub_selection_trace(),
            competency_model=_stub_competency_model(),
            jd_text="JD",
            primary_lens="A_strategy_research",
            target_industry="internet_strategic",
            tier_assigned=3,
            raw_files_root=raw_files_root,
            llm=mock_llm,
            fit_diagnosis_pre_rewrite=fit_fallback,
        )

    assert excinfo.value.sub_skill == "resume_rewrite_engine"
    assert excinfo.value.llm_unreachable is False
    assert "upstream fit_diagnosis returned fallback" in str(excinfo.value)


# --- 11. low competitiveness rating → operator warning entry ---


@pytest.mark.asyncio
async def test_competitiveness_rating_low_emits_decision_log_warning(raw_files_root):
    """Bonus: when competitiveness_rating == 'low', surface an operator
    warning entry in section_j_decision_log so the operator sees the signal.
    """
    fit = _stub_fit_diagnosis(competitiveness_rating="low")
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    found = False
    for entry in out.section_j_decision_log:
        decision = (entry.decision or "").lower()
        rationale = (entry.rationale or "").lower()
        if "low" in decision or "low" in rationale or "competitiveness" in rationale:
            found = True
            break
    assert found, (
        "Expected a decision_log entry surfacing the low competitiveness rating; "
        f"got: {[(e.experience_id, e.decision, e.rationale) for e in out.section_j_decision_log]}"
    )


# --- 12. strong_match count is logged ---


@pytest.mark.asyncio
async def test_strong_match_count_logged(raw_files_root):
    """Bonus: section_j_decision_log carries a count (or summary-style
    mention) of strong_match items consumed from the matrix.
    """
    matrix = [
        {
            "text": "Industry framing",
            "evidence": "01-kearney OSAT case",
            "verdict": "strong_match",
            "source": "section_b_priority",
            "bridging_or_closure": "",
        },
        {
            "text": "Quantitative survey design",
            "evidence": "02-ipsos consumer survey",
            "verdict": "strong_match",
            "source": "section_c_tier_1",
            "bridging_or_closure": "",
        },
        {
            "text": "Hands-on SQL",
            "evidence": "(none)",
            "verdict": "missing",
            "source": "section_c_tier_2",
            "bridging_or_closure": "preferred; long_term",
        },
    ]
    fit = _stub_fit_diagnosis(matrix=matrix)
    mock_llm = _stub_llm()

    out = await rewrite_bullets(
        experiences=_stub_experiences(),
        selection_trace=_stub_selection_trace(),
        competency_model=_stub_competency_model(),
        jd_text="JD",
        primary_lens="A_strategy_research",
        target_industry="internet_strategic",
        tier_assigned=3,
        raw_files_root=raw_files_root,
        llm=mock_llm,
        fit_diagnosis_pre_rewrite=fit,
    )

    found_count = False
    for entry in out.section_j_decision_log:
        decision = (entry.decision or "").lower()
        rationale = (entry.rationale or "").lower()
        # Either explicit count "2" or "strong_match" word in summary entry.
        if (
            "strong_match" in decision
            or "strong_match" in rationale
            or "2 strong" in rationale
            or "matrix" in rationale
        ):
            found_count = True
            break
    assert found_count, (
        "Expected a decision_log summary entry mentioning the count of "
        "strong_match items consumed from the matrix; got: "
        f"{[(e.experience_id, e.decision, e.rationale) for e in out.section_j_decision_log]}"
    )
