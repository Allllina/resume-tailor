"""Unit tests for selection/three_pass.py — Wave 4 D.1."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.selection.three_pass import (
    ExperienceTrace,
    run_three_pass,
)


# --------------------------------------------------------------------------- #
# Fixture helpers                                                              #
# --------------------------------------------------------------------------- #


def _exp(
    *,
    exp_id: str = "X",
    recognition: str | None = None,
    fit: str | None = None,
    ai_fluency: str | None = None,
    industry: str = "internet_strategic",
    lens: str = "C_product_ops",
    cell_shape: str = "score",  # "score" | "value" | "string"
    disambiguator_type: str | None = None,
) -> dict:
    """Build a minimal experience dict for a single industry+lens cell."""
    def _cell(value: str | None) -> object:
        if value is None:
            return None
        if cell_shape == "string":
            return value
        if cell_shape == "value":
            return {"value": value}
        return {"score": value}

    out: dict = {
        "id": exp_id,
        "recognition_per_industry": {industry: _cell(recognition)},
        "vertical_fit_per_lens": {lens: _cell(fit)},
    }
    if ai_fluency is not None:
        out["ai_digital_fluency"] = {"score": ai_fluency}
    if disambiguator_type is not None:
        out["disambiguator_per_industry"] = {
            industry: {"type": disambiguator_type, "text": "(test)", "rationale": "(test)"}
        }
    return out


def _competency_with_ai_keywords(*keywords: str) -> dict:
    """Section D keyword architecture loaded with the given keywords."""
    return {
        "section_d_keyword_architecture": {
            "tier_1_core_role": list(keywords),
            "tier_2_capability": [],
            "tier_3_tools_methods": [],
            "tier_4_action_verbs": [],
            "tier_5_semantic_equivalents": [],
        }
    }


async def _run_one(experience: dict, competency_model: dict | None = None) -> ExperienceTrace:
    """Run the selector on a single experience and return its trace."""
    traces = await run_three_pass(
        experiences=[experience],
        jd_text="(unused)",
        primary_lens="C_product_ops",
        target_industry="internet_strategic",
        competency_model=competency_model,
    )
    assert len(traces) == 1
    return traces[0]


# --------------------------------------------------------------------------- #
# Pass A grid                                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recognition,fit,expected",
    [
        # high recognition rows
        ("high", "core", "必上展开"),
        ("high", "adjacent", "上展开"),
        ("high", "weak", "砍"),
        ("high", "missing", "砍"),
        # medium recognition rows (same as high per simplified grid)
        ("medium", "core", "必上展开"),
        ("medium", "adjacent", "上展开"),
        ("medium", "weak", "砍"),
        ("medium", "missing", "砍"),
        # low recognition rows
        ("low", "core", "单bullet"),
        ("low", "adjacent", "backup行"),
        ("low", "weak", "砍"),
        ("low", "missing", "砍"),
    ],
)
async def test_pass_a_grid(recognition: str, fit: str, expected: str):
    """5×4 cross-grid behavior per ARCHITECTURE.md §7b + recognition-rubric §9."""
    trace = await _run_one(_exp(recognition=recognition, fit=fit))
    assert trace["pass_a_tier"] == expected
    # Pass B/C with no disambiguator + no AI pressure shouldn't move it.
    assert trace["pass_b_tier"] == expected
    assert trace["pass_b_lift"] == "none"
    assert trace["pass_c_tier"] == expected
    assert trace["pass_c_ai_pressure"] == "none"


@pytest.mark.asyncio
async def test_pass_a_handles_value_cell_shape():
    """Wave 2.7 auto_scorer cells use {value: ...} shape."""
    trace = await _run_one(_exp(recognition="high", fit="core", cell_shape="value"))
    assert trace["pass_a_tier"] == "必上展开"


@pytest.mark.asyncio
async def test_pass_a_handles_string_cell_shape():
    """Bare-string cells (legacy) should also parse."""
    trace = await _run_one(_exp(recognition="high", fit="core", cell_shape="string"))
    assert trace["pass_a_tier"] == "必上展开"


# --------------------------------------------------------------------------- #
# Pass A null fallback                                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_pass_a_null_recognition_treated_as_low():
    """null recognition → conservative low row; with core fit → 单bullet."""
    trace = await _run_one(_exp(recognition=None, fit="core"))
    assert trace["pass_a_tier"] == "单bullet"


@pytest.mark.asyncio
async def test_pass_a_null_fit_treated_as_missing():
    """null fit → conservative missing → 砍."""
    trace = await _run_one(_exp(recognition="high", fit=None))
    assert trace["pass_a_tier"] == "砍"


@pytest.mark.asyncio
async def test_pass_a_missing_industry_cell_falls_back_to_low():
    """If target_industry not present in recognition_per_industry, treat as low."""
    exp = {
        "id": "X",
        "recognition_per_industry": {"some_other_industry": {"score": "high"}},
        "vertical_fit_per_lens": {"C_product_ops": {"score": "core"}},
    }
    trace = await _run_one(exp)
    assert trace["pass_a_tier"] == "单bullet"  # low × core


# --------------------------------------------------------------------------- #
# Pass B disambiguator                                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_pass_b_mis_classification_lifts_low_to_above():
    """mis_classification on (low, core) = 单bullet → 上展开 (one tier up).

    Mis-classification ceiling rule R-8: cannot reach 必上展开 unless
    base_recognition >= medium; one-tier lift from 单bullet is 上展开,
    which is allowed.
    """
    trace = await _run_one(
        _exp(recognition="low", fit="core", disambiguator_type="mis_classification")
    )
    assert trace["pass_a_tier"] == "单bullet"
    assert trace["pass_b_tier"] == "上展开"
    assert trace["pass_b_lift"] == "mis_classification"


@pytest.mark.asyncio
async def test_pass_b_mis_classification_lifts_medium_to_top():
    """mis_classification on (medium, adjacent) = 上展开 → 必上展开 (medium qualifies)."""
    trace = await _run_one(
        _exp(recognition="medium", fit="adjacent", disambiguator_type="mis_classification")
    )
    assert trace["pass_a_tier"] == "上展开"
    assert trace["pass_b_tier"] == "必上展开"


@pytest.mark.asyncio
async def test_pass_b_mis_classification_low_recognition_capped_at_above():
    """mis_classification on (low, adjacent) = backup行 → 单bullet, not 必上展开.

    R-8 ceiling: low recognition can't reach 必上展开 even with mis_classification.
    """
    trace = await _run_one(
        _exp(recognition="low", fit="adjacent", disambiguator_type="mis_classification")
    )
    assert trace["pass_a_tier"] == "backup行"
    assert trace["pass_b_tier"] == "单bullet"


@pytest.mark.asyncio
async def test_pass_b_pure_recognition_caps_at_dan_bullet():
    """pure_recognition on (low, core) = 单bullet → still 单bullet (ceiling cap).

    pure_recognition cannot promote into 上展开/必上展开 — ceiling = 单bullet.
    """
    trace = await _run_one(
        _exp(recognition="low", fit="core", disambiguator_type="pure_recognition")
    )
    assert trace["pass_a_tier"] == "单bullet"
    assert trace["pass_b_tier"] == "单bullet"
    assert trace["pass_b_lift"] == "pure_recognition"


@pytest.mark.asyncio
async def test_pass_b_pure_recognition_lifts_backup_to_dan_bullet():
    """pure_recognition on (low, adjacent) = backup行 → 单bullet (one-tier lift, capped)."""
    trace = await _run_one(
        _exp(recognition="low", fit="adjacent", disambiguator_type="pure_recognition")
    )
    assert trace["pass_a_tier"] == "backup行"
    assert trace["pass_b_tier"] == "单bullet"


@pytest.mark.asyncio
async def test_pass_b_no_disambiguator_no_change():
    """Disambiguator None → pass_b_lift='none', pass_b_tier == pass_a_tier."""
    trace = await _run_one(_exp(recognition="medium", fit="adjacent"))
    assert trace["pass_b_lift"] == "none"
    assert trace["pass_b_tier"] == trace["pass_a_tier"]


@pytest.mark.asyncio
async def test_pass_b_disambiguator_does_not_resurrect_cut():
    """Even mis_classification can't lift 砍 (fit was weak/missing — content failed)."""
    trace = await _run_one(
        _exp(recognition="high", fit="weak", disambiguator_type="mis_classification")
    )
    assert trace["pass_a_tier"] == "砍"
    assert trace["pass_b_tier"] == "砍"


