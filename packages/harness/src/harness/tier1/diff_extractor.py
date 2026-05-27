"""Extract before/after content from .tex for ChangeCard rendering.

Used by repl/loop.py to populate state.change_cards after each Tier 1
transform. Pure string parsing; no LLM.
"""
from __future__ import annotations

import re


_SKILLS_SECTION = re.compile(
    r"\\section\{[^}]*技能[^}]*\}.*?\\begin\{itemize\}\s*(.*?)\s*\\end\{itemize\}",
    re.DOTALL,
)
_SUMMARY_SECTION = re.compile(
    r"\\section\*?\{Summary\}\s*\n(.*?)\n\s*\\vspace\{0\.4em\}",
    re.DOTALL,
)


def extract_skills_block(tex: str) -> str:
    """Return concatenated \\item lines inside the Skills itemize, or '' if absent.

    Each item rendered on its own line, leading \\item stripped, whitespace
    collapsed for easier diff display in UI.
    """
    m = _SKILLS_SECTION.search(tex)
    if not m:
        return ""
    body = m.group(1)
    items = re.findall(r"\\item\s+([^\n]+)", body)
    cleaned = [re.sub(r"\s+", " ", it).strip() for it in items]
    return " · ".join(cleaned)


def extract_summary_block(tex: str) -> str:
    """Return existing Summary section text, or '' if no Summary section."""
    m = _SUMMARY_SECTION.search(tex)
    if not m:
        return ""
    return m.group(1).strip()
