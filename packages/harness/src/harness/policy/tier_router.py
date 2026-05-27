"""Tier router — maps run scores to a tailoring tier (1, 2, or 3).

Per ARCHITECTURE.md §7a:

    Tier 1: jd_total >= 90 AND resume_match >= 85   → light tailoring (default ~85%)
    Tier 2: jd_total 70-89 OR resume_match 70-84    → medium / review draft
    Tier 3: jd_total < 70 OR resume_match < 70 OR hard filter blocked

Pure function, deterministic, no LLM, no async. The MVP caller only
provides `resume_match_score` (from `verdict_scorer.score_run`); when
`jd_total_score is None` we route on the resume_match thresholds alone:
`>= 85 → 1`, `70-84 → 2`, `< 70 → 3`.

`hard_filter_blocked` (visa rules etc.) is exposed as a parameter but no
caller currently sets it; it short-circuits to Tier 3 when true.
"""
from __future__ import annotations


_RESUME_TIER1_THRESHOLD = 85.0
_RESUME_TIER2_THRESHOLD = 70.0
_JD_TIER1_THRESHOLD = 90.0
_JD_TIER2_THRESHOLD = 70.0


def assign_tier(
    resume_match_score: float,
    jd_total_score: float | None = None,
    hard_filter_blocked: bool = False,
) -> int:
    """Return tailoring tier (1, 2, or 3) for the given scores.

    See ARCHITECTURE.md §7a thresholds. When `jd_total_score is None`
    (MVP — JD-side scoring not yet computed end-to-end), route on
    `resume_match_score` alone.
    """
    if hard_filter_blocked:
        return 3

    if jd_total_score is None:
        if resume_match_score >= _RESUME_TIER1_THRESHOLD:
            return 1
        if resume_match_score >= _RESUME_TIER2_THRESHOLD:
            return 2
        return 3

    # Both signals present — strict §7a routing.
    if (
        jd_total_score >= _JD_TIER1_THRESHOLD
        and resume_match_score >= _RESUME_TIER1_THRESHOLD
    ):
        return 1
    if (
        _RESUME_TIER2_THRESHOLD <= resume_match_score < _RESUME_TIER1_THRESHOLD
        or _JD_TIER2_THRESHOLD <= jd_total_score < _JD_TIER1_THRESHOLD
    ):
        return 2
    return 3
