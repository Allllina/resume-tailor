/**
 * DraftRowV2 — the dense, single-line inbox row from the AI-native design.
 *
 * Layout (design spec): [product status dot] · [Company · Role] · [product status] · [fit %] · [→]
 * Stripped vs. the old DraftCard: narration line, lifecycle badge, lift bar,
 * lens chip — those move to the run-detail / agent surfaces.
 *
 * Wired to real RunSummary fields:
 *   - status dot   ← confidence_tier product status, with ui_status only as workflow detail
 *   - title        ← company_hint · role_title_hint
 *   - status text  ← Ready / Review / Rewrite
 *   - fit %        ← resume_match_score (optional; hidden when absent)
 *   - row click    → /run/{run_id}
 */
import { Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import type { RunSummary } from "@/lib/api";
import { LENS_LABELS_ZH } from "@/lib/api";
import { PRODUCT_STATUS_META, STATUS_META, fitColor, productStatusForRun } from "./status-meta";

function titleFor(run: RunSummary): string {
  const parts = [run.company_hint, run.role_title_hint].filter(Boolean);
  if (parts.length > 0) return parts.join(" · ");
  const lens = run.primary_lens ? LENS_LABELS_ZH[run.primary_lens] : "Draft";
  return `${lens} · ${new Date(run.created_at).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })}`;
}

export function DraftRowV2({ run, selected }: { run: RunSummary; selected?: boolean }) {
  const productMeta = PRODUCT_STATUS_META[productStatusForRun(run)];
  const workflowMeta = STATUS_META[run.ui_status];
  const score = run.resume_match_score;

  return (
    <li>
      <Link
        to="/run/$id"
        params={{ id: run.run_id }}
        className={`group grid items-center gap-3.5 rounded-md px-3 py-2 transition hover:bg-accent/50 ${
          selected ? "bg-primary/[0.06]" : ""
        }`}
        style={{ gridTemplateColumns: "10px minmax(0,1fr) 118px 56px 16px" }}
      >
        <span
          className="inline-block h-[7px] w-[7px] rounded-full"
          style={{ background: productMeta.color }}
          title={productMeta.label}
          aria-hidden
        />
        <span className="min-w-0">
          <span className="block truncate text-[13px] text-foreground">{titleFor(run)}</span>
          {run.ui_status === "pending_human_verify" ||
          run.ui_status === "blocked" ||
          run.ui_status === "degraded_no_substance" ? (
            <span className="mt-0.5 inline-flex items-center gap-1 text-[10.5px]" style={{ color: workflowMeta.color }}>
              <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: workflowMeta.color }} />
              {workflowMeta.label}
            </span>
          ) : null}
        </span>
        <span
          className="truncate text-right text-[11px] font-medium"
          style={{ color: productMeta.color }}
          title={`${productMeta.label} · ${new Date(run.created_at).toLocaleString()}`}
        >
          {productMeta.short}
        </span>
        <span
          className="text-right text-[12.5px] font-medium"
          style={{
            fontFamily: "var(--font-mono)",
            color: typeof score === "number" ? fitColor(score) : "var(--muted-foreground)",
          }}
        >
          {typeof score === "number" ? `${Math.round(score)}%` : "—"}
        </span>
        <ChevronRight className="h-3 w-3 text-muted-foreground transition group-hover:translate-x-0.5" />
      </Link>
    </li>
  );
}
