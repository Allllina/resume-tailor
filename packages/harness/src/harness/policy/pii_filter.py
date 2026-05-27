"""PII detection + redaction + restoration.

Per HARNESS_COMPLIANCE_AUDIT.md Gap 1 (HIGH SEVERITY).
Closes the LLM-prompt PII leak — candidate names + phones + emails are
replaced with stable placeholders before any Claude API call.

THREAT MODEL
============

In scope:
- Candidate names (user-supplied via known_names, longest-first match)
- Phone numbers: CN (+86, bare 1[3-9]9d), US (+1, parenthesized, dotted,
  bare), HK (+852), UK (+44)
- Email addresses (ASCII local + domain, single-line)

Out of scope (NOT detected — caller responsibility):
- Companies, schools, project names (these are SIGNAL for tailoring,
  not PII; redacting them defeats the product)
- Addresses, SSN, government IDs, passport numbers, DOB
- IDN / unicode emails (e.g., 用户@example.公司)
- Multi-line emails (split across newlines)

Trust assumptions:
- known_names is curated upstream. Supplying overly broad entries (e.g.,
  ["the"]) destroys text. The class warns when name length < 2.
- Placeholders [CANDIDATE_NAME], [PHONE_N], [EMAIL_N] are reserved tokens.
  Input text containing these literal placeholders will round-trip
  incorrectly. Caller must validate input.

INVARIANT
=========

restore() is for LOCAL TRUSTED OUTPUT ONLY. Never call restore() on text
that will be:
- re-sent to an LLM
- written to logs / metrics events
- forwarded via email / Notion / external sink

Restore is only for the final user-visible artifact (e.g., the .tex file
shown in the Inbox UI). Misusing restore() defeats the entire filter.
"""
import re
import warnings
from dataclasses import dataclass
from typing import Iterable


@dataclass
class PIIToken:
    """One redacted span with its placeholder and original PII text."""
    kind: str  # "PHONE" | "EMAIL" | "CANDIDATE_NAME"
    placeholder: str  # e.g. "[CANDIDATE_NAME]" or "[PHONE_3]"
    original: str  # original PII text


# Phone patterns — covers CN / US / HK / UK.
# Order matters: longest / most-specific first so that, e.g., +852 wins over
# bare 8-digit US 3-3-4 patterns. Each pattern runs as a single re.sub pass.
_PHONE_PATTERNS = [
    re.compile(r"\+?86[-\s]?1\d{2}[-\s]?\d{4}[-\s]?\d{4}"),         # +86 138-2316-6715
    re.compile(r"\+?852[-\s]?\d{4}[-\s]?\d{4}"),                     # +852 9123 4567 (HK)
    re.compile(r"\+?44[-\s]?\d{2,5}[-\s]?\d{3,4}[-\s]?\d{3,4}"),     # +44 20 7946 0958 (UK)
    re.compile(r"\+?1[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4}"),            # +1 929-791-3436
    re.compile(r"\(\d{3}\)\s?\d{3}[-\s.]?\d{4}"),                    # (929) 791-3436
    re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),                  # 929-791-3436 / 929.791.3436
    re.compile(r"\b1[3-9]\d{9}\b"),                                   # 13823166715 (CN bare 11)
]
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Detect Latin-script in name (use word-boundary regex if any Latin letter present)
_LATIN_DETECT = re.compile(r"[A-Za-z]")


class PIIFilter:
    def __init__(self, known_names: Iterable[str] = ()):
        # Sort by length descending so longest names match first (e.g., 'Alina' before '陈')
        names = sorted(set(known_names), key=lambda n: (-len(n), n))
        # Warn on suspiciously short Latin-script names. CJK surnames are
        # legitimately single-char (陈 / 王 / 李) so don't warn on them.
        for n in names:
            if len(n) < 2 and n.isascii():
                warnings.warn(
                    f"PIIFilter: known_name {n!r} is < 2 chars (ASCII), may over-redact",
                    UserWarning,
                    stacklevel=2,
                )
        self.known_names = names

    def redact(self, text: str) -> tuple[str, list[PIIToken]]:
        if not text:
            return text, []

        mapping: list[PIIToken] = []

        # 1. Emails first (most structured PII; highest precision).
        #    Run before phones so digits inside email local-part don't get
        #    pulled by phone regex; run before names so name substrings inside
        #    local-part don't fragment the address.
        email_count = 0

        def _email_sub(match: re.Match) -> str:
            nonlocal email_count
            email_count += 1
            placeholder = f"[EMAIL_{email_count}]"
            mapping.append(
                PIIToken(kind="EMAIL", placeholder=placeholder, original=match.group(0))
            )
            return placeholder

        text = _EMAIL_PATTERN.sub(_email_sub, text)

        # 2. Phones — multiple patterns. Use re.sub callback so each match
        #    produces a fresh placeholder atomically; no findall snapshot drift.
        phone_count = 0

        def _make_phone_sub():
            def _phone_sub(match: re.Match) -> str:
                nonlocal phone_count
                phone_count += 1
                placeholder = f"[PHONE_{phone_count}]"
                mapping.append(
                    PIIToken(kind="PHONE", placeholder=placeholder, original=match.group(0))
                )
                return placeholder
            return _phone_sub

        for pat in _PHONE_PATTERNS:
            text = pat.sub(_make_phone_sub(), text)

        # 3. Names last (most likely to overlap other patterns).
        #    Latin-script names get \b word boundary; CJK uses bare substring
        #    (Chinese has no word-boundary semantics).
        for name in self.known_names:
            placeholder = "[CANDIDATE_NAME]"
            if _LATIN_DETECT.search(name):
                # Latin-script: word boundary + escaped pattern.
                # re.escape protects names with `'`, `-`, `.` (e.g., O'Brien).
                pat = re.compile(r"\b" + re.escape(name) + r"\b")
                if pat.search(text):
                    text = pat.sub(placeholder, text)
                    mapping.append(
                        PIIToken(kind="CANDIDATE_NAME", placeholder=placeholder, original=name)
                    )
            else:
                # CJK / non-Latin: bare substring (no word boundary in Chinese).
                if name in text:
                    text = text.replace(name, placeholder)
                    mapping.append(
                        PIIToken(kind="CANDIDATE_NAME", placeholder=placeholder, original=name)
                    )

        return text, mapping

    def restore(self, redacted_text: str, mapping: list[PIIToken]) -> str:
        # Restore in iteration order; PHONE/EMAIL placeholders are unique
        # (numbered), so order-independent. CANDIDATE_NAME may repeat — restore
        # each occurrence in iteration order.
        for token in mapping:
            redacted_text = redacted_text.replace(token.placeholder, token.original, 1)
        return redacted_text