# --------------------------------------------------------------------------- #
# Pass C JD AI pressure                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ai_keywords,exp_ai,expected_levels,expected_label",
    [
        # JD heavy (3+ AI hits)
        (["AIGC", "LLM", "RAG", "Prompt"], "none", 2, "none_minus_2"),
        (["AIGC", "LLM", "RAG", "Prompt"], "weak", 1, "weak_minus_1"),
        (["AIGC", "LLM", "RAG", "Prompt"], "moderate", 0, "none"),
        (["AIGC", "LLM", "RAG", "Prompt"], "strong", 0, "none"),
        # JD weak (1-2 AI hits)
        (["AIGC"], "none", 1, "weak_minus_1"),
        (["AIGC"], "weak", 0, "none"),
        (["AIGC"], "moderate", 0, "none"),
        (["AIGC"], "strong", 0, "none"),
        # JD none (0 AI hits)
        ([], "none", 0, "none"),
        ([], "weak", 0, "none"),
        ([], "moderate", 0, "none"),
        ([], "strong", 0, "none"),
    ],
)
async def test_pass_c_demotion_grid(
    ai_keywords: list[str], exp_ai: str, expected_levels: int, expected_label: str
):
    """4×4 JD pressure × experience AI fluency demotion grid."""
    cm = _competency_with_ai_keywords(*ai_keywords)
    trace = await _run_one(
        _exp(recognition="high", fit="core", ai_fluency=exp_ai),
        competency_model=cm,
    )
    # base = 必上展开; demote N levels
    expected_tiers = ("必上展开", "上展开", "单bullet", "backup行", "砍")
    assert trace["pass_b_tier"] == "必上展开"
    assert trace["pass_c_tier"] == expected_tiers[expected_levels]
    assert trace["pass_c_ai_pressure"] == expected_label


