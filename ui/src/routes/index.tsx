import { createFileRoute, Link } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { useRuns, useUserStatus } from "@/lib/queries";
import type { LifecycleState, RunSummary } from "@/lib/api";
import {
  PRODUCT_STATUS_META,
  PRODUCT_STATUS_ORDER,
  productStatusForRun,
  type ProductResumeStatus,
} from "@/components/inbox/status-meta";
import { DraftRowV2 } from "@/components/inbox/draft-row";
import {
  ActionQueue,
  LifecycleStrip,
  LIFECYCLE_FILTER_LABEL,
  type LifecycleFilterKey,
} from "@/components/inbox/action-queue";
import { InboxV2Conversation } from "@/components/inbox/agent-conversation";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Inbox — Resume Tailor" },
      { name: "description", content: "AI-tailored job applications, ready for review." },
    ],
  }),
  component: Inbox,
});

// Lifecycle filter buckets — same semantics as the previous inbox, with the
// "in_progress" key renamed to "interviewing" (the design's label) so the
// strip reads as application-process state, not workflow state.
const IN_PROGRESS_STATES = new Set<LifecycleState>(["oa", "interview"]);
const CLOSED_STATES = new Set<LifecycleState>(["rejected", "offer", "archived", "dismissed"]);
const RECENT_RUN_LIMIT = 20;

function passesFilter(run: RunSummary, filter: LifecycleFilterKey): boolean {
  const ls = run.lifecycle_state ?? "tailored";
  switch (filter) {
    case "all":
      // Hide archived/dismissed by default — they live under "Closed".
      return ls !== "archived" && ls !== "dismissed";
    case "tailored":
      return ls === "tailored";
    case "applied":
      return ls === "applied";
    case "interviewing":
      return IN_PROGRESS_STATES.has(ls);
    case "closed":
      return CLOSED_STATES.has(ls);
  }
}

