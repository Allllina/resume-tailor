/**
 * ActionQueue + LifecycleStrip — the two "dechromed" header lines from the
 * AI-native inbox design. No boxes; both are inline typographic rows.
 *
 * ActionQueue: "N drafts grouped by resume status — [Review recommended · n]
 * [Needs deep rewrite · n] [Ready to go · n]". These are the product-level
 * post-JD resume statuses; granular workflow states stay inside rows.
 *
 * LifecycleStrip: flat middot-separated text-links (All · Tailored · Applied ·
 * Interviewing · Closed) with mono counts. Active = heavier weight + fg color.
 * Drives the real lifecycle filter (reuses the app's existing filter buckets).
 */
import { CheckCircle2, Eye, PencilLine, type LucideIcon } from "lucide-react";
import type { RunSummary } from "@/lib/api";
import {
  PRODUCT_STATUS_META,
  productStatusForRun,
  type ProductResumeStatus,
} from "./status-meta";

// --- Action queue (product resume status) ---

interface ActionItem {
  status: ProductResumeStatus;
  Icon: LucideIcon;
  label: string;
  color: string;
}

// Product-level status after JD upload: keep this as the main action queue.
// More granular workflow states (Pass 3, blocked, submitted) live inside rows.
const ACTION_ITEMS: ActionItem[] = [
  {
    status: "review_recommended",
    Icon: Eye,
    label: PRODUCT_STATUS_META.review_recommended.label,
    color: PRODUCT_STATUS_META.review_recommended.color,
  },
  {
    status: "needs_deep_rewrite",
    Icon: PencilLine,
    label: PRODUCT_STATUS_META.needs_deep_rewrite.label,
    color: PRODUCT_STATUS_META.needs_deep_rewrite.color,
  },
  {
    status: "ready_to_go",
    Icon: CheckCircle2,
    label: PRODUCT_STATUS_META.ready_to_go.label,
    color: PRODUCT_STATUS_META.ready_to_go.color,
  },
];

export function ActionQueue({
  runs,
  onJumpToProductStatus,
}: {
  runs: RunSummary[];
  onJumpToProductStatus: (status: ProductResumeStatus) => void;
}) {
  const items = ACTION_ITEMS.map((it) => ({
    ...it,
    count: runs.filter((r) => productStatusForRun(r) === it.status).length,
  })).filter((it) => it.count > 0);

  const total = items.reduce((a, b) => a + b.count, 0);

  if (total === 0) {
    return (
      <p className="mt-3 text-xs text-muted-foreground">
        No active drafts in the selected lifecycle bucket.
      </p>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs">
      <span className="text-foreground">
        <span className="font-medium">
          {total} draft{total === 1 ? "" : "s"}
        </span>
        <span className="text-muted-foreground"> grouped by resume status</span>
      </span>
      <span className="text-muted-foreground">·</span>
      {items.map((it) => (
        <button
          key={it.status}
          onClick={() => onJumpToProductStatus(it.status)}
          className="-mx-0.5 inline-flex items-center gap-1.5 rounded px-1 py-0.5 transition hover:bg-foreground/[0.04]"
          style={{ color: it.color }}
        >
          <it.Icon className="h-[11px] w-[11px]" />
          <span className="font-medium">{it.label}</span>
          <span className="opacity-75" style={{ fontFamily: "var(--font-mono)" }}>
            {it.count}
          </span>
        </button>
      ))}
    </div>
  );
}

// --- Lifecycle strip (application-process state) ---

export type LifecycleFilterKey = "all" | "tailored" | "applied" | "interviewing" | "closed";

export const LIFECYCLE_FILTER_LABEL: Record<LifecycleFilterKey, string> = {
  all: "All",
  tailored: "Tailored",
  applied: "Applied",
  interviewing: "Interviewing",
  closed: "Closed",
};

export function LifecycleStrip({
  filter,
  counts,
  onChange,
}: {
  filter: LifecycleFilterKey;
  counts: Record<LifecycleFilterKey, number>;
  onChange: (f: LifecycleFilterKey) => void;
}) {
  const order: LifecycleFilterKey[] = ["all", "tailored", "applied", "interviewing", "closed"];
  return (
    <div className="flex items-center gap-1 border-b border-border px-6 py-1.5 text-[11.5px]">
      <span className="mr-2 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Lifecycle
      </span>
      {order.map((key, i) => {
        const active = filter === key;
        return (
          <span key={key} className="inline-flex items-baseline">
            {i > 0 ? <span className="mx-0.5 text-muted-foreground">·</span> : null}
            <button
              onClick={() => onChange(key)}
              className={`inline-flex items-baseline gap-1 rounded px-1 py-0.5 text-xs transition ${
                active ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
              aria-pressed={active}
            >
              {LIFECYCLE_FILTER_LABEL[key]}
              <span
                className="text-[10.5px] opacity-60"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {counts[key]}
              </span>
            </button>
          </span>
        );
      })}
    </div>
  );
}
