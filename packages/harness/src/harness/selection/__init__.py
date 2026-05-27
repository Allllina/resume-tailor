"""Per-experience 3-pass selection algorithm (Wave 4 D.1).

See `three_pass.py` for the canonical Pass A → Pass B → Pass C selector
that populates `state.experience_selection_trace`.
"""
from .three_pass import (
    ExperienceTrace,
    run_three_pass,
)

__all__ = ["ExperienceTrace", "run_three_pass"]
