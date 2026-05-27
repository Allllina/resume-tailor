// Gate 2 / Phase 2 (v0.6.2 / v0.7.0) — sub-skill error banner for run detail.
//
// Renders above the change-card list when one or more degradation events
// indicate a critical sub-skill ran in fallback mode. The intent is to
// surface the "why" more prominently than the collapsed <details> in
// DegradationsList, and to distinguish LLM-transport failures (retry helps)
// from bad-output failures (retry might not help).
//
// The banner is intentionally non-blocking — it's informational and can be
// dismissed. The output is still valid; the user just needs to know the
// confidence is reduced.
import { useState } from "react";
import type { DegradationEvent } from "@/lib/api";

const LLM_STAGES = new Set([
  "competency_extractor",
  "fit_diagnosis_pre_rewrite",
  "rewrite_engine",
  "gap_bridging_planner",
  "fit_diagnosis_post_rewrite",
  "pass3_verifier",
  "summary_writer",
]);

function isLlmStage(stage: string): boolean {
  return LLM_STAGES.has(stage) || stage.includes("llm") || stage.includes("sub_skill");
}

interface Props {
  events: DegradationEvent[];
}

export function SubSkillErrorBanner({ events }: Props) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  const llmEvents = events.filter(
    (e) => isLlmStage(e.stage) || /llm|sub.?skill|unavailable/i.test(e.reason),
  );
  if (llmEvents.length === 0) return null;

  const isLikelyLlmDown = llmEvents.some((e) =>
    /unreachable|circuit|timeout|connection/i.test(e.reason),
  );

  return (
    <div
      role="alert"
      className="mb-4 flex items-start gap-3 rounded-xl border border-attention/30 bg-attention/5 px-4 py-3"
    >
      <span className="mt-0.5 text-sm text-attention-foreground/80">⚠</span>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-medium text-foreground">
          {llmEvents.length === 1
            ? `${llmEvents[0].stage} ran in fallback mode`
            : `${llmEvents.length} sub-skills ran in fallback mode`}
        </p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          {isLikelyLlmDown
            ? "LLM was unreachable during this run — output may be less tailored than usual. Regenerate when the service recovers."
            : "Some AI steps fell back to heuristics — the output is valid but confidence is reduced."}
        </p>
      </div>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="shrink-0 text-muted-foreground/60 hover:text-foreground transition text-base leading-none"
      >
        ×
      </button>
    </div>
  );
}
