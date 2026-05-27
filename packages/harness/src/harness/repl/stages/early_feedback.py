"""Early FEEDBACK stage: verdict scoring + tier routing.

WHY: scoring + tier assignment must run BEFORE ACTION so ACTION can
dispatch Tier 1 light tailoring vs Tier 2/3 rewrite engine. Artifact
write + lifecycle seed stay in late_feedback. Events are tagged with
the "planning" stage string for wire-format compatibility with pre-M4
trace consumers.
"""
from harness.policy import assign_tier
from harness.tier1.verdict_scorer import score_run

from ..state import RunState, Stage

STAGE: Stage = "planning"


async def run_early_feedback(
    state: RunState,
    routing: dict,
    index_data: dict,
) -> None:
    try:
        state.match_scores = score_run(
            experiences=index_data.get("experiences", []),
            primary_lens=routing.get("primary_lens", ""),
            degradation_count=len(state.degradation_events),
            lens_routing_confidence=routing.get("confidence"),
            experience_selection_trace=state.experience_selection_trace,
        )
        state.add_event(
            STAGE,
            "verdict_scored",
            {
                "tier": state.match_scores["confidence_tier"],
                "score": state.match_scores["resume_match_score"],
            },
        )
    except Exception as e:
        state.add_degradation(STAGE, f"verdict scoring failed: {e}", "no tier label emitted")

    state.tier = assign_tier(
        resume_match_score=state.resume_match_score,
        jd_total_score=None,
        hard_filter_blocked=False,
    )
    state.add_event(
        STAGE,
        "tier_assigned",
        {
            "tier": state.tier,
            "resume_match_score": state.resume_match_score,
        },
    )
