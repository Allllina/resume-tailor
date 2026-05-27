"""Shared parser for index.json cell shapes.

Cells in `assets/experience-bank/index.json` come in two shapes:
- v0.2.0 hand-curated: `{score: "high|medium|low|core|adjacent|...", ...}`
- Wave 2.7 auto_scorer:  `{value: "high|medium|...", ...}`
Plus bare strings from older fixtures and `None` for unscored cells.
"""
from __future__ import annotations

from typing import Any


def extract_cell_score(cell: Any) -> str | None:
    """Return the categorical value of a cell, or None if unscored.

    Handles {value: ...}, {score: ...}, bare string, and None.
    """
    if isinstance(cell, dict):
        return cell.get("value") or cell.get("score")
    if isinstance(cell, str):
        return cell
    return None
