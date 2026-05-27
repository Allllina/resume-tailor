"""PPAF stage handlers for run_tier1.

Each stage exposes one async function that mutates RunState in-place.
Stages are chained from `repl.loop.run_tier1`.
"""
from .perception import run_perception
from .planning import run_planning
from .early_feedback import run_early_feedback
from .action import run_action
from .late_feedback import run_late_feedback

__all__ = [
    "run_perception",
    "run_planning",
    "run_early_feedback",
    "run_action",
    "run_late_feedback",
]
