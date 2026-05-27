"""PLANNING stage."""
import json
from pathlib import Path

from harness.competency.extractor import (
    extract_competencies,
    fallback_model,
)
from harness.fit_diagnosis import build_diagnosis
from harness.gap_bridging import build_gap_bridging_plan
from harness.selection.three_pass import run_three_pass

from ..eval import Tier1Tools
from ..state import RunState
from ._helpers import _emit_call_metrics


def _has_gap_bridging_work(fit_diagnosis: dict | None) -> bool:
    if not isinstance(fit_diagnosis, dict):
        return False
    for row in fit_diagnosis.get("matching_matrix") or []:
        if isinstance(row, dict) and row.get("verdict") in {"transferable", "missing"}:
            return True
    boundary = fit_diagnosis.get("optimization_boundary") or {}
    if isinstance(boundary, dict):
        for item in boundary.get("rewriting_cannot_solve") or []:
            if isinstance(item, str) and item.strip().endswith("; supplement"):
                return True
    return False


async def run_planning(
    state: RunState,
    jd_text: str,
    target_market: str,
    repo_root: Path,
    tools: Tier1Tools,
) -> tuple[dict, str, str, dict] | None:
    """Mutates state. Returns (routing, master_tex, target_industry, index_data) on
    success; None when planning aborted (e.g. master selection failed → caller
    should bail and return assemble_output(state) immediately)."""
    # Lens routing
    try:
        routing = await tools.lens_router.route(jd_text)
    except Exception as e:
        state.add_degradation("planning", f"lens routing failed: {e}", "default to C_product_ops")
        routing = {"primary_lens": "C_product_ops", "scenario": None, "blend_ratio": {}, "used_llm_fallback": False, "confidence": 0.0}
    state.lens_routing = routing
    state.add_event("planning", "lens_routed", {"primary_lens": routing.get("primary_lens"), "used_llm_fallback": routing.get("used_llm_fallback", False)})
    if routing.get("used_llm_fallback"):
        await _emit_call_metrics(state, tools, "planning", "lens_routing_call")

    # WHY: always populate state.competency_model (fallback on failure) so
    # downstream consumers don't need conditional branches.
    try:
        primary_lens_for_competency = routing.get("primary_lens") or ""
        state.competency_model = await extract_competencies(
            jd_text=jd_text,
            lens=primary_lens_for_competency,
            llm=tools.llm,
        )
        method = state.competency_model.get("_method", "fallback_no_llm")
        confidence_node = state.competency_model.get("section_i_limitations_confidence") or {}
        confidence = confidence_node.get("confidence", "low") if isinstance(confidence_node, dict) else "low"
        state.add_event(
            "planning",
            "competency_extracted",
            {"section_count": 9, "confidence": confidence, "method": method},
        )
        if method in ("llm", "llm_partial"):
            await _emit_call_metrics(state, tools, "planning", "competency_extractor_call")
        if method == "fallback_no_llm":
            state.add_degradation(
                "planning",
                "competency extraction returned fallback model",
                "use placeholder 9-section model",
            )
        elif method == "llm_partial":
            state.add_degradation(
                "planning",
                "competency model missing some sections",
                "fill missing sections with placeholders",
            )
    except Exception as e:
        state.add_degradation("planning", f"competency extraction failed: {e}", "use placeholder 9-section model")
        state.competency_model = fallback_model(routing.get("primary_lens") or "")

    # Master selection
    try:
        selection = tools.master_selector.select(routing["primary_lens"])
        if selection.fallback_used:
            state.add_degradation("planning", "primary master not delivered", f"fell back to {selection.master_path}")
        master_tex = selection.master_path.read_text()
        # When the user uploaded their own master, label it "custom" — not the
        # lens — so UI and downstream consumers don't misrepresent the user's
        # resume as a project-shipped lens template. Wave 4 C.1.3: the source
        # enum was extended for multi-lens onboarding; both per-lens and
        # legacy single-master variants of "user uploaded" map to "custom".
        if selection.metadata.get("source") in (
            "user_uploaded",
            "user_uploaded_per_lens",
            "user_uploaded_legacy",
        ):
            state.matched_resume_version = "custom"
        else:
            state.matched_resume_version = routing["primary_lens"]
    except Exception as e:
        state.add_degradation("planning", f"master selection failed: {e}", "abort run")
        state.verdict = "failed"
        return None

    # WHY: load index.json + derive target_industry in PLANNING (was ACTION) so
    # the 3-pass selector can run before ACTION; ACTION reuses the same dict.
    try:
        try:
            index_data = json.loads((repo_root / "assets/experience-bank/index.json").read_text())
        except FileNotFoundError:
            # D11 — fresh-clone fallback: sample data lives at index.sample.json.
            # `make seed-sample` would normally copy it to index.json; this catches
            # the un-seeded case so the loop still works.
            index_data = json.loads(
                (repo_root / "assets/experience-bank/index.sample.json").read_text()
            )
    except Exception as e:
        state.add_degradation("planning", f"index.json load failed: {e}", "use empty index")
        index_data = {"experiences": []}

    # Wave 1 default target_industry — heuristic from market.
    # mainland-china → internet_operational; north-america + hong-kong → internet_strategic
    target_industry = {
        "mainland-china": "internet_operational",
        "north-america": "internet_strategic",
        "hong-kong": "internet_strategic",
    }.get(target_market, "internet_operational")

    # 3-pass selection (Wave 4 D.1) — populates state.experience_selection_trace.
    # Wrapped: any failure leaves the trace empty so verdict_scorer falls back
    # to the closed-form path automatically.
    try:
        trace = await run_three_pass(
            experiences=index_data.get("experiences", []),
            jd_text=jd_text,
            primary_lens=routing.get("primary_lens", ""),
            target_industry=target_industry,
            competency_model=state.competency_model,
        )
        state.experience_selection_trace = list(trace)
        cat_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for entry in state.experience_selection_trace:
            cat_counts[entry["final_category"]] = cat_counts.get(entry["final_category"], 0) + 1
        state.add_event(
            "planning",
            "experience_selection_traced",
            {
                "count": len(state.experience_selection_trace),
                "cat1": cat_counts[1],
                "cat2": cat_counts[2],
                "cat3": cat_counts[3],
                "cat4": cat_counts[4],
            },
        )
    except Exception as e:
        state.add_degradation(
            "planning",
            f"3-pass selection failed: {e}",
            "leave experience_selection_trace empty; verdict_scorer falls back to closed-form",
        )

    # Wave 5 F2b — fit-diagnosis-engine pre_rewrite at PLANNING stage.
    # Runs after competency_model + experience_selection_trace are ready
    # so the matrix can ground its verdicts in the upstream signals.
    # Per Rule 1.3 + spec: build_diagnosis returns shape-valid fallback on
    # every documented LLM failure; no outer try/except so programmer
    # bugs surface. F2 keeps late_feedback's old match_matrix invocation
    # in parallel ("dual-output coexistence") until F2d cleanup.
    if state.competency_model and tools is not None:
        state.fit_diagnosis_pre_rewrite = await build_diagnosis(
            mode="pre_rewrite",
            target_market=target_market,
            jd_text=jd_text,
            competency_profile=state.competency_model,
            experience_selection_trace=state.experience_selection_trace,
            lens=(state.lens_routing or {}).get("primary_lens", "C_product_ops"),
            llm=tools.llm,
        )
        state.add_event("planning", "fit_diagnosis_pre_rewrite_built", {
            "method": state.fit_diagnosis_pre_rewrite.get("_method"),
            "confidence": state.fit_diagnosis_pre_rewrite.get("confidence"),
            "rating": state.fit_diagnosis_pre_rewrite.get("competitiveness_rating"),
        })
        if _has_gap_bridging_work(state.fit_diagnosis_pre_rewrite):
            state.gap_bridging = await build_gap_bridging_plan(
                fit_diagnosis_pre_rewrite=state.fit_diagnosis_pre_rewrite,
                competency_profile=state.competency_model,
                candidate_assets={
                    "profile": {},
                    # Trim to experience identity only. The full index.json
                    # (~46KB of per-industry scoring/recognition metadata)
                    # bloated the prompt and pushed the LLM response past
                    # max_tokens → truncated JSON → SubSkillUnavailable → 503
                    # (live smoke 2026-05-23). gap_bridging only needs to know
                    # which experiences exist to suggest reframes / adds.
                    "experience_bank_index": {
                        "experiences": [
                            {
                                k: e[k]
                                for k in (
                                    "id",
                                    "company",
                                    "role",
                                    "period",
                                    "one_line",
                                    "capability_tags",
                                )
                                if k in e
                            }
                            for e in (index_data.get("experiences") or [])
                            if isinstance(e, dict)
                        ],
                    },
                },
                target_market=target_market,
                application_timeline="immediate",
                llm=tools.llm,
            )
            state.add_event("planning", "gap_bridging_plan_built", {
                "method": state.gap_bridging.get("_method"),
                "confidence": state.gap_bridging.get("confidence"),
                "reframe_count": len(state.gap_bridging.get("reframe_directives") or []),
                "add_count": len(state.gap_bridging.get("add_suggestions") or []),
            })

    return routing, master_tex, target_industry, index_data
