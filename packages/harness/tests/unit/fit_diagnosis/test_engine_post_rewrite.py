"""Unit tests for harness.fit_diagnosis (Wave 5 F3 backend, post_rewrite mode).

This is the Phase A (test contract) deliverable for F3. It covers
`build_diagnosis(mode="post_rewrite", ...)` per Section 8 of
`packages/strategy-modules/fit-diagnosis-engine/output-schema.md`:

  - Common header (mode=post_rewrite, ppaf_stage=late_feedback,
    current_resume_hash non-null sha256-shaped string).
  - Section 8-A — HM (highlights / concerns / comparison_risk).
  - Section 8-B — HRBP (keyword_hit_rate / hard_filter_match /
    advance_decision / decision_rationale).
  - Section 8-C — 6-axis radar with `citation` field per dim
    (spec extension over harness/review/ legacy contract).
  - Section 8-D — improvement_suggestions (capped at 5, effort enum).

Style mirrors `test_engine_pre_rewrite.py` — module-level helper
functions, no fixtures, AsyncMock-only LLM. Tests intentionally FAIL
today because `build_diagnosis(mode="post_rewrite", ...)` currently
raises NotImplementedError; Phase B (separate dispatch) replaces that
branch with the real implementation and these tests gate the cutover.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from harness.exceptions import SubSkillUnavailable
from harness.fit_diagnosis import build_diagnosis, fallback_diagnosis


# ----------------------------- stubs -----------------------------


def _stub_competency_model() -> dict:
    """A 9-section profile (keys-only) — used to mark `competency_complete`."""
    base: dict = {
        "section_b_core_hiring_logic": [
            {
                "priority_name": "Stakeholder management",
                "what_it_means": "Lead cross-functional PMs.",
                "why_it_matters": "Coordination is the binding constraint.",
                "credible_proof_signals": "Owned launches with 3+ XFN partners.",
            },
            {
                "priority_name": "Data fluency",
                "what_it_means": "Self-serve SQL + dashboards.",
                "why_it_matters": "Avoid blocking on analyst capacity.",
                "credible_proof_signals": "Shipped dashboards used in QBR.",
            },
        ],
        "section_c_qualification_model": {
            "tier_1_must_have": [
                {
                    "name": "PM experience",
                    "practical_meaning": "Owned roadmap end-to-end.",
                    "credible_proof_signals": "Documented PRDs.",
                }
            ],
            "tier_2_strongly_preferred": [
                {
                    "name": "B2B SaaS",
                    "practical_meaning": "Worked with enterprise buyers.",
                    "credible_proof_signals": "Closed enterprise deals.",
                }
            ],
            "tier_3_nice_to_have": [
                {"name": "ML literacy", "practical_meaning": "Reads ML papers."}
            ],
        },
    }
    # Pad to 9 section_* keys so `_competency_complete` returns True.
    for letter in ("a", "d", "e", "f", "g", "h", "i"):
        base[f"section_{letter}_stub"] = {}
    return base


def _stub_experience_trace() -> list[dict]:
    return [
        {
            "experience_id": "exp_pm_2023",
            "pass_a_tier": "必上展开",
            "pass_b_tier": "必上展开",
            "pass_c_tier": "必上展开",
            "final_category": 1,
        },
        {
            "experience_id": "exp_data_2022",
            "pass_a_tier": "次选简提",
            "pass_b_tier": "次选简提",
            "pass_c_tier": "次选简提",
            "final_category": 2,
        },
    ]


def _stub_match_matrix() -> dict:
    """Realistic-shape D06 / pre_rewrite-style matrix output that the
    impl may consume as upstream context. Tests don't assert on whether
    this is consumed; we just provide a believable shape so Phase B
    can use it if desired without test churn.
    """
    return {
        "competitiveness_rating": "above_mid",
        "matching_matrix": [
            {"text": "PM experience", "verdict": "strong_match"},
            {"text": "B2B SaaS", "verdict": "transferable"},
            {"text": "ML literacy", "verdict": "missing"},
        ],
        "integrated_assessment": "Strong PM background, missing ML.",
    }


def _stub_current_resume() -> str:
    """A short rewritten resume body — content is not load-bearing,
    only its presence + hashability matter for the header signature.
    """
    return (
        "% Rewritten resume — Wave 5 F3 test fixture.\n"
        "\\section{Experience}\n"
        "  \\textbf{Senior PM, Acme Corp} — Led 3 cross-functional launches; "
        "shipped dashboard adopted by 4 BU leads.\n"
        "\\section{Skills}\n"
        "  SQL, Python, prompt engineering, stakeholder management.\n"
    )


def _valid_review_obj(extra: dict | None = None) -> dict:
    """A valid Section 8 dict. Override any top-level field via `extra`."""
    base: dict = {
        "competitiveness_rating": "above_mid",
        "hm": {
            "highlights": ["Acme 2.1: led 3 cross-functional launches"],
            "concerns": ["summary: ML rigor unclear"],
            "comparison_risk": "Loses to candidates with applied-ML projects.",
        },
        "hrbp": {
            "keyword_hit_rate": 0.72,
            "hard_filter_match": {"degree": "match", "language": "match"},
            "advance_decision": "push_with_note",
            "decision_rationale": "Above bar but flag the ML gap in HM screen.",
        },
        "improvement_suggestions": [
            {"text": "Surface SQL+dashboard work in summary line", "effort": "wording"},
            {"text": "Add a B2B PM side-project bullet", "effort": "supplement_project"},
        ],
        "radar": {
            "dimensions": [
                {"name": "行业经验", "resume_score": 70, "jd_required": 80,
                 "citation": "Acme 2.1 — 3 yrs B2B PM"},
                {"name": "核心技能", "resume_score": 65, "jd_required": 85,
                 "citation": "Skills row — prompt engineering"},
                {"name": "数据能力", "resume_score": 60, "jd_required": 70,
                 "citation": "Acme 2.3 — dashboard adoption"},
                {"name": "沟通协作", "resume_score": 80, "jd_required": 75,
                 "citation": "Acme 2.1 — XFN launches"},
                {"name": "文化匹配", "resume_score": 70, "jd_required": 70,
                 "citation": "Summary — ownership signals"},
                {"name": "B2B产品", "resume_score": 50, "jd_required": 80,
                 "citation": "exp_pm_2023 — adjacent industry"},
            ]
        },
    }
    if extra:
        for k, v in extra.items():
            base[k] = v
    return base


def _valid_review_json(extra: dict | None = None) -> str:
    return json.dumps(_valid_review_obj(extra), ensure_ascii=False)


async def _call(
    mock_llm,
    *,
    current_resume: str | None = "<DEFAULT>",
    competency_complete: bool = True,
    target_market: str = "north-america",
    multi_jd: bool = False,
) -> dict:
    """Standard wrapper: invokes build_diagnosis(mode="post_rewrite", ...).

    `current_resume` defaults to a non-null short body so the header's
    `current_resume_hash` is populated; tests that exercise the
    "missing current_resume" branch override with None. The sentinel
    "<DEFAULT>" is used so an EXPLICIT current_resume=None passed by a
    test propagates through (instead of being substituted with the stub).
    """
    if current_resume == "<DEFAULT>":
        current_resume = _stub_current_resume()
    competency = _stub_competency_model() if competency_complete else {}
    return await build_diagnosis(
        mode="post_rewrite",
        target_market=target_market,
        jd_text="Senior PM, B2B SaaS. SQL, Python, stakeholder management.",
        competency_profile=competency,
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        multi_jd=multi_jd,
        current_resume=current_resume,
        llm=mock_llm,
    )


# ----------------------------- happy path -----------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_full_valid_review():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_review_json())
    out = await _call(mock)

    assert out["_method"] == "llm"
    assert out["sub_skill"] == "fit-diagnosis-engine"
    assert out["mode"] == "post_rewrite"
    assert out["ppaf_stage"] == "late_feedback"
    assert out["target_market"] == "north-america"
    assert out["multi_jd"] is False

    # Section 8-A — HM
    assert isinstance(out["hm"]["highlights"], list)
    assert len(out["hm"]["highlights"]) >= 1
    assert isinstance(out["hm"]["concerns"], list)
    assert isinstance(out["hm"]["comparison_risk"], str)
    assert out["hm"]["comparison_risk"]

    # Section 8-B — HRBP
    assert 0.0 <= out["hrbp"]["keyword_hit_rate"] <= 1.0
    assert isinstance(out["hrbp"]["hard_filter_match"], dict)
    assert out["hrbp"]["advance_decision"] in {
        "push_direct",
        "push_with_note",
        "screen_out",
    }
    assert isinstance(out["hrbp"]["decision_rationale"], str)

    # Section 8-C — radar (exactly 6 dims, each with citation)
    assert len(out["radar"]["dimensions"]) == 6
    for dim in out["radar"]["dimensions"]:
        assert isinstance(dim["name"], str) and dim["name"]
        assert 0 <= dim["resume_score"] <= 100
        assert 0 <= dim["jd_required"] <= 100
        assert isinstance(dim["citation"], str)

    # Section 8-D — improvement_suggestions (effort enum + cap)
    assert 0 <= len(out["improvement_suggestions"]) <= 5
    for sug in out["improvement_suggestions"]:
        assert isinstance(sug["text"], str) and sug["text"]
        assert sug["effort"] in {"wording", "supplement_project", "long_term"}


@pytest.mark.asyncio
async def test_happy_path_with_markdown_fences_parses_ok():
    fenced = "```json\n" + _valid_review_json() + "\n```"
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=fenced)
    out = await _call(mock)
    assert out["_method"] == "llm"
    assert len(out["radar"]["dimensions"]) == 6


# ----------------------------- LLM failure modes -----------------------------


@pytest.mark.asyncio
async def test_llm_circuit_open_returns_fallback():
    """CircuitOpen is a documented LLM failure mode — collapse to fallback."""
    from harness.llm.protocol import CircuitOpen

    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=CircuitOpen("circuit open"))
    with pytest.raises(SubSkillUnavailable) as exc:
        await _call(mock)
    assert exc.value.sub_skill == "fit_diagnosis_post_rewrite"
    assert exc.value.llm_unreachable is True


@pytest.mark.asyncio
async def test_unexpected_runtime_error_propagates():
    """Per Rule 1.1 — programmer-bug exceptions (RuntimeError) MUST surface."""
    mock = AsyncMock()
    mock.call = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await _call(mock)


@pytest.mark.asyncio
async def test_malformed_json_returns_fallback():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="Sorry, I cannot comply.")
    with pytest.raises(SubSkillUnavailable) as exc:
        await _call(mock)
    assert exc.value.sub_skill == "fit_diagnosis_post_rewrite"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_empty_response_returns_fallback():
    mock = AsyncMock()
    mock.call = AsyncMock(return_value="   ")
    with pytest.raises(SubSkillUnavailable) as exc:
        await _call(mock)
    assert exc.value.sub_skill == "fit_diagnosis_post_rewrite"
    assert exc.value.llm_unreachable is False


@pytest.mark.asyncio
async def test_llm_none_returns_fallback():
    """When llm=None, no LLM call is attempted; fallback is returned."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await _call(None)
    assert exc.value.sub_skill == "fit_diagnosis_post_rewrite"
    assert exc.value.llm_unreachable is True


