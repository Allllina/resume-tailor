"""Print stage — feedback assembler.

Per HARNESS_DESIGN.md §3.3 (Print). Converts RunState to a
harness-tailor-output.schema.json compliant dict for the API caller.
"""
from .state import RunState


def assemble_output(state: RunState) -> dict:
    """Convert RunState → harness-tailor-output.schema.json compliant dict.

    The dict will be re-validated against the schema at the API boundary
    (Task 19). Here we just project the in-memory state to the output shape.
    """
    out = {
        "run_id": str(state.run_id),
        "input_ref": "<set by API layer>",
        "verdict": state.verdict or "failed",
        "tier_assigned": state.tier or 1,
        "matched_resume_version": state.matched_resume_version or "C_product_ops",
        "lens_routing": state.lens_routing,
        "experience_selection_trace": state.experience_selection_trace,
        "tex_artifact_path": state.tex_artifact_path or "",
        "trace": {
            "perception_events": [e.model_dump(mode="json") for e in state.trace_events if e.stage == "perception"],
            "planning_events": [e.model_dump(mode="json") for e in state.trace_events if e.stage == "planning"],
            "action_events": [e.model_dump(mode="json") for e in state.trace_events if e.stage == "action"],
            "feedback_events": [e.model_dump(mode="json") for e in state.trace_events if e.stage == "feedback"],
        },
        "metrics": state.metrics,
        "degradation_events": [e.model_dump(mode="json") for e in state.degradation_events],
        "created_at": state.started_at.isoformat(),
    }
    if state.jd_context:
        out["jd_context"] = state.jd_context
    if state.change_cards:
        out["change_cards"] = state.change_cards
    if state.match_scores:
        out["match_scores"] = state.match_scores
    if state.lifecycle:
        out["lifecycle"] = state.lifecycle
    if state.competency_model:
        out["competency_model"] = state.competency_model
    if state.rewrite_engine_output:
        out["rewrite_engine_output"] = state.rewrite_engine_output
    if state.pass3_trace:
        out["pass3_trace"] = state.pass3_trace
    if state.fit_diagnosis_pre_rewrite:
        out["fit_diagnosis_pre_rewrite"] = state.fit_diagnosis_pre_rewrite
    if state.fit_diagnosis_post_rewrite:
        out["fit_diagnosis_post_rewrite"] = state.fit_diagnosis_post_rewrite
    if state.gap_bridging:
        out["gap_bridging"] = state.gap_bridging
    if state.quality_pass_report:
        out["quality_pass_report"] = state.quality_pass_report
    if state.substance_check is not None:
        out["substance_check"] = state.substance_check
    return out
