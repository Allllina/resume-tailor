"""Step 6 disambiguator injection — R-7 enforcement.

Per resume-rewrite-engine/SKILL.md Hard rule R-7:
- Only add disambiguator in Cat 1 / Cat 2 main bullets
- NEVER add in Cat 3 backup line (招聘方 1 秒扫过 backup, 括号被忽略;
  R-7 round 3 fix from 2026-05-04 Anker AIGC 试跑)
- Cat 4 (cut) — N/A
- Lens-specific lookup from
  index.json[exp].disambiguator_per_industry[target_industry]
"""
import json
from pathlib import Path
from typing import Optional


class Disambiguator:
    def __init__(self, repo_root: Path):
        index_path = repo_root / "assets" / "experience-bank" / "index.json"
        data = json.loads(index_path.read_text())
        self._index: dict[str, dict] = {exp["id"]: exp for exp in data["experiences"]}

    def lookup(self, experience_id: str, target_industry: str) -> Optional[str]:
        """Return the disambiguator text for (exp, industry) or None.

        Returns None when:
        - experience_id unknown
        - exp.disambiguator_per_industry is null (品牌足够强)
        - exp.disambiguator_per_industry[target_industry] is null / missing
        """
        exp = self._index.get(experience_id)
        if not exp:
            return None
        dpi = exp.get("disambiguator_per_industry")
        if dpi is None:
            return None
        cell = dpi.get(target_industry)
        if cell is None:
            return None
        # cell may be a dict {type, text, rationale} or just a string text
        if isinstance(cell, dict):
            return cell.get("text")
        return cell  # string

    def apply(
        self,
        experience_id: str,
        target_industry: str,
        company_text: str,
        final_category: int,
    ) -> str:
        """Return company_text with disambiguator parenthetical iff Cat 1 or 2.

        Per R-7: Cat 3 (backup line) and Cat 4 (cut) — return company_text
        unchanged. Even if a disambiguator is registered for this lookup.
        """
        if final_category not in (1, 2):
            return company_text
        text = self.lookup(experience_id, target_industry)
        if text is None:
            return company_text
        return f"{company_text}（{text}）"
