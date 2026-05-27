import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Eye,
  PencilLine,
  Send,
  X,
} from "lucide-react";
import { LifecycleBadge } from "@/components/lifecycle/LifecycleBadge";
import type { LifecycleState, UiStatus } from "@/lib/api";

// Status derivation (computed by backend per ARCHITECTURE.md §7a + Wave 4):
//   confidence_tier=ready_to_go             → "ready"                 (green ✦)
//   confidence_tier=review_recommended      → "verify"                (amber ◷)
//   confidence_tier=needs_deep_rewrite      → "needs_rewrite"         (orange ✎ — Tier 2/3 helps)
//   verdict=partial_pending_user (W4 D.5)   → "pending_human_verify"  (amber 👁 — per-claim review)
//   verdict=failed                          → "blocked"               (red ⚠)
//   verdict=degraded_no_substance (Gate 1)  → "degraded_no_substance" (red ！ — quality floor failed)
//   submit_audit.outcome=submitted          → "submitted"             (gray ✓)
type Status = UiStatus;

const STATUS_META: Record<Status, { color: string; Icon: typeof CheckCircle2; label: string }> = {
  ready: { color: "var(--verified)", Icon: CheckCircle2, label: "Ready" },
  verify: { color: "var(--attention)", Icon: Clock3, label: "Verify" },
  needs_rewrite: { color: "var(--error)", Icon: PencilLine, label: "Deep rewrite" },
  blocked: { color: "var(--error)", Icon: AlertTriangle, label: "Blocked" },
  submitted: { color: "var(--muted-foreground)", Icon: CheckCircle2, label: "Submitted" },
  pending_human_verify: {
    color: "var(--attention)",
    Icon: Eye,
    label: "Verify claims",
  },
  degraded_no_substance: {
    color: "var(--error)",
    Icon: AlertTriangle,
    label: "Quality floor failed",
  },
};

interface Props {
  id: string;
  status: Status;
  title: string;
  location: string;
  narration: string;
  lifecycleState?: LifecycleState;
}

export function DraftCard({ id, status, title, location, narration, lifecycleState }: Props) {
  const meta = STATUS_META[status];
  const StatusIcon = meta.Icon;
  const isSubmitted = status === "submitted";

  return (
    <article
      className="group relative rounded-lg border border-border bg-card p-5 pl-6 transition hover:border-foreground/15"
      style={{ boxShadow: isSubmitted ? "none" : "0 1px 0 rgba(0,0,0,0.02)" }}
    >
      <span
        className="absolute left-0 top-4 bottom-4 w-[3px] rounded-full"
        style={{ background: meta.color }}
        aria-hidden
      />

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <h3
              className={`text-base font-medium ${
                isSubmitted ? "text-muted-foreground" : "text-foreground"
              }`}
            >
              {title}
            </h3>
            {location ? <span className="text-xs text-muted-foreground">· {location}</span> : null}
          </div>
          {lifecycleState ? (
            <div className="mt-2">
              <LifecycleBadge state={lifecycleState} size="sm" />
            </div>
          ) : null}
        </div>
        <span
          className="inline-flex h-7 shrink-0 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[11px] font-medium"
          style={{ color: meta.color }}
        >
          <StatusIcon className="h-3.5 w-3.5" />
          {meta.label}
        </span>
      </header>

      <p
        className={`mt-2 text-sm leading-relaxed ${
          isSubmitted ? "text-muted-foreground" : "text-foreground/85"
        }`}
      >
        {narration}
      </p>

      <div className="mt-4 grid gap-3 border-t border-border pt-4 md:grid-cols-3">
        <DiagnosticCell
          label="Probability lift"
          value={status === "ready" ? "42% → 64%" : "31% → 52%"}
          detail={status === "ready" ? "Stronger JD keyword coverage." : "Improves lifecycle + AI ops framing."}
        />
        <DiagnosticCell
          label="Remaining gap"
          value={status === "ready" ? "SQL depth" : "AIGC metrics"}
          detail={status === "ready" ? "Evidence still thin for advanced analytics." : "Needs user-confirmed usage or impact data."}
        />
        <DiagnosticCell
          label="Bridge"
          value={status === "ready" ? "Add project scope" : "Verify claims"}
          detail={status === "ready" ? "Explain ownership and business result." : "Decide whether the inferred claims are safe."}
        />
      </div>

      {!isSubmitted && (
        <div className="mt-4 flex items-center gap-2">
          <button
            disabled
            title="Submit channels arrive in Wave 3"
            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-muted px-3 text-xs font-medium text-muted-foreground cursor-not-allowed"
          >
            <Send className="h-3.5 w-3.5" />
            Submit
          </button>
          <Link
            to="/run/$id"
            params={{ id }}
            className="flex h-8 items-center rounded-md border border-border px-3 text-xs font-medium transition hover:bg-accent"
          >
            Review
          </Link>
          <button
            className="ml-auto flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-muted"
            aria-label="Dismiss"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </article>
  );
}

function DiagnosticCell({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-md bg-muted/35 p-3">
      <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{detail}</p>
    </div>
  );
}
