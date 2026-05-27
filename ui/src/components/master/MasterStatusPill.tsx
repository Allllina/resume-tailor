import { Loader2 } from "lucide-react";
import type { MasterGenStatus } from "@/lib/api";

const META: Record<
  MasterGenStatus,
  { color: string; bg: string; label: string; spin?: boolean }
> = {
  ready: {
    color: "var(--verified)",
    bg: "color-mix(in oklab, var(--verified) 12%, transparent)",
    label: "ready",
  },
  generating: {
    color: "var(--primary)",
    bg: "color-mix(in oklab, var(--primary) 12%, transparent)",
    label: "generating",
    spin: true,
  },
  absent: {
    color: "var(--muted-foreground)",
    bg: "var(--muted)",
    label: "absent",
  },
};

/**
 * Pill matching the visual idiom of ScoringStatusPill — small dot, color
 * indicates state, label spells it out. Rendered in:
 *  - /setup Step 3 (mid-onboarding generation list)
 *  - /settings Per-Direction Masters table
 */
export function MasterStatusPill({ status }: { status: MasterGenStatus }) {
  const m = META[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium"
      style={{ color: m.color, background: m.bg }}
      data-testid={`master-status-${status}`}
    >
      {m.spin ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <span
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: m.color }}
        />
      )}
      {m.label}
    </span>
  );
}
