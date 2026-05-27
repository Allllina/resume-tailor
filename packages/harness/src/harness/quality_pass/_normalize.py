"""Pure deterministic transforms for quality-pass-runner."""
from __future__ import annotations

import re
from typing import Any

from ._ai_tone_dict import (
    AI_TONE_REPLACEMENTS,
    CHINESE_READABILITY_REPLACEMENTS,
    STANDARD_TECHNICAL_TERMS,
)


_CJK_MARKETS = frozenset({"mainland-china", "hong-kong"})


def is_chinese_market(target_market: str) -> bool:
    return target_market in _CJK_MARKETS


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _has_word_boundary(term: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z -]*[A-Za-z]", term))


def _compile_term_pattern(term: str) -> re.Pattern[str]:
    flags = 0 if _contains_cjk(term) else re.IGNORECASE
    if _has_word_boundary(term):
        return re.compile(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", flags)
    return re.compile(re.escape(term), flags)


def _term_in_text(term: str, text: str) -> bool:
    if not text:
        return False
    return bool(_compile_term_pattern(term).search(text))


def _replacement_for_match(configured_term: str, matched: str, replacement: str) -> str:
    if configured_term == matched and matched[:1].isupper() and replacement:
        return replacement[:1].upper() + replacement[1:]
    return replacement


def normalize_chinese_readability(
    text: str,
    *,
    target_market: str,
) -> dict[str, Any]:
    enabled = is_chinese_market(target_market)
    if not enabled:
        return {
            "text": text,
            "enabled": False,
            "flagged_phrases": [],
            "preserved_english_terms": [],
            "verdict": "pass",
        }

    out = text or ""
    flagged: list[dict[str, str]] = []
    for item in CHINESE_READABILITY_REPLACEMENTS:
        term = item["term"]
        if term not in out:
            continue
        out = out.replace(term, item["replacement"])
        flagged.append(
            {
                "original": term,
                "replacement": item["replacement"],
                "reason": item["reason"],
            }
        )

    # Avoid "市场规模...测算测算" after replacing only the abbreviation.
    out = out.replace("市场规模（总量/可服务/可获取）测算", "市场规模测算（总量/可服务/可获取）")

    preserved = [
        {"term": term, "reason": "standard technical term"}
        for term in sorted(STANDARD_TECHNICAL_TERMS, key=str.lower)
        if term in out
    ]

    return {
        "text": out,
        "enabled": True,
        "flagged_phrases": flagged,
        "preserved_english_terms": preserved,
        "verdict": "pass",
    }


def normalize_ai_tone(
    text: str,
    *,
    jd_text: str,
) -> dict[str, Any]:
    out = text or ""
    replacements: list[dict[str, str]] = []
    protected: list[dict[str, str]] = []
    protected_terms: set[str] = set()

    for item in AI_TONE_REPLACEMENTS:
        term = item["term"]
        replacement = item["replacement"]
        pattern = _compile_term_pattern(term)

        first_match = pattern.search(out)
        if first_match is None:
            continue

        if _term_in_text(term, jd_text or ""):
            key = first_match.group(0).casefold()
            if key not in protected_terms:
                protected.append({"term": first_match.group(0), "reason": "in_jd"})
                protected_terms.add(key)
            continue

        seen = False
        first_original = first_match.group(0)

        def _sub(match: re.Match[str]) -> str:
            nonlocal seen
            seen = True
            return _replacement_for_match(term, match.group(0), replacement)

        out = pattern.sub(_sub, out)
        if seen:
            replacements.append(
                {"original": first_original, "replacement": replacement, "location": "body"}
            )

    out = _normalize_ai_punctuation(out)

    return {
        "text": out,
        "replacements_applied": replacements,
        "protected_skipped": protected,
        "verdict": "pass",
    }


def _normalize_ai_punctuation(text: str) -> str:
    out = text
    out = out.replace("——", "：")
    out = re.sub(r"(?<=\d)\s*→\s*(?=\d)", " 升至 ", out)
    out = re.sub(r"\s*→\s*", "、", out)
    out = re.sub(r"(?<=\d)-(?=\d)", " 至 ", out)
    return out


def build_pass_1_stub() -> dict[str, Any]:
    return {
        "injected_keywords": [],
        "hit_rate_before": "0/0",
        "hit_rate_after": "0/0",
        "unable_to_inject": [],
        "verdict": "pass",
    }


def build_pass_3_stub() -> dict[str, Any]:
    return {
        "verified_claims_count": 0,
        "unsourced_claims": [],
        "identity_lock_check": "pass",
        "identity_lock_violations": [],
        "verdict": "pass",
    }


__all__ = [
    "build_pass_1_stub",
    "build_pass_3_stub",
    "is_chinese_market",
    "normalize_ai_tone",
    "normalize_chinese_readability",
]
