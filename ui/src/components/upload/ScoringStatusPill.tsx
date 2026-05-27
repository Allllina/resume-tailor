import { Loader2 } from "lucide-react";
import type { ScoringStatus } from "@/lib/api";

const META: Record<
  ScoringStatus,
  { color: string; label: string; bg: string; spin?: boolean }
> = {
  queued: { color: "var(--muted-foreground)", bg: "var(--muted)", label: "queued" },
  scoring: {
    color: "var(--primary)",
    bg: "color-mix(in oklab, var(--primary) 12%, transparent)",
    label: "scoring",
    spin: true,
  },
  done: {
    color: "var(--verified)",
    bg: "color-mix(in oklab, var(--verified) 12%, transparent)",
    label: "scored",
  },
  failed: {
    color: "var(--error)",
    bg: "color-mix(in oklab, var(--error) 12%, transparent)",
    label: "failed",
  },
};

export function ScoringStatusPill({ status }: { status: ScoringStatus }) {
  const m = META[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium"
      style={{ color: m.color, background: m.bg }}
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
