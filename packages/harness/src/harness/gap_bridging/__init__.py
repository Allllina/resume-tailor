"""harness.gap_bridging — backend for the gap-bridging-planner sub-skill."""
from .engine import build_gap_bridging_plan, fallback_gap_bridging_plan

__all__ = ["build_gap_bridging_plan", "fallback_gap_bridging_plan"]
