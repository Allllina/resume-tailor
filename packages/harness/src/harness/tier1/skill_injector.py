"""Skills section reorder — deterministic, with bilingual keyword bridge.

Per Tier 1 Light Tailoring (R-9): Skills 行 may reorder + add from
existing tool bank, but cannot fabricate new tools. This module only
reorders.

Strategy: extract JD keywords + expand via bilingual bridge → rank
each \\item by JD-keyword overlap frequency. Highest-scoring row moves
to position 1.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Callable


_DEFAULT_BRIDGE_PATH = (
    Path(__file__).resolve().parents[5]
    / "assets"
    / "knowledge-base"
    / "references"
    / "keyword-bridge.json"
)


def _load_bridge(path: Path = _DEFAULT_BRIDGE_PATH) -> dict[str, list[str]]:
    """Load bridge mapping {cn_or_en_term: [equivalent_skill_tokens]}.

    Bridge file is OPTIONAL — returns empty dict if missing so tests/
    isolated runs don't break.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("bridges", {}) or {}
    except (json.JSONDecodeError, OSError):
        return {}


class SkillInjector:
    def __init__(
        self,
        jd_keywords_extractor: Callable[[str], list[str]] | None = None,
        bridge: dict[str, list[str]] | None = None,
    ):
        self._extractor = jd_keywords_extractor or self._default_extractor
        self._bridge = bridge if bridge is not None else _load_bridge()

    def reorder_skills_section(
        self,
        tex: str,
        jd_text: str,
        extra_keywords: list[str] | None = None,
    ) -> str:
        """Find the Skills section in `tex`; reorder \\item rows by JD relevance.

        If no Skills section found OR no items in it OR jd_text is empty,
        return tex unchanged. `extra_keywords` (Wave 4 Step B) lets callers
        merge in additional ranking terms — e.g. tiers 1/2/3/5 from the
        role-competency-extractor's Section D — alongside the JD-extractor +
        bilingual bridge keywords. Behavior is purely additive: when None
        or empty, scoring matches the pre-Wave-4 behavior exactly.
        """
        if not jd_text:
            return tex

        # Locate the Skills section's itemize body. Skills section heading
        # patterns observed: 技能 / 技能/证书 / 技能 与其他 / Skills 等.
        section_pattern = re.compile(
            r"(\\section\{[^}]*技能[^}]*\}.*?\\begin\{itemize\}\s*)(.*?)(\s*\\end\{itemize\})",
            re.DOTALL,
        )
        match = section_pattern.search(tex)
        if not match:
            return tex

        prefix, body, suffix = match.group(1), match.group(2), match.group(3)
        items = re.findall(r"\\item[^\n]*(?:\n(?!\s*\\item|\s*\\end)[^\n]*)*", body)
        if not items:
            return tex

        keywords = self._extractor(jd_text)
        if not keywords and not extra_keywords:
            return tex

        # Bridge expansion: for each extracted keyword, also include any
        # bridged equivalents. Case-insensitive matching against bridge keys.
        expanded: list[str] = list(keywords)
        for kw in keywords:
            kw_lower = kw.lower()
            for bridge_key, bridged in self._bridge.items():
                if bridge_key.lower() == kw_lower or bridge_key.lower() in kw_lower:
                    expanded.extend(bridged)
        # Merge in extractor-provided extras (e.g. competency Section D)
        if extra_keywords:
            for kw in extra_keywords:
                if isinstance(kw, str) and kw.strip():
                    expanded.append(kw.strip())
        # Dedup while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for kw in expanded:
            kl = kw.lower()
            if kl not in seen:
                seen.add(kl)
                deduped.append(kw)

        kw_lower = [k.lower() for k in deduped]
        scored = []
        for item in items:
            item_lower = item.lower()
            score = sum(1 for kw in kw_lower if kw in item_lower)
            scored.append((score, item))

        # Stable sort by score descending; preserves original order on ties
        # to avoid unnecessary churn.
        scored.sort(key=lambda x: -x[0])
        new_body = "\n    " + "\n    ".join(item.strip() for _, item in scored) + "\n"

        # Replace the captured body in the original tex
        return tex[: match.start(2)] + new_body + tex[match.end(2):]

    @staticmethod
    def _default_extractor(jd_text: str) -> list[str]:
        """Naive token frequency extractor.

        Splits on whitespace + keeps tokens of len >= 2 (CJK chars or alphanum).
        Returns top-30 by frequency.
        """
        tokens = re.findall(r"[A-Za-z一-鿿][A-Za-z一-鿿\d]{1,}", jd_text)
        common = Counter(tokens).most_common(30)
        return [t for t, _ in common]