@pytest.mark.asyncio
async def test_pass_c_demotion_floors_at_cut():
    """Demoting past 砍 stays at 砍."""
    cm = _competency_with_ai_keywords("AIGC", "LLM", "RAG", "Prompt")
    # base = backup行 (low × adjacent); heavy × none demotes 2 → 砍 (floored)
    trace = await _run_one(
        _exp(recognition="low", fit="adjacent", ai_fluency="none"),
        competency_model=cm,
    )
    assert trace["pass_b_tier"] == "backup行"
    assert trace["pass_c_tier"] == "砍"  # 2 levels down from backup行 = 砍 (floored)
    assert trace["pass_c_ai_pressure"] == "none_minus_2"


@pytest.mark.asyncio
async def test_pass_c_already_cut_stays_cut():
    """An already-砍 experience can't be demoted further."""
    cm = _competency_with_ai_keywords("AIGC", "LLM", "RAG")
    trace = await _run_one(
        _exp(recognition="high", fit="missing", ai_fluency="none"),
        competency_model=cm,
    )
    assert trace["pass_b_tier"] == "砍"
    assert trace["pass_c_tier"] == "砍"


# --------------------------------------------------------------------------- #
# Final category mapping                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recognition,fit,expected_cat",
    [
        ("high", "core", 1),       # → 必上展开 → Cat 1
        ("high", "adjacent", 2),   # → 上展开 → Cat 2
        ("low", "core", 3),        # → 单bullet → Cat 3
        ("high", "missing", 4),    # → 砍 → Cat 4
    ],
)
async def test_final_category_mapping(recognition: str, fit: str, expected_cat: int):
    """Each pass_c_tier maps to its canonical final_category."""
    trace = await _run_one(_exp(recognition=recognition, fit=fit))
    assert trace["final_category"] == expected_cat


# --------------------------------------------------------------------------- #
# End-to-end on real index.json                                                #
# --------------------------------------------------------------------------- #


@pytest.fixture
def real_index_experiences(repo_root: Path) -> list[dict]:
    data = json.loads((repo_root / "assets/experience-bank/index.json").read_text())
    return data["experiences"]


