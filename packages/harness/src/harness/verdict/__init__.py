"""Verdict-level computations applied after the PPAF pipeline completes.

Currently:
- `substance_check.compute_substance_check` — Gate 1 / R-18 quality floor
  (see SKILL.md R-18 + docs/plans/2026-05-12-gate1-verdict-substance-floor.md)
"""
from .substance_check import compute_substance_check

__all__ = ["compute_substance_check"]
