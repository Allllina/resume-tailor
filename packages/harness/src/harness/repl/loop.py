"""REPL loop orchestrator — Tier 1 path.

Per HARNESS_DESIGN.md §3.4 Loop termination conditions. Wave 1
implements the Tier 1 happy path: lens routing → master selection →
skill row reorder → summary regen → tex write.

Failure paths emit DegradationEvent records but always return a
schema-compliant output dict.
"""
import time
from pathlib import Path

from .eval import Tier1Tools
from .print import assemble_output
from .stages import (
    run_action,
    run_early_feedback,
    run_late_feedback,
    run_perception,
    run_planning,
)
from .state import RunState


async def run_tier1(
    jd_text: str,
    target_market: str,
    repo_root: Path,
    tools: Tier1Tools,
    candidate_names: list[str],
    jd_context: dict | None = None,
    runs_root: Path | None = None,
) -> dict:
    """Run one Tier 1 PPAF cycle. Returns harness-tailor-output dict.

    runs_root: where to persist data/runs/<id>/. If None, uses legacy global
    `packages/harness/data/runs/` path (Wave 1 behavior). Multi-user callers
    pass `data/users/{user_id}/runs/`.
    """
    # WHY: tier is now derived dynamically (W4 D.3) by assign_tier() between
    # PLANNING and ACTION. We start with tier=None and let the router set it
    # based on resume_match_score; default to 1 only if scoring fails.
    state = RunState(tier=None)
    if jd_context:
        state.jd_context = jd_context
    started = time.monotonic()

    # PPAF stages — each mutates state in-place; planning may bail with None.
    await run_perception(state, jd_text, target_market)
    planning_result = await run_planning(state, jd_text, target_market, repo_root, tools)
    if planning_result is None:
        # Master selection failed; verdict already set. Bail with whatever's in state.
        state.metrics["elapsed_seconds"] = time.monotonic() - started
        return assemble_output(state)
    routing, master_tex, target_industry, index_data = planning_result

    await run_early_feedback(state, routing, index_data)
    final_tex = await run_action(
        state, jd_text, target_market, repo_root, tools,
        routing, master_tex, target_industry, index_data,
    )
    return await run_late_feedback(state, final_tex, repo_root, runs_root, started, tools=tools)