@pytest.mark.asyncio
async def test_real_index_returns_one_trace_per_experience(real_index_experiences: list[dict]):
    """Six experiences in (default), six trace entries out."""
    cm = _competency_with_ai_keywords("AIGC", "LLM", "RAG", "Prompt", "Agent")  # heavy AI JD
    traces = await run_three_pass(
        experiences=real_index_experiences,
        jd_text="AIGC PM JD",
        primary_lens="C_product_ops",
        target_industry="internet_strategic",
        competency_model=cm,
    )
    assert len(traces) == len(real_index_experiences)
    # Schema enums obeyed across all entries
    valid_tiers = {"必上展开", "上展开", "单bullet", "backup行", "砍"}
    valid_lifts = {"mis_classification", "pure_recognition", "none"}
    valid_pressure = {"none", "weak_minus_1", "none_minus_2"}
    valid_cats = {1, 2, 3, 4}
    for t in traces:
        assert t["pass_a_tier"] in valid_tiers
        assert t["pass_b_tier"] in valid_tiers
        assert t["pass_b_lift"] in valid_lifts
        assert t["pass_c_tier"] in valid_tiers
        assert t["pass_c_ai_pressure"] in valid_pressure
        assert t["final_category"] in valid_cats


@pytest.mark.asyncio
async def test_real_index_heavy_ai_demotes_low_ai_experiences(real_index_experiences: list[dict]):
    """Heavy AI JD should produce >=1 demotion event among the 6 experiences.

    default has ai_digital_fluency=weak on Kearney/Ipsos/Desay/Mercer/SDIC
    (the traditional consulting roles), so a heavy AI JD must surface
    at least one weak_minus_1 or none_minus_2 entry. Asserting "any
    demotion present" rather than a specific id keeps this resilient
    to data churn.
    """
    cm = _competency_with_ai_keywords("AIGC", "LLM", "RAG", "Prompt", "Agent")
    traces = await run_three_pass(
        experiences=real_index_experiences,
        jd_text="AIGC PM JD",
        primary_lens="C_product_ops",
        target_industry="internet_strategic",
        competency_model=cm,
    )
    pressures = [t["pass_c_ai_pressure"] for t in traces]
    assert any(p in ("weak_minus_1", "none_minus_2") for p in pressures), (
        f"Expected at least one demotion under heavy AI JD; got pressures={pressures}"
    )


# --------------------------------------------------------------------------- #
# Edge cases                                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_empty_experiences_returns_empty_trace():
    traces = await run_three_pass(
        experiences=[],
        jd_text="(any)",
        primary_lens="C_product_ops",
        target_industry="internet_strategic",
        competency_model=None,
    )
    assert traces == []


@pytest.mark.asyncio
async def test_competency_model_none_no_demotion():
    """competency_model=None → JD pressure 'none' → no Pass C demotion at all."""
    trace = await _run_one(
        _exp(recognition="high", fit="core", ai_fluency="none"),
        competency_model=None,
    )
    assert trace["pass_c_tier"] == trace["pass_b_tier"]
    assert trace["pass_c_ai_pressure"] == "none"


@pytest.mark.asyncio
async def test_missing_target_industry_falls_back_to_low():
    """Experience with no recognition cell for target_industry → low fallback."""
    exp = {
        "id": "X",
        # explicitly no entry for our target_industry
        "recognition_per_industry": {},
        "vertical_fit_per_lens": {"C_product_ops": {"score": "core"}},
    }
    trace = await _run_one(exp)
    # low × core → 单bullet → Cat 3
    assert trace["pass_a_tier"] == "单bullet"
    assert trace["final_category"] == 3


@pytest.mark.asyncio
async def test_empty_disambiguator_map_treated_as_no_lift():
    """Empty/null disambiguator_per_industry → pass_b_lift='none'."""
    exp = _exp(recognition="medium", fit="adjacent")
    exp["disambiguator_per_industry"] = None
    trace = await _run_one(exp)
    assert trace["pass_b_lift"] == "none"


@pytest.mark.asyncio
async def test_disambiguator_for_other_industry_ignored():
    """Disambiguator only applies if it's set on the target_industry cell."""
    exp = {
        "id": "X",
        "recognition_per_industry": {"internet_strategic": {"score": "low"}},
        "vertical_fit_per_lens": {"C_product_ops": {"score": "core"}},
        "disambiguator_per_industry": {
            "consulting": {"type": "mis_classification", "text": "(test)", "rationale": "..."}
        },
    }
    trace = await _run_one(exp)
    assert trace["pass_b_lift"] == "none"
    assert trace["pass_b_tier"] == trace["pass_a_tier"]
