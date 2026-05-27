"""Compute resume_match_score + confidence_tier for a Tier 1 run.

Per ARCHITECTURE.md §7b. Two scoring paths:

1. **Closed-form approximation** (`method == "tier1_approximation"`) — pre-D.1
   default; averages `vertical_fit_per_lens[primary_lens]` cells through
   Cat→points. Used when no `experience_selection_trace` is available.

2. **Pass C trace consumer** (`method == "pass_c_full"`) — Wave 4 D.1 path;
   reads `final_category` from each ExperienceTrace entry, applies §7b
   weighting:
       Cat 1 = 100, Cat 2 = 75, Cat 3 = 40, Cat 4 = 0.

`confidence_tier` follows ARCHITECTURE.md §7a thresholds + degradation
+ lens routing confidence penalties (unchanged across both paths).
"""
from __future__ import annotations

from typing import Literal

from harness.tier1.cell_shape import extract_cell_score


ConfidenceTier = Literal["ready_to_go", "review_recommended", "needs_deep_rewrite"]


# Vertical-fit values map to Cat-weighted points (per ARCHITECTURE.md §7b).
# core   → Cat 1 = 100
# adjacent→ Cat 2 = 75
# weak    → Cat 3 = 40
# missing → Cat 4 = 0
_FIT_TO_POINTS: dict[str, int] = {
    "core": 100,
    "adjacent": 75,
    "weak": 40,
    "missing": 0,
}

# Penalty weights (subtracted from raw score)
_DEGRADATION_PENALTY = 5  # per degradation_event
_LOW_CONFIDENCE_PENALTY = 5  # if lens routing confidence < 0.6

# §7b category → score map (Pass C trace consumer path).
_CATEGORY_TO_POINTS: dict[int, int] = {1: 100, 2: 75, 3: 40, 4: 0}


def compute_score_from_trace(trace: list[dict]) -> float:
    """Average §7b category points across an experience_selection_trace.

    Each trace entry must have a `final_category` ∈ {1,2,3,4}. Returns 0.0
    on empty trace (caller treats that as needs_deep_rewrite).
    """
    if not trace:
        return 0.0
    points = [
        _CATEGORY_TO_POINTS.get(int(entry.get("final_category", 4)), 0)
        for entry in trace
    ]
    return sum(points) / len(points)


def compute_resume_match_score(
    experiences: list[dict],
    primary_lens: str,
) -> float:
    """Average vertical_fit_per_lens for the routing's primary lens.

    Returns 0..100. Returns 0 when there are no experiences (caller should
    treat that as needs_deep_rewrite).

    `experiences` is the experiences-index entry list; each dict may have
    `vertical_fit_per_lens: {lens_name: "core"|"adjacent"|"weak"|"missing"}`.
    Missing entries score as Cat 4.
    """
    if not experiences or not primary_lens:
        return 0.0
    points = []
    for exp in experiences:
        fit_map = exp.get("vertical_fit_per_lens") or {}
        value = extract_cell_score(fit_map.get(primary_lens))
        points.append(_FIT_TO_POINTS.get(value or "missing", 0))
    return sum(points) / len(points)


def derive_confidence_tier(
    resume_match_score: float,
    degradation_count: int,
    lens_routing_confidence: float | None,
) -> ConfidenceTier:
    """Map score + signal penalties to a 3-bucket UI tier.

    Per ARCHITECTURE.md §7a thresholds, with degradation + low-confidence
    overrides.
    """
    # Apply penalties
    adjusted = resume_match_score
    adjusted -= _DEGRADATION_PENALTY * max(0, degradation_count)
    if lens_routing_confidence is not None and lens_routing_confidence < 0.6:
        adjusted -= _LOW_CONFIDENCE_PENALTY

    # Hard overrides — cannot escape needs_deep_rewrite from these signals
    if degradation_count >= 2:
        return "needs_deep_rewrite"
    if lens_routing_confidence is not None and lens_routing_confidence < 0.5:
        return "needs_deep_rewrite"

    if adjusted >= 85:
        return "ready_to_go"
    if adjusted >= 70:
        return "review_recommended"
    return "needs_deep_rewrite"


def score_run(
    experiences: list[dict],
    primary_lens: str,
    degradation_count: int,
    lens_routing_confidence: float | None,
    experience_selection_trace: list[dict] | None = None,
) -> dict:
    """One-shot: compute both raw score and tier label.

    When `experience_selection_trace` is non-empty (Wave 4 D.1 path), the
    score is derived from each trace entry's `final_category` via the §7b
    category-points formula and `method = "pass_c_full"`. Otherwise we
    fall back to the closed-form vertical-fit average and tag the result
    `method = "tier1_approximation"`. The trace path is preferred because
    it picks up Pass B disambiguator lifts and Pass C JD AI demotions
    that the closed-form average can't see.

    Returns the dict embedded in harness-tailor-output's `match_scores`
    field (see harness-tailor-output.schema.json):
        {
          "resume_match_score": 82.5,
          "confidence_tier": "review_recommended",
          "method": "pass_c_full" | "tier1_approximation",
        }
    """
    if experience_selection_trace:
        score = compute_score_from_trace(experience_selection_trace)
        method = "pass_c_full"
    else:
        score = compute_resume_match_score(experiences, primary_lens)
        method = "tier1_approximation"
    tier = derive_confidence_tier(score, degradation_count, lens_routing_confidence)
    return {
        "resume_match_score": round(score, 1),
        "confidence_tier": tier,
        "method": method,
        "degradation_count": degradation_count,
        "lens_routing_confidence": lens_routing_confidence,
    }
