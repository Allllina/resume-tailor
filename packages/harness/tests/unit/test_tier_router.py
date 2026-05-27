"""Tests for harness.policy.tier_router (Wave 4 D.3).

Covers ARCHITECTURE.md §7a tier-routing thresholds:
  Tier 1: jd_total >= 90 AND resume_match >= 85
  Tier 2: jd_total 70-89 OR resume_match 70-84
  Tier 3: anything else / hard_filter_blocked

MVP fallback (jd_total_score is None): route on resume_match alone.
"""
import pytest

from harness.policy import assign_tier


# ----- MVP path: jd_total_score is None, route on resume_match -----


def test_resume_match_85_no_jd_score_is_tier1():
    """Boundary inclusive at 85 → Tier 1."""
    assert assign_tier(resume_match_score=85.0) == 1


def test_resume_match_high_no_jd_score_is_tier1():
    assert assign_tier(resume_match_score=92.5) == 1


def test_resume_match_84_99_no_jd_score_is_tier2():
    """Just below the Tier 1 cut → Tier 2."""
    assert assign_tier(resume_match_score=84.99) == 2


def test_resume_match_70_no_jd_score_is_tier2():
    """Boundary inclusive at 70 → Tier 2."""
    assert assign_tier(resume_match_score=70.0) == 2


def test_resume_match_69_99_no_jd_score_is_tier3():
    """Just below the Tier 2 cut → Tier 3."""
    assert assign_tier(resume_match_score=69.99) == 3


def test_resume_match_50_no_jd_score_is_tier3():
    assert assign_tier(resume_match_score=50.0) == 3


def test_resume_match_zero_no_jd_score_is_tier3():
    assert assign_tier(resume_match_score=0.0) == 3


def test_resume_match_100_no_jd_score_is_tier1():
    assert assign_tier(resume_match_score=100.0) == 1


# ----- Strict §7a path: both signals present -----


def test_high_resume_and_jd_is_tier1():
    """resume=100, jd=95 → both above Tier 1 cuts → Tier 1."""
    assert assign_tier(resume_match_score=100.0, jd_total_score=95.0) == 1


def test_high_resume_low_jd_is_tier2():
    """jd dragged down (89) → Tier 2 even if resume is perfect."""
    assert assign_tier(resume_match_score=100.0, jd_total_score=89.0) == 2


def test_high_jd_low_resume_is_tier3():
    """resume too low (50) and not in the 70-84 band → Tier 3."""
    assert assign_tier(resume_match_score=50.0, jd_total_score=95.0) == 3


def test_resume_and_jd_both_in_tier2_band():
    """resume 75, jd 80 → both in Tier 2 band → Tier 2."""
    assert assign_tier(resume_match_score=75.0, jd_total_score=80.0) == 2


# ----- hard_filter_blocked short-circuit -----


def test_hard_filter_blocked_overrides_tier1_scores():
    assert (
        assign_tier(
            resume_match_score=100.0,
            jd_total_score=95.0,
            hard_filter_blocked=True,
        )
        == 3
    )


def test_hard_filter_blocked_overrides_no_jd_score():
    assert assign_tier(resume_match_score=90.0, hard_filter_blocked=True) == 3
