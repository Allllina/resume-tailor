"""Heuristic prompt injection detection.

Per HARNESS_DESIGN.md §6 (Policy gateway boundary).
Wave 1: simple keyword-based detector. Wave 2+ may upgrade to LLM-based.

Patterns are intentionally narrow — false positives would deny legitimate
JD content. Add new patterns when real attacks surface, not preemptively.
"""
import re

_INJECTION_MARKERS = [
    # "ignore previous instructions" / "ignore all prior instructions" /
    # "ignore the above instructions" — allow up to a few interstitial words
    # like "all", "any", "the", etc. between the verb and the qualifier.
    r"ignore\s+(\w+\s+){0,3}(previous|above|prior)\s+instructions",
    r"disregard\s+(\w+\s+){0,3}(previous|above|prior)\s+instructions",
    r"new\s+system\s+prompt:",
    r"</?system>",
    r"</?user>",
    r"\[INST\]",
    r"\[/INST\]",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_MARKERS), re.IGNORECASE)


def detect_injection(text: str) -> list[str]:
    """Return list of injection-marker strings found in text. Empty if clean."""
    if not text:
        return []
    found = []
    for m in _INJECTION_RE.finditer(text):
        # Get the matched span (whichever alternation fired)
        found.append(m.group(0))
    return found
