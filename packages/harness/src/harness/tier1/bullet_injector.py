"""Inject Section G rewritten bullets into the master tex.

Per ARCHITECTURE.md §9 Tier 2/3 policy: bullet body rewrites land on
top of the existing master. We locate each experience's section in the
tex by company-name substring match against the `\\expheader{<company>}
{<role>}{<period>}{<location>}` macro, then replace the items inside
the immediately-following `\\begin{itemize} ... \\end{itemize}` block.

If we can't locate an experience, we silently skip its bullets and the
caller emits a degradation event. This is a **deterministic** transform
— no LLM calls.

Match heuristics:
- Case-insensitive substring match on the company string.
- We tolerate the master using either the full Chinese name or a
  shorter alias (e.g. "科尔尼" inside "科尔尼管理咨询"); the experience's
  index.json `company` may be the English name (e.g. "A.T. Kearney"),
  so we also try the experience id's stem (e.g. "01-kearney" → "kearney")
  and the `company_zh` field if present.

Limitations (acceptable per D.2b plan):
- Project section (`\\projheader{...}`) is not yet a target; bullets
  emitted for project-style experience ids will land in the skipped
  list.
- We don't preserve the bold "**xxx：**" prefix that decorates Tier 1
  bullets in the master — Tier 2/3 rewrites get plain text. The
  knowledge-base general-rules covers this trade-off; reviewer can flag
  if it bites.
"""
from __future__ import annotations

import re


_EXPHEADER_RE = re.compile(
    r"\\expheader\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}",
    re.DOTALL,
)


def _candidate_match_strings(experience: dict) -> list[str]:
    """Build a list of company-name candidates to substring-match the tex.

    Order matters: we try the most-specific name first. Returns
    lowercase variants for case-insensitive comparison.
    """
    out: list[str] = []
    # WHY: real master tex emits Chinese company names in \expheader{} blocks,
    # so company_zh is the highest-yield substring. We put it first; English
    # `company` is the fallback for English-language masters.
    for key in ("company_zh", "company", "company_en", "company_short", "company_alias"):
        v = experience.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip().lower())
    # Fallback: derive a hint from the id (e.g. "01-kearney" → "kearney").
    eid = experience.get("id")
    if isinstance(eid, str):
        # Strip leading "<digits>-" prefix.
        m = re.match(r"^\d+[-_](.+)$", eid)
        if m:
            out.append(m.group(1).strip().lower())
        else:
            out.append(eid.strip().lower())
    # Dedup, preserve order.
    seen: set[str] = set()
    deduped: list[str] = []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def _locate_experience_block(
    tex: str,
    candidates: list[str],
) -> tuple[int, int, int, int] | None:
    """Find the `\\begin{itemize}...\\end{itemize}` block belonging to an experience.

    Returns (begin_start, begin_end, end_start, end_end) — the spans of
    the begin/end tokens. Caller replaces the body between begin_end
    and end_start. Returns None if no match.

    Algorithm:
    1. Walk every `\\expheader{c}{r}{p}{l}` match in the tex.
    2. For the first one whose `c` (lowercased) contains any candidate
       substring (or vice-versa), find the next `\\begin{itemize}` after
       the header and the matching `\\end{itemize}`.
    """
    for header_match in _EXPHEADER_RE.finditer(tex):
        company = header_match.group(1).strip().lower()
        if not company:
            continue
        hit = False
        for cand in candidates:
            if not cand:
                continue
            if cand in company or company in cand:
                hit = True
                break
        if not hit:
            continue

        # Locate the immediately-following itemize block.
        after = header_match.end()
        begin_re = re.compile(r"\\begin\{itemize\}")
        end_re = re.compile(r"\\end\{itemize\}")
        begin_m = begin_re.search(tex, after)
        if not begin_m:
            return None
        end_m = end_re.search(tex, begin_m.end())
        if not end_m:
            return None
        # Reject if another \expheader fell between header and the begin
        # — that would mean we mis-matched and the block belongs to the
        # next experience.
        next_header = _EXPHEADER_RE.search(tex, after)
        if next_header and next_header.start() < begin_m.start():
            continue
        return (begin_m.start(), begin_m.end(), end_m.start(), end_m.end())

    return None


def _format_items(bullets: list[str]) -> str:
    """Render bullets as `\\item ...` lines with stable indentation.

    The master uses 4-space indented `\\item` rows; we keep that.
    """
    lines = []
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        lines.append(f"    \\item {text}")
    if not lines:
        return ""
    return "\n" + "\n".join(lines) + "\n"


def inject_bullets(
    tex: str,
    bullets_per_experience: dict[str, list[str]],
    experiences: list[dict],
) -> tuple[str, list[str]]:
    """Replace itemize-block contents per experience.

    Args:
        tex: master tex source.
        bullets_per_experience: {experience_id: [bullet_text, ...]}.
            Empty lists are skipped (no replacement).
        experiences: index.json experiences list (for company-name lookup).

    Returns:
        (new_tex, skipped_experience_ids). `skipped_experience_ids`
        contains every key from `bullets_per_experience` whose section
        could not be located in the tex. The original tex is preserved
        for skipped experiences.
    """
    if not bullets_per_experience:
        return tex, []

    exp_by_id = {e.get("id"): e for e in experiences if isinstance(e, dict)}
    skipped: list[str] = []
    new_tex = tex

    for experience_id, bullets in bullets_per_experience.items():
        if not bullets:
            # No bullets to inject — not a failure, just a no-op.
            continue
        experience = exp_by_id.get(experience_id)
        if experience is None:
            skipped.append(experience_id)
            continue

        candidates = _candidate_match_strings(experience)
        spans = _locate_experience_block(new_tex, candidates)
        if spans is None:
            skipped.append(experience_id)
            continue

        _begin_start, begin_end, end_start, _end_end = spans
        replacement = _format_items(bullets)
        if not replacement:
            # All bullets were empty strings; treat as skipped.
            skipped.append(experience_id)
            continue
        new_tex = new_tex[:begin_end] + replacement + new_tex[end_start:]

    return new_tex, skipped