# ----------------------------- post_rewrite-specific input contract -----


@pytest.mark.asyncio
async def test_post_rewrite_requires_current_resume():
    """Per spec: post_rewrite mode must receive a non-null current_resume.

    Phase B should raise ValueError when current_resume is None and
    mode == "post_rewrite" (the rewritten body is the load-bearing input
    for HM + radar simulation).
    """
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_review_json())
    with pytest.raises(ValueError, match="current_resume"):
        await _call(mock, current_resume=None)


@pytest.mark.asyncio
async def test_current_resume_hash_populated():
    """When current_resume is provided, header.inputs_signature.current_resume_hash
    is a non-null hex string (sha256-shaped: 16-64 hex chars).
    """
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_review_json())
    out = await _call(mock, current_resume=_stub_current_resume())

    sig = out["inputs_signature"]
    digest = sig["current_resume_hash"]
    assert digest is not None
    assert isinstance(digest, str)
    # SHA-256 is 64 hex chars; spec allows truncated hex (≥16) for
    # parity with `_stable_hash` used by jd_analysis_id /
    # competency_profile_id. Accept any hex string of length 16-64.
    assert 16 <= len(digest) <= 64
    assert all(c in "0123456789abcdef" for c in digest.lower())


@pytest.mark.asyncio
async def test_ppaf_stage_is_late_feedback():
    """post_rewrite mode → ppaf_stage MUST be 'late_feedback'."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_review_json())
    out = await _call(mock)
    assert out["mode"] == "post_rewrite"
    assert out["ppaf_stage"] == "late_feedback"


# ----------------------------- partial / degraded shapes ----------------


@pytest.mark.asyncio
async def test_missing_radar_key_repaired_to_partial():
    """LLM omits the radar key entirely → padded with placeholder dims,
    `_method == 'llm_partial'`, exactly 6 dims emitted."""
    obj = _valid_review_obj()
    del obj["radar"]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert len(out["radar"]["dimensions"]) == 6
    # Default-axis names should be used for the placeholders.
    assert out["radar"]["dimensions"][0]["name"]


@pytest.mark.asyncio
async def test_invalid_advance_decision_repaired():
    obj = _valid_review_obj()
    obj["hrbp"]["advance_decision"] = "promote_to_offer"  # not in enum
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert out["hrbp"]["advance_decision"] == "screen_out"


@pytest.mark.asyncio
async def test_invalid_competitiveness_rating_repaired():
    obj = _valid_review_obj()
    obj["competitiveness_rating"] = "stellar"  # not in 5-level enum
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert out["competitiveness_rating"] == "mid"


@pytest.mark.asyncio
async def test_radar_with_4_dims_padded_to_6():
    obj = _valid_review_obj()
    obj["radar"]["dimensions"] = obj["radar"]["dimensions"][:4]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert len(out["radar"]["dimensions"]) == 6


@pytest.mark.asyncio
async def test_radar_with_9_dims_truncated_to_6():
    obj = _valid_review_obj()
    extra = [
        {"name": f"x{i}", "resume_score": 50, "jd_required": 50, "citation": ""}
        for i in range(3)
    ]
    obj["radar"]["dimensions"] = obj["radar"]["dimensions"] + extra
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert len(out["radar"]["dimensions"]) == 6


@pytest.mark.asyncio
async def test_keyword_hit_rate_clamped_to_0_1():
    obj = _valid_review_obj()
    obj["hrbp"]["keyword_hit_rate"] = 1.5
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert out["hrbp"]["keyword_hit_rate"] == 1.0


@pytest.mark.asyncio
async def test_radar_score_clamped_to_0_100():
    obj = _valid_review_obj()
    obj["radar"]["dimensions"][0]["resume_score"] = 150
    obj["radar"]["dimensions"][1]["jd_required"] = -10
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert out["radar"]["dimensions"][0]["resume_score"] == 100
    assert out["radar"]["dimensions"][1]["jd_required"] == 0


@pytest.mark.asyncio
async def test_invalid_hard_filter_value_dropped():
    """A hard_filter entry whose value is outside {match, mismatch, uncertain}
    is dropped; the result is marked llm_partial and other valid entries
    are preserved."""
    obj = _valid_review_obj()
    obj["hrbp"]["hard_filter_match"]["timing"] = "schrodinger"  # invalid
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert "timing" not in out["hrbp"]["hard_filter_match"]
    # Valid sibling entries survive the repair.
    assert out["hrbp"]["hard_filter_match"]["degree"] == "match"


@pytest.mark.asyncio
async def test_improvement_suggestions_capped_at_5():
    obj = _valid_review_obj()
    obj["improvement_suggestions"] = [
        {"text": f"item {i}", "effort": "wording"} for i in range(8)
    ]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert len(out["improvement_suggestions"]) == 5


# ----------------------------- citation field (spec extension) ---------


@pytest.mark.asyncio
async def test_radar_dimension_includes_citation_field():
    """Each of the 6 radar dimensions MUST carry a `citation` string field
    per Section 8-C (spec extension over harness/review/ legacy)."""
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=_valid_review_json())
    out = await _call(mock)

    assert out["_method"] == "llm"
    assert len(out["radar"]["dimensions"]) == 6
    for dim in out["radar"]["dimensions"]:
        assert "citation" in dim, f"missing citation in dim {dim!r}"
        assert isinstance(dim["citation"], str)


@pytest.mark.asyncio
async def test_radar_dimension_missing_citation_repaired():
    """LLM omits citation on at least one dim → repaired to empty string
    default; `_method == 'llm_partial'` flags the partial fill."""
    obj = _valid_review_obj()
    # Strip citation from the first dim only.
    del obj["radar"]["dimensions"][0]["citation"]
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(obj, ensure_ascii=False))
    out = await _call(mock)

    assert out["_method"] == "llm_partial"
    assert len(out["radar"]["dimensions"]) == 6
    # Repaired citation is a string (empty default is acceptable).
    assert isinstance(out["radar"]["dimensions"][0]["citation"], str)


# ----------------------------- mode handling -----------------------------


@pytest.mark.asyncio
async def test_invalid_mode_raises_value_error():
    """A bogus mode value must raise ValueError before any LLM call."""
    mock = AsyncMock()
    with pytest.raises(ValueError, match="pre_rewrite"):
        await build_diagnosis(
            mode="bogus",
            target_market="north-america",
            jd_text="jd",
            competency_profile=_stub_competency_model(),
            experience_selection_trace=_stub_experience_trace(),
            lens="C_product_ops",
            current_resume=_stub_current_resume(),
            llm=mock,
        )


@pytest.mark.asyncio
async def test_pre_rewrite_mode_unaffected():
    """Calling build_diagnosis(mode='pre_rewrite', ...) must keep working
    after Phase B lands — F3 is additive, no regression in the F1 path."""
    # Use a minimal valid pre_rewrite Section 4 payload so the existing
    # pre_rewrite normalizer accepts it without flagging partial.
    section_4_payload = {
        "matching_matrix": [
            {
                "text": "PM experience",
                "evidence": "Acme 2.1 — 3 yrs B2B PM ownership.",
                "verdict": "strong_match",
                "source": "section_b_priority",
                "bridging_or_closure": "",
            }
        ],
        "integrated_assessment": (
            "Strong PM background with shipped B2B launches. Biggest gap is "
            "applied ML rigor. Above-mid pool position with bridgeable "
            "interview narrative."
        ),
        "optimization_boundary": {
            "rewriting_can_solve": [
                "关键词显化: surface SQL+dashboard work",
            ],
            "rewriting_cannot_solve": [
                "ML rigor gap: missing applied-ML projects; supplement",
            ],
        },
    }
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=json.dumps(section_4_payload, ensure_ascii=False))
    out = await build_diagnosis(
        mode="pre_rewrite",
        target_market="north-america",
        jd_text="Senior PM, B2B SaaS. SQL, Python, stakeholder management.",
        competency_profile=_stub_competency_model(),
        experience_selection_trace=_stub_experience_trace(),
        lens="C_product_ops",
        llm=mock,
    )
    assert out["mode"] == "pre_rewrite"
    assert out["ppaf_stage"] == "planning"
    # current_resume_hash must be None on pre_rewrite.
    assert out["inputs_signature"]["current_resume_hash"] is None
    assert "matching_matrix" in out


@pytest.mark.asyncio
async def test_competitiveness_rating_in_5_level_enum():
    """Header.competitiveness_rating must be one of the canonical 5 values
    in both happy-path and fallback branches."""
    valid_ratings = {"high", "above_mid", "mid", "below_mid", "low"}

    # Happy path
    mock_ok = AsyncMock()
    mock_ok.call = AsyncMock(return_value=_valid_review_json())
    out_ok = await _call(mock_ok)
    assert out_ok["competitiveness_rating"] in valid_ratings

    # Fallback path (manual helper)
    out_fb = fallback_diagnosis(mode="post_rewrite")
    assert out_fb["competitiveness_rating"] in valid_ratings
