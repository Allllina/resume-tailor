"""Unit tests for tier1/verdict_scorer.py."""
import pytest

from harness.tier1.verdict_scorer import (
    compute_resume_match_score,
    derive_confidence_tier,
    score_run,
)


# ============ compute_resume_match_score ============


def _exp(fit_value: str | None) -> dict:
    """Build an experience dict with a single lens fit value."""
    return {
        "vertical_fit_per_lens": (
            {"C_product_ops": fit_value} if fit_value is not None else {}
        )
    }


def test_score_all_core_returns_100():
    exps = [_exp("core") for _ in range(3)]
    assert compute_resume_match_score(exps, "C_product_ops") == 100.0


def test_score_all_missing_returns_0():
    exps = [_exp("missing") for _ in range(3)]
    assert compute_resume_match_score(exps, "C_product_ops") == 0.0


def test_score_mixed():
    # core=100, adjacent=75, weak=40 → mean = 71.67
    exps = [_exp("core"), _exp("adjacent"), _exp("weak")]
    score = compute_resume_match_score(exps, "C_product_ops")
    assert 71 < score < 72


def test_score_handles_dict_cell_format_value_key():
    """auto_scorer (Wave 2.7) emits {value: ...} dict cells."""
    exps = [{"vertical_fit_per_lens": {"C_product_ops": {"value": "core"}}}]
    assert compute_resume_match_score(exps, "C_product_ops") == 100.0


def test_score_handles_dict_cell_format_score_key():
    """index.json v0.2.0 (hand-curated) uses {score, evidence_strength, rationale}."""
    exps = [{"vertical_fit_per_lens": {"C_product_ops": {
        "score": "adjacent",
        "evidence_strength": "direct",
        "rationale": "matches",
    }}}]
    assert compute_resume_match_score(exps, "C_product_ops") == 75.0


def test_score_missing_cell_is_cat4():
    """Experience with no entry for primary_lens → Cat 4 = 0 points."""
    exps = [_exp(None)]  # vertical_fit_per_lens={} so primary_lens missing
    assert compute_resume_match_score(exps, "C_product_ops") == 0.0


def test_score_empty_experiences_returns_zero():
    assert compute_resume_match_score([], "C_product_ops") == 0.0


def test_score_no_primary_lens_returns_zero():
    exps = [_exp("core")]
    assert compute_resume_match_score(exps, "") == 0.0


# ============ derive_confidence_tier ============


def test_tier_ready_to_go_clean():
    assert derive_confidence_tier(90, 0, 0.85) == "ready_to_go"


def test_tier_ready_to_go_at_boundary():
    assert derive_confidence_tier(85, 0, 0.7) == "ready_to_go"


def test_tier_review_recommended_70s():
    assert derive_confidence_tier(75, 0, 0.7) == "review_recommended"


def test_tier_review_recommended_when_high_score_with_degradation():
    """≥85 score but 1 degradation → drop to review_recommended (penalty -5 → 85)."""
    # 90 - 5*1 = 85 → still ready_to_go boundary; need 1+ deg drops below
    assert derive_confidence_tier(85, 1, 0.85) == "review_recommended"


def test_tier_needs_deep_rewrite_low_score():
    assert derive_confidence_tier(50, 0, 0.85) == "needs_deep_rewrite"


def test_tier_needs_deep_rewrite_two_degradations_overrides_high_score():
    """Hard override: 2+ degradations always needs_deep_rewrite even with score 100."""
    assert derive_confidence_tier(100, 2, 0.95) == "needs_deep_rewrite"


def test_tier_needs_deep_rewrite_low_lens_confidence_overrides():
    """Hard override: lens_routing_confidence < 0.5 → needs_deep_rewrite."""
    assert derive_confidence_tier(100, 0, 0.4) == "needs_deep_rewrite"


