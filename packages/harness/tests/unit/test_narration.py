"""Unit tests for repl/narration.py."""
from datetime import datetime, timezone, timedelta

from harness.repl.narration import generate_narration, humanize_age, lens_label_zh


_NOW = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)


def _iso(delta_seconds: float) -> str:
    return (_NOW - timedelta(seconds=delta_seconds)).isoformat()


def test_humanize_just_now():
    assert humanize_age(_iso(30), now=_NOW) == "just now"


def test_humanize_minutes():
    assert humanize_age(_iso(180), now=_NOW) == "3 min ago"


def test_humanize_one_hour():
    assert humanize_age(_iso(3700), now=_NOW) == "1 hour ago"


def test_humanize_multi_hours():
    assert humanize_age(_iso(7400), now=_NOW) == "2 hours ago"


def test_humanize_yesterday():
    assert humanize_age(_iso(86400 + 60), now=_NOW) == "yesterday"


def test_lens_label_known():
    assert lens_label_zh("C_product_ops") == "C 产品运营"


def test_lens_label_unknown():
    assert lens_label_zh("Z_unknown") == ""
    assert lens_label_zh(None) == ""


def test_narration_clean_run():
    state = {
        "created_at": _iso(120),
        "lens_routing": {"primary_lens": "C_product_ops"},
        "degradation_events": [],
    }
    text = generate_narration(state, now=_NOW)
    assert "C 产品运营 lens" in text
    assert "no issues" in text


def test_narration_one_degradation():
    state = {
        "created_at": _iso(120),
        "lens_routing": {"primary_lens": "B_data_analytics"},
        "degradation_events": [{"stage": "action", "reason": "x", "fallback_taken": "y"}],
    }
    text = generate_narration(state, now=_NOW)
    assert "B 数据分析 lens" in text
    assert "action stage degraded" in text


def test_narration_multi_degradations():
    state = {
        "created_at": _iso(120),
        "lens_routing": {"primary_lens": "A_strategy_research"},
        "degradation_events": [{"stage": "x"}, {"stage": "y"}, {"stage": "z"}],
    }
    text = generate_narration(state, now=_NOW)
    assert "3 stages degraded" in text


def test_narration_no_lens():
    state = {"created_at": _iso(120), "degradation_events": []}
    text = generate_narration(state, now=_NOW)
    assert "lens" not in text
    assert "no issues" in text
