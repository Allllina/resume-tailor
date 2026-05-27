/**
 * LifecycleBadge — small colored pill rendering the current lifecycle state.
 *
 * Used in two places:
 *   1. DraftCard (Inbox row) — next to the existing Status pip.
 *   2. DraftReview header — alongside the picker.
 *
 * Color tokens map to brand vars defined in styles.css:
 *   tailored                         → --primary (blue)
 *   applied                          → --verified (sage green)
 *   oa / interview                   → --attention (paper-yellow amber)
 *   offer                            → --verified (bold variant)
 *   rejected / dismissed / archived  → --muted-foreground
 */
import type { LifecycleState, LifecycleEvent } from "@/lib/api";
import { humanizeAge } from "@/lib/api";

interface BadgeMeta {
  /** CSS var or raw color used for the dot + text. */
  color: string;
  /** Display label shown in the pill. */
  label: string;
}

const META: Record<LifecycleState, BadgeMeta> = {
  tailored: { color: "var(--primary)", label: "Tailored" },
  applied: { color: "var(--verified)", label: "Applied" },
  oa: { color: "var(--attention)", label: "OA" },
  interview: { color: "var(--attention)", label: "Interview" },
  offer: { color: "var(--verified)", label: "Offer" },
  rejected: { color: "var(--muted-foreground)", label: "Rejected" },
  archived: { color: "var(--muted-foreground)", label: "Archived" },
  dismissed: { color: "var(--muted-foreground)", label: "Dismissed" },
};

interface Props {
  state: LifecycleState;
  /** Optional last lifecycle event — used to render channel + relative age. */
  lastEvent?: LifecycleEvent;
  /** Smaller variant for inline rendering on DraftCard. */
  size?: "sm" | "md";
  className?: string;
}

export function LifecycleBadge({ state, lastEvent, size = "md", className = "" }: Props) {
  const meta = META[state];
  const isOffer = state === "offer";
  const padX = size === "sm" ? "px-2" : "px-2.5";
  const padY = size === "sm" ? "py-0.5" : "py-1";
  const text = size === "sm" ? "text-[10px]" : "text-xs";

  const detail = formatDetail(state, lastEvent);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${padX} ${padY} ${text} font-medium ${className}`}
      style={{
        color: meta.color,
        borderColor: meta.color,
        backgroundColor: "transparent",
        // Offer = bolder fill so it visually pops vs. plain Applied
        ...(isOffer
          ? { backgroundColor: "color-mix(in oklab, var(--verified) 12%, transparent)" }
          : {}),
      }}
      aria-label={`Lifecycle: ${meta.label}${detail ? ` (${detail})` : ""}`}
    >
      <span
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ background: meta.color }}
        aria-hidden
      />
      <span>{meta.label}</span>
      {detail ? <span className="text-muted-foreground font-normal">· {detail}</span> : null}
    </span>
  );
}

function formatDetail(state: LifecycleState, ev?: LifecycleEvent): string {
  if (!ev) return "";
  const age = humanizeAge(ev.timestamp);
  if (state === "applied" && ev.channel) {
    return `via ${ev.channel} · ${age}`;
  }
  return age;
}
