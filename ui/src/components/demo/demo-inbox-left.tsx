/**
 * DemoInboxLeft — the dense, status-grouped left list pane.
 *
 * This REUSES the real inbox components verbatim (DraftRowV2, ActionQueue,
 * LifecycleStrip, STATUS_META, STATUS_GROUP_ORDER) — they're pure/presentational
 * and take RunSummary[] directly, so no clone is needed. We only re-implement
 * the tiny grouping + header shell that index.tsx wraps them in (index.tsx's
 * Inbox component is query-driven and not cleanly script-feedable). Markup +
 * classes are copied from src/routes/index.tsx so it's 1:1 with production.
 */
import {
  PRODUCT_STATUS_META,
  PRODUCT_STATUS_ORDER,
  productStatusForRun,
  type ProductResumeStatus,
} from "@/components/inbox/status-meta";
import { DraftRowV2 } from "@/components/inbox/draft-row";
import { ActionQueue, LifecycleStrip } from "@/components/inbox/action-queue";
import type { RunSummary } from "@/lib/api";
import { useLang } from "@/lib/lang-context";

export function DemoInboxLeft({ runs }: { runs: RunSummary[] }) {
  const zh = useLang() === "zh";
  const byStatus = new Map<ProductResumeStatus, RunSummary[]>();
  for (const r of runs) {
    const status = productStatusForRun(r);
    const arr = byStatus.get(status) ?? [];
    arr.push(r);
    byStatus.set(status, arr);
  }
  for (const arr of byStatus.values()) {
    arr.sort((a, b) => a.created_at.localeCompare(b.created_at));
  }
  const groups = PRODUCT_STATUS_ORDER.map((s) => ({ status: s, items: byStatus.get(s) ?? [] })).filter(
    (g) => g.items.length > 0,
  );

  const lifecycleCounts = {
    all: runs.length,
    tailored: runs.filter((r) => (r.lifecycle_state ?? "tailored") === "tailored").length,
    applied: runs.filter((r) => r.lifecycle_state === "applied").length,
    interviewing: runs.filter((r) => r.lifecycle_state === "interview" || r.lifecycle_state === "oa").length,
    closed: 0,
  };

  return (
    <section className="flex min-h-0 flex-col border-r border-border">
      <header className="border-b border-border bg-background/80 px-6 pb-3 pt-4 backdrop-blur">
        <div className="flex items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Inbox
            </p>
            <h1 className="text-[22px] text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
              {zh ? "你好，Alina" : "Hello, Alina"}
            </h1>
            <p className="mt-0.5 text-[11.5px] text-muted-foreground">
              {lifecycleCounts.all} active draft{lifecycleCounts.all === 1 ? "" : "s"}
            </p>
          </div>
        </div>
        <ActionQueue runs={runs} onJumpToProductStatus={() => {}} />
      </header>

      <LifecycleStrip filter="all" counts={lifecycleCounts} onChange={() => {}} />

      <div className="min-h-0 flex-1 overflow-hidden">
        {groups.map((g) => {
          const meta = PRODUCT_STATUS_META[g.status];
          return (
            <div key={g.status}>
              <div className="flex items-center gap-2 px-6 pb-1.5 pt-3.5 text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full"
                  style={{ background: meta.color }}
                  aria-hidden
                />
                <span style={{ color: `color-mix(in oklab, ${meta.color} 70%, var(--foreground))` }}>
                  {meta.groupLabel}
                </span>
                <span
                  className="opacity-80"
                  style={{ fontFamily: "var(--font-mono)", letterSpacing: 0, textTransform: "none" }}
                >
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
        })}
      </div>
    </section>
  );
}
