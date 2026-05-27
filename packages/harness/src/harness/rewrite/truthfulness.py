"""Truthfulness pre-check (Wave 4 D.2a).

Fast, deterministic substring gate. For every claimed_fact emitted by the
LLM rewrite engine in Section G, attempt to locate the claim inside the
relevant `assets/experience-bank/raw/<id>.md`. Any miss → caller raises
`UnsourcedClaimError`.

This is NOT a semantic verifier. Pass 3 (D.4 LangGraph) does paraphrase
matching and LLM-driven adjudication. D.2a's job is fail-loud on obvious
fabrication so we don't waste a Pass 3 round trip on broken candidates.

Looseness rules (pragmatic, intentionally lenient):
- Whitespace is collapsed and case is folded before substring search.
- Common Chinese / English punctuation that adds no semantic content is
  stripped from both sides of the comparison (commas, quotes, brackets,
  bullet markers).
- Numeric percentages match across notations: a claim containing `5%` is
  considered verified when the raw contains either `5%` OR `5 percent` OR
  `5 个百分点`. Likewise `5 percent` in a claim verifies against raw `5%`.
- Numbers themselves (e.g. revenue 50M) are matched verbatim — a claim
  containing `50M` only verifies if the raw mentions `50M` literally.
  Looseness here would let fabricated stats slip through.

Module exports:
    verify_claims_in_raw(claims, raw_text) -> (verified, unsourced)
    normalize_text(text) -> str  # exposed for tests / debugging
"""
from __future__ import annotations

import re


# Punctuation we strip before substring matching. Keep digits, alpha, CJK,
# and the percent sign — those carry semantic weight.
_NOISE_PUNCT_RE = re.compile(
    r"[\,\.\;\:\!\?\(\)\[\]\{\}\"\'`«»‹›\\　、。，；"
    r"：！？（）【】「」『』"
    r"‘’“”\—\–\-\*\#\>]+"
)


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase + strip noise punctuation + collapse whitespace.

    Preserves digits, percent signs, alphanumerics, and CJK characters.
    Used for both claim and raw text before substring matching.
    """
    if not text:
        return ""
    s = text.lower()
    s = _NOISE_PUNCT_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


_PERCENT_NUM_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_PERCENT_NUM_WORD_RE = re.compile(r"(\d+(?:\.\d+)?)\s*percent")
_PERCENT_NUM_CN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*个?百分点")

# Whitespace flanking a digit in CJK contexts is fluff: 提升 5% and 提升5%
# carry the same meaning. Strip whitespace immediately before/after digits
# so substring matching survives those tokenization choices.
_WS_BEFORE_DIGIT_RE = re.compile(r"\s+(?=\d)")
_WS_AFTER_DIGIT_RE = re.compile(r"(?<=\d)\s+")


def _canonicalize_percentages(text: str) -> str:
    """Rewrite all percentage notations in `text` to a single canonical form.

    `5%` / `5 percent` / `5个百分点` / `5百分点` → `5_PCT_`

    Also collapses whitespace immediately around digits so claim and raw
    written with different spacing conventions (`提升 5%` vs `提升5%`) align.
    """
    s = _PERCENT_NUM_CN_RE.sub(lambda m: f"{m.group(1)}_PCT_", text)
    s = _PERCENT_NUM_WORD_RE.sub(lambda m: f"{m.group(1)}_PCT_", s)
    s = _PERCENT_NUM_PCT_RE.sub(lambda m: f"{m.group(1)}_PCT_", s)
    s = _WS_BEFORE_DIGIT_RE.sub("", s)
    s = _WS_AFTER_DIGIT_RE.sub("", s)
    return s


def _claim_in_raw(claim: str, raw_norm: str) -> bool:
    """True if `claim` is a substring of `raw_norm` after percentage canonicalization."""
    claim_norm = normalize_text(claim)
    if not claim_norm:
        # Empty claim is vacuously verified — caller filters out empty.
        return True

    if claim_norm in raw_norm:
        return True

    # Percentage-loose comparison: rewrite both sides to a canonical form.
    claim_canon = _canonicalize_percentages(claim_norm)
    raw_canon = _canonicalize_percentages(raw_norm)
    return claim_canon in raw_canon


def verify_claims_in_raw(
    claims: list[str],
    raw_text: str,
) -> tuple[list[str], list[str]]:
    """Split `claims` into (verified, unsourced) by substring match against `raw_text`.

    Both verified and unsourced lists preserve original (pre-normalization)
    claim strings so error messages and logs read naturally.

    Empty `claims` → ([], []).
    Empty `raw_text` → all claims are unsourced (no source to ground in).
    """
    if not claims:
        return [], []

    raw_norm = normalize_text(raw_text)
    if not raw_norm:
        return [], [c for c in claims if isinstance(c, str)]

    verified: list[str] = []
    unsourced: list[str] = []
    for claim in claims:
        if not isinstance(claim, str):
            # Defensive: non-string claims are dropped silently. The LLM
            # contract is list[str]; anything else is malformed and
            # would only confuse error messages.
            continue
        if not claim.strip():
            continue
        if _claim_in_raw(claim, raw_norm):
            verified.append(claim)
        else:
            unsourced.append(claim)
    return verified, unsourced
