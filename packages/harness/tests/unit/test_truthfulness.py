"""Unit tests for harness.rewrite.truthfulness (Wave 4 D.2a).

The truthfulness pre-check is a fast substring gate, NOT a semantic
verifier. Pass 3 (D.4) does paraphrase/LLM matching. These tests pin the
gate's lenient looseness rules — the engine relies on them when it
decides whether to raise UnsourcedClaimError.
"""
from __future__ import annotations

from harness.rewrite.truthfulness import normalize_text, verify_claims_in_raw


# --------------------------- normalize_text ---------------------------


def test_normalize_text_lowercases():
    assert normalize_text("Hello WORLD") == "hello world"


def test_normalize_text_strips_noise_punctuation():
    out = normalize_text("Built (LLM) tool, shipped — fast.")
    # commas / parens / em-dash / period removed
    assert "(" not in out and ")" not in out
    assert "," not in out
    assert "—" not in out
    assert "built" in out and "llm" in out and "shipped" in out


def test_normalize_text_collapses_whitespace():
    assert normalize_text("a   b\n\tc") == "a b c"


def test_normalize_text_keeps_percent_signs_and_digits():
    out = normalize_text("revenue lifted 5% YoY")
    assert "5%" in out


def test_normalize_text_handles_empty():
    assert normalize_text("") == ""


def test_normalize_text_preserves_cjk():
    out = normalize_text("我搭建了Prompt 管线")
    assert "我搭建了" in out
    assert "prompt" in out


# --------------------------- verify_claims_in_raw — substring match ---------------------------


def test_substring_match_case_insensitive():
    claims = ["Built LLM tool"]
    raw = "Background: built llm tool in 2 months and shipped."
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == ["Built LLM tool"]
    assert unsourced == []


def test_substring_match_whitespace_normalized():
    claims = ["built  LLM\n tool"]
    raw = "background: built llm tool in 2 months."
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == claims
    assert unsourced == []


def test_substring_match_strips_punctuation():
    claims = ["built (LLM) tool"]
    raw = "we built llm tool"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == claims
    assert unsourced == []


def test_unsourced_when_claim_not_in_raw():
    claims = ["fabricated 99% revenue lift"]
    raw = "shipped a small llm prototype"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == []
    assert unsourced == claims


# --------------------------- percentage looseness ---------------------------


def test_percent_lenient_5pct_matches_5_percent_in_raw():
    """`claim = '5%'` verifies against raw containing `5 percent`."""
    claims = ["lift of 5% YoY"]
    raw = "experiment showed lift of 5 percent YoY"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == claims
    assert unsourced == []


def test_percent_lenient_5_percent_matches_5pct_in_raw():
    """Reverse direction: `5 percent` claim matches `5%` raw."""
    claims = ["lift of 5 percent YoY"]
    raw = "experiment showed lift of 5% YoY"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == claims
    assert unsourced == []


def test_percent_lenient_baifen_dian_matches_pct():
    """`5 个百分点` claim matches `5%` raw when surrounding context is shared.

    The substring gate only canonicalizes the percentage token; it does
    NOT do paraphrase matching on surrounding verbs. So claim and raw
    must share enough non-percent text to align as a substring.
    """
    claims = ["ROI 提升5个百分点"]
    raw = "团队 ROI 提升 5%"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == claims
    assert unsourced == []


# --------------------------- non-percent number strictness ---------------------------


def test_specific_number_not_matched_loosely():
    """A `50M` claim does NOT verify against `100M` — number strictness."""
    claims = ["revenue 50M"]
    raw = "revenue 100M"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == []
    assert unsourced == claims


# --------------------------- edge cases ---------------------------


def test_empty_claims_yields_empty_lists():
    verified, unsourced = verify_claims_in_raw([], "some raw text")
    assert verified == []
    assert unsourced == []


def test_empty_raw_text_marks_all_unsourced():
    claims = ["claim 1", "claim 2"]
    verified, unsourced = verify_claims_in_raw(claims, "")
    assert verified == []
    assert unsourced == ["claim 1", "claim 2"]


def test_blank_claim_skipped_not_returned_as_verified():
    """Whitespace-only claims are dropped, not returned in verified."""
    claims = ["", "   ", "valid claim"]
    raw = "this is the valid claim text"
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert verified == ["valid claim"]
    assert unsourced == []


def test_non_string_claims_dropped_silently():
    """LLM contract is list[str]; non-string entries are skipped."""
    claims = [None, 42, "valid claim"]  # type: ignore[list-item]
    raw = "the valid claim is here"
    verified, unsourced = verify_claims_in_raw(claims, raw)  # type: ignore[arg-type]
    assert verified == ["valid claim"]
    assert unsourced == []


def test_mixed_verified_and_unsourced():
    claims = [
        "shipped LLM tool",
        "lifted revenue by 99 percent",  # not in raw
        "ran A/B tests",
    ]
    raw = (
        "Built and shipped llm tool in 3 months. "
        "Ran A/B tests on prompt variants."
    )
    verified, unsourced = verify_claims_in_raw(claims, raw)
    assert "shipped LLM tool" in verified
    assert "ran A/B tests" in verified
    assert "lifted revenue by 99 percent" in unsourced