function Inbox() {
  const [filter, setFilter] = useState<LifecycleFilterKey>("all");
  const groupRefs = useRef<Partial<Record<ProductResumeStatus, HTMLDivElement | null>>>({});

  const { data, isLoading, isError, error, refetch } = useRuns();
  const { data: status, isLoading: statusLoading } = useUserStatus();

  const allRuns = data?.runs ?? [];
  const filteredRuns = allRuns.filter((r) => passesFilter(r, filter));
  const visibleRuns = filteredRuns.slice(0, RECENT_RUN_LIMIT);
  const hasDrafts = allRuns.length > 0;
  const hiddenRunCount = Math.max(filteredRuns.length - visibleRuns.length, 0);
  const primaryName = status?.profile?.candidate_names?.[0];
  const userInitials = initialsFor(primaryName);

  // Group by the product-facing three-status model. `ui_status` remains a
  // workflow badge inside the row when it carries extra action semantics.
  const byStatus = new Map<ProductResumeStatus, RunSummary[]>();
  for (const r of visibleRuns) {
    const statusKey = productStatusForRun(r);
    const arr = byStatus.get(statusKey) ?? [];
    arr.push(r);
    byStatus.set(statusKey, arr);
  }
  for (const arr of byStatus.values()) {
    arr.sort((a, b) => b.created_at.localeCompare(a.created_at));
  }
  const groups = PRODUCT_STATUS_ORDER.map((s) => ({ status: s, items: byStatus.get(s) ?? [] })).filter(
    (g) => g.items.length > 0,
  );

  const lifecycleCounts: Record<LifecycleFilterKey, number> = {
    all: allRuns.filter((r) => passesFilter(r, "all")).length,
    tailored: allRuns.filter((r) => passesFilter(r, "tailored")).length,
    applied: allRuns.filter((r) => passesFilter(r, "applied")).length,
    interviewing: allRuns.filter((r) => passesFilter(r, "interviewing")).length,
    closed: allRuns.filter((r) => passesFilter(r, "closed")).length,
  };

  function jumpToStatus(s: ProductResumeStatus) {
    groupRefs.current[s]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (statusLoading) {
    return (
      <div className="px-8 pt-10 pb-6">
        <div className="h-8 w-40 animate-pulse rounded bg-muted/60" />
      </div>
    );
  }

  // Full-width two-pane workspace: dense list (left) + agent conversation
  // (right). The app's left sidebar is supplied by AppShell.
  return (
    <div className="grid h-[100dvh] min-h-0 grid-cols-1 lg:h-screen lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
      {/* LEFT — dense run list (stacks above agent on mobile) */}
      <section className="flex min-h-0 flex-col border-r border-border max-lg:border-r-0 max-lg:border-b">
        <header className="border-b border-border bg-background/80 px-4 pb-3 pt-4 backdrop-blur sm:px-6">
          <div className="flex items-end justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                Inbox
              </p>
              <h1 className="text-[22px] text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
                {hasDrafts && primaryName ? `你好,${primaryName}` : "Tailoring queue"}
              </h1>
              <p className="mt-0.5 text-[11.5px] text-muted-foreground">
                {isLoading
                  ? "Loading…"
                  : hasDrafts
                    ? `${visibleRuns.length} shown · ${lifecycleCounts.all} active total`
                    : "Paste a JD in the agent to create your first run."}
              </p>
            </div>
          </div>
          {hasDrafts ? <ActionQueue runs={visibleRuns} onJumpToProductStatus={jumpToStatus} /> : null}
        </header>

        {hasDrafts ? (
          <LifecycleStrip filter={filter} counts={lifecycleCounts} onChange={setFilter} />
        ) : null}
        {hiddenRunCount > 0 ? (
          <div className="border-b border-border bg-muted/20 px-6 py-2 text-[11px] text-muted-foreground">
            Showing the latest {RECENT_RUN_LIMIT} in {LIFECYCLE_FILTER_LABEL[filter]};{" "}
            {hiddenRunCount} older draft{hiddenRunCount === 1 ? "" : "s"} hidden from this MVP view.
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-auto">
          {isLoading ? (
            <LoadingSkeleton />
          ) : isError ? (
            <ErrorState message={error?.message ?? "Failed to load runs."} onRetry={() => void refetch()} />
          ) : !hasDrafts ? (
            <EmptyInbox />
          ) : groups.length === 0 ? (
            <FilteredEmpty filter={filter} onShowAll={() => setFilter("all")} />
          ) : (
            groups.map((g) => {
              const meta = PRODUCT_STATUS_META[g.status];
              return (
                <div
                  key={g.status}
                  ref={(el) => {
                    groupRefs.current[g.status] = el;
                  }}
                >
                  <div className="flex items-center gap-2 px-6 pb-1.5 pt-3.5 text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    <span
                      className="inline-block h-1.5 w-1.5 rounded-full"
                      style={{ background: meta.color }}
                      aria-hidden
                    />
                    <span style={{ color: `color-mix(in oklab, ${meta.color} 70%, var(--foreground))` }}>
                      {meta.groupLabel}
                    </span>
                    <span className="opacity-80" style={{ fontFamily: "var(--font-mono)", letterSpacing: 0, textTransform: "none" }}>
                      · {g.items.length}
                    </span>
                    <span className="ml-1 h-px flex-1 bg-border" />
                  </div>
                  <ul className="m-0 list-none px-3 pb-1">
                    {g.items.map((r) => (
                      <DraftRowV2 key={r.run_id} run={r} />
                    ))}
                  </ul>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* RIGHT — agent conversation + sticky composer */}
      <InboxV2Conversation runs={allRuns} userInitials={userInitials} />
    </div>
  );
}

function initialsFor(name?: string): string {
  if (!name) return "AC";
  const trimmed = name.trim();
  // CJK names: use the last 1–2 characters; otherwise first letters of words.
  if (/[一-鿿]/.test(trimmed)) return trimmed.slice(-2);
  const words = trimmed.split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

function LoadingSkeleton() {
  return (
    <div className="space-y-2 px-3 pt-4 motion-reduce:animate-none" aria-busy="true" aria-label="Loading runs">
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="h-11 animate-pulse rounded-md bg-card/60 motion-reduce:animate-none" />
      ))}
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mx-6 mt-6 rounded-2xl border border-border bg-card/40 px-6 py-8 text-center">
      <p className="text-sm text-error">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 inline-flex h-11 min-h-11 items-center rounded-md border border-border bg-card px-4 text-xs font-medium transition hover:border-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 motion-reduce:transition-none"
      >
        Retry
      </button>
    </div>
  );
}

function EmptyInbox() {
  return (
    <div className="mx-6 mt-8 rounded-2xl border border-dashed border-border bg-card/40 px-6 py-12 text-center">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles className="h-4 w-4" />
      </span>
      <h2 className="mt-4 text-xl text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
        I'm watching, no JDs yet.
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        Paste a JD in the tailoring agent below, or finish the 2-minute setup so I can use your real
        experience bank.
      </p>
      <Link
        to="/setup"
        className="group mt-5 inline-flex h-11 min-h-11 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-medium text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 motion-reduce:transition-none"
      >
        Get started
        <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
      </Link>
    </div>
  );
}

function FilteredEmpty({
  filter,
  onShowAll,
}: {
  filter: LifecycleFilterKey;
  onShowAll: () => void;
}) {
  return (
    <div className="mx-6 mt-6 rounded-2xl border border-dashed border-border bg-card/40 px-6 py-10 text-center">
      <p className="text-sm text-muted-foreground">
        No drafts in <span className="text-foreground">{LIFECYCLE_FILTER_LABEL[filter]}</span> right now.
      </p>
      <button
        onClick={onShowAll}
        className="mt-3 inline-flex h-8 items-center rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
      >
        Show all
      </button>
    </div>
  );
}
