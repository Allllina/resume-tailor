// Gate 2 (v0.6.2) — LLM health status pill for the sidebar.
//
// Healthy = nothing rendered (the common case; no noise).
// Degraded = small yellow dot + label (1+ failures, circuit still closed).
// Down = red dot + "LLM unavailable" (circuit open, requests blocked).
// Loading/backend unreachable = nothing (avoid false alarms at startup).
import { useHealth } from "@/lib/queries";
import type { LLMHealthStatus } from "@/lib/api";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const STATUS_CONFIG: Record<
  Exclude<LLMHealthStatus, "healthy">,
  { dotColor: string; label: string; tooltip: string }
> = {
  degraded: {
    dotColor: "var(--attention)",
    label: "LLM unstable",
    tooltip: "LLM provider has recent failures. Tailoring may be slow.",
  },
  down: {
    dotColor: "var(--error)",
    label: "LLM unavailable",
    tooltip: "LLM circuit open — tailoring is blocked until the provider recovers.",
  },
};

interface Props {
  collapsed: boolean;
}

export function LlmHealthPill({ collapsed }: Props) {
  const { data } = useHealth();
  if (!data || data.llm.status === "healthy") return null;

  const status = data.llm.status as keyof typeof STATUS_CONFIG;
  const cfg = STATUS_CONFIG[status];
  if (!cfg) return null;

  const dot = (
    <span
      className="inline-block h-2 w-2 rounded-full shrink-0"
      style={{ background: cfg.dotColor }}
      aria-hidden
    />
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex justify-center py-1">{dot}</div>
        </TooltipTrigger>
        <TooltipContent side="right" className="text-xs">
          {cfg.tooltip}
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className="mx-2 mb-1 flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px]"
          style={{
            background: status === "down" ? "var(--error)/0.06" : "var(--attention)/0.06",
            color: status === "down" ? "var(--error)" : "var(--attention-foreground)",
            border: `1px solid ${status === "down" ? "var(--error)" : "var(--attention)"}22`,
          }}
        >
          {dot}
          <span className="flex-1 truncate font-medium">{cfg.label}</span>
          {data.llm.consecutive_failures > 0 && (
            <span className="font-mono text-[10px] opacity-60">
              ×{data.llm.consecutive_failures}
            </span>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs max-w-[220px]">
        {cfg.tooltip}
        {data.llm.seconds_since_last_failure != null && (
          <> Last failure {Math.round(data.llm.seconds_since_last_failure)}s ago.</>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
