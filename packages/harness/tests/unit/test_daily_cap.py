"""Test DailyCapManager — total + LinkedIn sub-cap atomic reservation."""
import pytest
from pathlib import Path
from harness.submit.daily_cap import DailyCapManager, CapExceededError


def test_allows_under_total_cap(tmp_path):
    mgr = DailyCapManager(tmp_path / "caps.db", total_cap=50, linkedin_subcap=15)
    for _ in range(10):
        mgr.check_and_reserve("workday")
    assert mgr.used_today() == 10
    assert mgr.remaining()["total"] == 40


def test_blocks_at_total_cap(tmp_path):
    mgr = DailyCapManager(tmp_path / "caps.db", total_cap=3, linkedin_subcap=2)
    mgr.check_and_reserve("workday")
    mgr.check_and_reserve("workday")
    mgr.check_and_reserve("workday")
    with pytest.raises(CapExceededError) as excinfo:
        mgr.check_and_reserve("workday")
    assert excinfo.value.scope == "daily total"
    assert excinfo.value.used == 3
    assert excinfo.value.cap == 3


def test_blocks_at_linkedin_subcap(tmp_path):
    mgr = DailyCapManager(tmp_path / "caps.db", total_cap=50, linkedin_subcap=2)
    mgr.check_and_reserve("linkedin")
    mgr.check_and_reserve("linkedin")
    with pytest.raises(CapExceededError) as excinfo:
        mgr.check_and_reserve("linkedin")
    assert excinfo.value.scope == "linkedin"


def test_linkedin_subcap_independent_of_other_channels(tmp_path):
    mgr = DailyCapManager(tmp_path / "caps.db", total_cap=50, linkedin_subcap=2)
    # Use up LinkedIn cap
    mgr.check_and_reserve("linkedin")
    mgr.check_and_reserve("linkedin")
    # But other channels still work
    for _ in range(3):
        mgr.check_and_reserve("workday")
    # And LinkedIn is still blocked
    with pytest.raises(CapExceededError):
        mgr.check_and_reserve("linkedin")


def test_persists_across_instances(tmp_path):
    db = tmp_path / "caps.db"
    mgr1 = DailyCapManager(db, total_cap=10, linkedin_subcap=5)
    mgr1.check_and_reserve("linkedin")
    mgr1.check_and_reserve("linkedin")
    mgr1.check_and_reserve("workday")

    # New instance reads same DB
    mgr2 = DailyCapManager(db, total_cap=10, linkedin_subcap=5)
    assert mgr2.used_today() == 3
    assert mgr2.used_today("linkedin") == 2
    assert mgr2.remaining() == {"total": 7, "linkedin": 3}


def test_remaining_clamped_to_zero(tmp_path):
    """If somehow over cap, remaining shows 0 not negative."""
    mgr = DailyCapManager(tmp_path / "caps.db", total_cap=2, linkedin_subcap=1)
    mgr.check_and_reserve("workday")
    mgr.check_and_reserve("workday")
    assert mgr.remaining()["total"] == 0
