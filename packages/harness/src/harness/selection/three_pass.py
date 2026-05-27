"""3-pass per-experience selection (Wave 4 D.1).

Implements ARCHITECTURE.md §7b + resume-rewrite-engine SKILL.md hard rule R-8:
the canonical Pass A (base score) → Pass B (disambiguator booster) → Pass C
(JD AI hard 筛) selector that decides Cat 1 / 2 / 3 / 4 for every entry in
`assets/experience-bank/index.json`.

Output populates `state.experience_selection_trace` (schema field declared in
`contracts/schemas/harness-tailor-output.schema.json` lines 33-49). The
verdict_scorer reads `final_category` from each trace entry to compute
`resume_match_score` via the §7b formula.

Deterministic; no LLM calls. Async signature is preserved for forward-compat
with future LLM-driven Pass C variations (e.g. Tier 3 重跑 Step 4).
"""
from __future__ import annotations

from typing import Literal, TypedDict

from harness.tier1.cell_shape import extract_cell_score


# Tier ordering — lower index = higher tier. Used by demote/lift helpers.
_TIER_ORDER: tuple[str, ...] = ("必上展开", "上展开", "单bullet", "backup行", "砍")


# Pass A 5×4 grid — recognition × fit → base tier.
# The grid follows ARCHITECTURE.md §7b: high|medium recognition fans out by fit;
# low (or null fallback) lands one row down; weak/missing fit always cuts.
def _pass_a_grid(recognition: str, fit: str) -> str:
    if fit in ("weak", "missing"):
        return "砍"
    if recognition in ("high", "medium"):
        if fit == "core":
            return "必上展开"
        if fit == "adjacent":
            return "上展开"
    # recognition low/null falls into the conservative row
    if fit == "core":
        return "单bullet"
    if fit == "adjacent":
        return "backup行"
    return "砍"


# JD AI keyword detection (CN + EN). Hits counted across Section D tier_1 + tier_2.
_AI_KEYWORDS: tuple[str, ...] = (
    "AIGC",
    "AI Agent",
    "RAG",
    "Prompt",
    "LLM",
    "生成式 AI",
    "Agent",
    "提示词",
)


# Demotion table per Pass C: (jd_pressure, experience_ai_fluency) → levels demoted.
# Per ARCHITECTURE.md §7b — only the 3 demotion cases are listed; all other
# (jd_pressure, ai_fluency) pairs default to 0 (no change) via .get(..., 0).
_PASS_C_DEMOTION: dict[tuple[str, str], int] = {
    ("heavy", "none"): 2,
    ("heavy", "weak"): 1,
    ("weak", "none"): 1,
}


# Maps demotion levels to the schema's `pass_c_ai_pressure` enum.
_AI_PRESSURE_LABEL: dict[int, str] = {
    0: "none",
    1: "weak_minus_1",
    2: "none_minus_2",
}


class ExperienceTrace(TypedDict):
    """Per-experience selection trace entry.

    Matches `harness-tailor-output.schema.json` `experience_selection_trace`
    items exactly (lines 33-49). All literal values come from the schema's
    enum fields.
    """
    experience_id: str
    pass_a_tier: Literal["必上展开", "上展开", "单bullet", "backup行", "砍"]
    pass_b_tier: Literal["必上展开", "上展开", "单bullet", "backup行", "砍"]
    pass_b_lift: Literal["mis_classification", "pure_recognition", "none"]
    pass_c_tier: Literal["必上展开", "上展开", "单bullet", "backup行", "砍"]
    pass_c_ai_pressure: Literal["none", "weak_minus_1", "none_minus_2"]
    final_category: Literal[1, 2, 3, 4]


def _disambiguator_type(cell: object) -> str | None:
    """Return the disambiguator type from a `disambiguator_per_industry[X]` cell.

    Cell shape per recognition-rubric.md §7 / index.json examples:
        {"type": "mis_classification" | "pure_recognition", "text": ..., "rationale": ...}
    Returns None when cell is null / missing / malformed.
    """
    if not isinstance(cell, dict):
        return None
    t = cell.get("type")
    if t in ("mis_classification", "pure_recognition"):
        return t
    return None


def _lift_tier(base_tier: str, base_recognition: str, lift_type: str) -> str:
    """Apply Pass B disambiguator lift with R-8 ceiling enforcement.

    Hard rule R-8: disambiguator may NOT promote any experience to "必上展开"
    (that tier requires base_recognition >= medium).
    `pure_recognition` further capped at "单bullet" (cannot reach 必上展开
    even if base_recognition were high — though by construction
    pure_recognition is only used when recognition is low/null, so this is
    a defensive cap).
    """
    if base_tier == "砍":
        # Disambiguator can't resurrect a 砍 — fit was weak/missing, R-7
        # parenthetical wouldn't help anyway.
        return base_tier

    idx = _TIER_ORDER.index(base_tier)
    new_idx = max(0, idx - 1)  # one tier up
    new_tier = _TIER_ORDER[new_idx]

    if lift_type == "pure_recognition":
        # pure_recognition ceiling = 单bullet
        ceiling_idx = _TIER_ORDER.index("单bullet")
        new_idx = max(new_idx, ceiling_idx)
        new_tier = _TIER_ORDER[new_idx]
    elif lift_type == "mis_classification":
        # Cannot promote to 必上展开 unless base_recognition >= medium
        if new_tier == "必上展开" and base_recognition not in ("high", "medium"):
            new_tier = "上展开"

    return new_tier


