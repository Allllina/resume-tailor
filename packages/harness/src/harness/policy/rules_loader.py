"""Load R-1..R-8 hard rules from JSON encodings.

Per HARNESS_COMPLIANCE_AUDIT.md Gap 2.
forbidden-patterns.json + truthfulness-checklist.json -> enforceable rules.

Consumers:
- Task 7 PolicyGateway: calls find_violations(content) before allowing
  bullet_rewrite / skill_inject / summary_write actions
- Wave 2 Pass 3 verifier: uses hard_locked_fields() + detection_heuristics()
  + actions_when_unsourced() as grading rubric
"""
import json
from pathlib import Path
from typing import Any


class RulesLoader:
    """Eager-loads R-1..R-8 JSON rules at construction.

    Files loaded:
    - assets/knowledge-base/references/forbidden-patterns.json
    - assets/knowledge-base/references/truthfulness-checklist.json
    """

    def __init__(self, repo_root: Path):
        ref_dir = repo_root / "assets" / "knowledge-base" / "references"
        forbidden_path = ref_dir / "forbidden-patterns.json"
        truthfulness_path = ref_dir / "truthfulness-checklist.json"
        self._forbidden: dict[str, list[dict[str, Any]]] = json.loads(
            forbidden_path.read_text()
        )["categories"]
        self._truthfulness: dict[str, Any] = json.loads(truthfulness_path.read_text())

    def forbidden_categories(self) -> list[str]:
        """List of category names in forbidden-patterns.json."""
        return list(self._forbidden.keys())

    def find_violations(self, text: str) -> list[dict[str, Any]]:
        """Return all forbidden patterns present in `text`.

        Wave 1 implementation: literal substring match (per match_type='literal'
        on every entry). Future regex support reads match_type='regex' and
        compiles via re. For now, only literal is honored.

        Returns: list of dicts with keys {category, pattern, match_type,
        replacement, rationale} per matched entry. Empty list if none.
        """
        if not text:
            return []
        violations = []
        for category, patterns in self._forbidden.items():
            for entry in patterns:
                pattern = entry["pattern"]
                match_type = entry.get("match_type", "literal")
                if match_type == "literal" and pattern in text:
                    violations.append({
                        "category": category,
                        "pattern": pattern,
                        "match_type": match_type,
                        "replacement": entry.get("replacement", ""),
                        "rationale": entry.get("rationale", ""),
                    })
                # Future: handle match_type="regex" via re.compile + search
        return violations

    def hard_locked_fields(self) -> list[str]:
        """Fields that must never change (R-1)."""
        return list(self._truthfulness["hard_locked_fields"])

    def detection_heuristics(self) -> list[dict[str, Any]]:
        """Heuristic patterns for surfacing likely fabrications."""
        return list(self._truthfulness.get("detection_heuristics", []))

    def actions_when_unsourced(self) -> list[str]:
        """Canonical action enum for unsourced claims (remove/mark_TBD/ask_user)."""
        return list(self._truthfulness["actions_when_unsourced"])