def test_tier_low_lens_confidence_penalty_applied():
    """confidence < 0.6 (but >= 0.5) → -5 penalty, may shift bucket."""
    # 90 - 5 = 85 → still ready_to_go
    assert derive_confidence_tier(90, 0, 0.55) == "ready_to_go"
    # 87 - 5 = 82 → review_recommended
    assert derive_confidence_tier(87, 0, 0.55) == "review_recommended"


# ============ score_run ============


def test_score_run_full_shape():
    exps = [_exp("core"), _exp("adjacent")]
    out = score_run(exps, "C_product_ops", 0, 0.85)
    assert out["confidence_tier"] in (
        "ready_to_go",
        "review_recommended",
        "needs_deep_rewrite",
    )
    assert isinstance(out["resume_match_score"], float)
    assert out["method"] == "tier1_approximation"
    assert out["degradation_count"] == 0
    assert out["lens_routing_confidence"] == 0.85


def test_score_run_jingwen_shaped_data():
    """Realistic case: 6 experiences, primary lens C_product_ops, mixed fits."""
    exps = [
        _exp("adjacent"),
        _exp("weak"),
        _exp("core"),
        _exp("adjacent"),
        _exp("missing"),
        _exp("core"),
    ]
    out = score_run(exps, "C_product_ops", 0, 0.85)
    # 75+40+100+75+0+100 / 6 = 65 → needs_deep_rewrite
    assert out["confidence_tier"] == "needs_deep_rewrite"
    assert 64 < out["resume_match_score"] < 66


# ============ Wave 4 D.1: experience_selection_trace consumption ============


def _trace_entry(experience_id: str, final_category: int) -> dict:
    """Build a minimal trace entry; only final_category drives §7b math."""
    return {
        "experience_id": experience_id,
        "pass_a_tier": "必上展开",
        "pass_b_tier": "必上展开",
        "pass_b_lift": "none",
        "pass_c_tier": "必上展开",
        "pass_c_ai_pressure": "none",
        "final_category": final_category,
    }


def test_score_run_consumes_trace_when_present():
    """Trace path overrides closed-form math, sets method='pass_c_full'.

    §7b formula: Cat 1=100, Cat 2=75, Cat 3=40, Cat 4=0.
    Mixed [1,2,3,4] → mean = 53.75.
    """
    trace = [
        _trace_entry("01", 1),
        _trace_entry("02", 2),
        _trace_entry("03", 3),
        _trace_entry("04", 4),
    ]
    # Pass nonsensical experiences/lens to prove the closed-form path is NOT used.
    out = score_run(
        experiences=[_exp("missing")] * 4,  # would score 0 via closed form
        primary_lens="C_product_ops",
        degradation_count=0,
        lens_routing_confidence=0.85,
        experience_selection_trace=trace,
    )
    assert out["method"] == "pass_c_full"
    assert out["resume_match_score"] == 53.8  # round(53.75, 1)
    # 53.8 < 70 → needs_deep_rewrite
    assert out["confidence_tier"] == "needs_deep_rewrite"


def test_score_run_falls_back_to_closed_form_when_trace_empty():
    """Empty trace → closed-form path, method='tier1_approximation'."""
    exps = [_exp("core"), _exp("adjacent")]
    out = score_run(
        experiences=exps,
        primary_lens="C_product_ops",
        degradation_count=0,
        lens_routing_confidence=0.85,
        experience_selection_trace=[],
    )
    assert out["method"] == "tier1_approximation"
    # core=100 + adjacent=75 → 87.5
    assert out["resume_match_score"] == 87.5


def test_score_run_falls_back_to_closed_form_when_trace_arg_missing():
    """Backwards-compat: callers that don't pass the new kwarg keep working."""
    exps = [_exp("core"), _exp("core")]
    out = score_run(exps, "C_product_ops", 0, 0.85)  # no trace kwarg
    assert out["method"] == "tier1_approximation"
    assert out["resume_match_score"] == 100.0