def _demote_tier(tier: str, levels: int) -> str:
    """Move tier `levels` notches down the ordering. Floor = 砍."""
    if levels <= 0:
        return tier
    idx = _TIER_ORDER.index(tier)
    new_idx = min(len(_TIER_ORDER) - 1, idx + levels)
    return _TIER_ORDER[new_idx]


def _jd_ai_pressure(competency_model: dict | None) -> str:
    """Count AI keyword hits across Section D tier_1 + tier_2 → none/weak/heavy.

    Returns "none" when competency_model is None (no Step B output) — Pass C
    never demotes in that case.
    """
    if not isinstance(competency_model, dict):
        return "none"
    section_d = competency_model.get("section_d_keyword_architecture")
    if not isinstance(section_d, dict):
        return "none"

    candidate_terms: list[str] = []
    for key in ("tier_1_core_role", "tier_2_capability"):
        items = section_d.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str):
                candidate_terms.append(item)

    hits = 0
    for term in candidate_terms:
        lowered = term.lower()
        for kw in _AI_KEYWORDS:
            if kw.lower() in lowered:
                hits += 1
                break  # one term contributes at most one hit

    if hits >= 3:
        return "heavy"
    if hits >= 1:
        return "weak"
    return "none"


def _final_category(pass_c_tier: str) -> int:
    if pass_c_tier == "必上展开":
        return 1
    if pass_c_tier == "上展开":
        return 2
    if pass_c_tier in ("单bullet", "backup行"):
        return 3
    return 4


def _select_one(
    experience: dict,
    primary_lens: str,
    target_industry: str,
    jd_ai_pressure: str,
) -> ExperienceTrace:
    """Run Pass A → B → C for a single experience entry."""
    # ----- Pass A -----
    rec_cell = (experience.get("recognition_per_industry") or {}).get(target_industry)
    fit_cell = (experience.get("vertical_fit_per_lens") or {}).get(primary_lens)
    rec_score = extract_cell_score(rec_cell) or "low"  # null → conservative low
    fit_score = extract_cell_score(fit_cell) or "missing"  # null → conservative missing
    pass_a_tier = _pass_a_grid(rec_score, fit_score)

    # ----- Pass B -----
    disambig_map = experience.get("disambiguator_per_industry") or {}
    disambig_cell = disambig_map.get(target_industry) if isinstance(disambig_map, dict) else None
    lift_type = _disambiguator_type(disambig_cell)
    if lift_type is None:
        pass_b_tier = pass_a_tier
        pass_b_lift = "none"
    else:
        pass_b_tier = _lift_tier(pass_a_tier, rec_score, lift_type)
        pass_b_lift = lift_type

    # ----- Pass C -----
    ai_fluency = extract_cell_score(experience.get("ai_digital_fluency")) or "none"
    demote_levels = _PASS_C_DEMOTION.get((jd_ai_pressure, ai_fluency), 0)
    pass_c_tier = _demote_tier(pass_b_tier, demote_levels)
    pass_c_ai_pressure = _AI_PRESSURE_LABEL[demote_levels]

    return ExperienceTrace(
        experience_id=experience.get("id", ""),
        pass_a_tier=pass_a_tier,  # type: ignore[typeddict-item]
        pass_b_tier=pass_b_tier,  # type: ignore[typeddict-item]
        pass_b_lift=pass_b_lift,  # type: ignore[typeddict-item]
        pass_c_tier=pass_c_tier,  # type: ignore[typeddict-item]
        pass_c_ai_pressure=pass_c_ai_pressure,  # type: ignore[typeddict-item]
        final_category=_final_category(pass_c_tier),  # type: ignore[typeddict-item]
    )


async def run_three_pass(
    experiences: list[dict],
    jd_text: str,
    primary_lens: str,
    target_industry: str,
    competency_model: dict | None,
) -> list[ExperienceTrace]:
    """Run Pass A → Pass B → Pass C for every experience.

    Returns one `ExperienceTrace` per input entry, in the same order. Each
    trace's `final_category` feeds verdict_scorer's §7b formula.

    `jd_text` is currently unused (Pass C derives AI pressure from the
    competency_model's Section D, which is the canonical structured form
    of the JD); kept in the signature so a future Pass C variant can scan
    raw JD text for keywords missing from Section D without breaking
    callers.
    """
    del jd_text  # reserved for future variants — see docstring
    if not experiences:
        return []

    jd_ai_pressure = _jd_ai_pressure(competency_model)

    return [
        _select_one(exp, primary_lens, target_industry, jd_ai_pressure)
        for exp in experiences
    ]
