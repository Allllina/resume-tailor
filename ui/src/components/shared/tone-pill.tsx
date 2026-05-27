// Shared TonePill — single source for the emerald/amber/red/orange/muted
// sentiment vocabulary used by every enum-driven badge in the app
// (verdict pill in MatchMatrixPanel, hard-filter / decision / effort pills
// in DualReviewPanel, future panels). Reviewer of D07.2 flagged 4
// near-identical pill components + 4 near-identical tone-color maps as
// duplication that would keep growing; this consolidates them.
//
// 5 tones: positive / warn / negative / info / neutral. Each maps to one
// Tailwind class string (border + bg + text in light, dark variant in
// dark). The mapping is intentionally narrower than what each individual
// pill had — slight visual flattening is the cost of single-source
// maintenance.
import type { ReactNode } from "react";

export type Tone = "positive" | "warn" | "negative" | "info" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  positive:
    "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  warn:
    "border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-300",
  negative:
    "border-red-500/40 bg-red-500/15 text-red-700 dark:text-red-300",
  info:
    "border-orange-500/30 bg-orange-500/15 text-orange-700 dark:text-orange-300",
  neutral: "border-border bg-muted text-muted-foreground",
};

interface TonePillProps {
  tone: Tone;
  ariaLabel: string;
  className?: string;
  children: ReactNode;
}

export function TonePill({
  tone,
  ariaLabel,
  className = "",
  children,
}: TonePillProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONE_CLASSES[tone]} ${className}`}
      aria-label={ariaLabel}
    >
      {children}
    </span>
  );
}
