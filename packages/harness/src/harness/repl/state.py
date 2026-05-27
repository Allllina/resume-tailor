"""RunState — short-term memory per REPL run.

Per HARNESS_DESIGN.md §10 Memory layering. Designed to serialize to
harness-tailor-output.schema.json (run_id / verdict / tier_assigned /
matched_resume_version / lens_routing / experience_selection_trace /
trace / metrics / degradation_events).
"""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


Verdict = Literal[
    "complete",
    "partial_pending_user",
    "failed",
    "degraded_to_manual",
    "degraded_no_substance",
    "user_aborted",
]
Stage = Literal["perception", "planning", "action", "feedback"]


class TraceEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stage: Stage
    event_type: str
    payload: dict = Field(default_factory=dict)


class DegradationEvent(BaseModel):
    stage: Stage
    reason: str
    fallback_taken: str


class RunState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tier: int | None = None
    matched_resume_version: str | None = None
    lens_routing: dict = Field(default_factory=dict)
    experience_selection_trace: list[dict] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    degradation_events: list[DegradationEvent] = Field(default_factory=list)
    verdict: Verdict | None = None
    tex_artifact_path: str | None = None
    pdf_artifact_path: str | None = None
    jd_context: dict | None = None
    change_cards: list[dict] = Field(default_factory=list)
    match_scores: dict | None = None  # output of verdict_scorer.score_run
    lifecycle: dict | None = None  # Wave 4 Step C — see harness.lifecycle
    competency_model: dict | None = None  # Wave 4 Step B — see harness.competency
    rewrite_engine_output: dict | None = None  # Wave 4 D.2b — serialized RewriteOutput per harness-tailor-output schema; populated for Tier 2/3 runs via model_dump_jsonable()
    pass3_trace: dict | None = None  # Wave 4 D.4c — Pass 3 verifier summary; see harness/verify/pass3.py
    fit_diagnosis_pre_rewrite: dict | None = None  # Wave 5 F1 — see harness.fit_diagnosis (pre_rewrite mode)
    fit_diagnosis_post_rewrite: dict | None = None  # Wave 5 F3 — see harness.fit_diagnosis (post_rewrite mode)
    gap_bridging: dict | None = None  # Wave 5 F6 — see harness.gap_bridging
    quality_pass_report: dict | None = None  # Wave 5 P2 — Pass 1.5 Chinese readability + Pass 2 R-11 cleanup
    substance_check: dict | None = None  # Gate 1 v0.6.1 — R-18 quality floor; see harness.verdict.substance_check
    metrics: dict = Field(
        default_factory=lambda: {
            "total_tokens": 0,
            "total_claude_calls": 0,
            "elapsed_seconds": 0.0,
            "cost_usd": 0.0,
        }
    )

    def add_event(self, stage: Stage, event_type: str, payload: dict | None = None) -> None:
        self.trace_events.append(
            TraceEvent(stage=stage, event_type=event_type, payload=payload or {})
        )

    def add_degradation(self, stage: Stage, reason: str, fallback: str) -> None:
        self.degradation_events.append(
            DegradationEvent(stage=stage, reason=reason, fallback_taken=fallback)
        )

    @property
    def resume_match_score(self) -> float:
        return (self.match_scores or {}).get("resume_match_score", 0.0)
