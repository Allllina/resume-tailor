// Wave 4 D.5 — Pass 3 user-trust surface.
//
// Renders when a run's verdict is `partial_pending_user`. The user reads
// each unsourced claim and decides Approve / Reject / Edit. Decisions are
// recorded in `runs/<id>/verification_log.json`; once every unsourced claim
// has been decided, the run flips to `complete` and the Submit gate opens.
//
// MVP scope: decisions are recorded but the .tex is NOT auto-patched on
// reject/edit (user takes responsibility for what they submit). A follow-up
// can wire deterministic claim-removal patches + LaTeX re-render.
import { useState } from "react";
import { Check, Loader2, Pencil, X } from "lucide-react";
import { usePass3, useVerifyClaim } from "@/lib/queries";
import type {
  Pass3Bullet,
  Pass3UnsourcedClaim,
  VerifyClaimDecision,
  VerificationLogEvent,
} from "@/lib/api";

interface Props {
  runId: string;
}

interface FlatClaim {
  bullet_id: string;
  claim_index: number;
  claim: Pass3UnsourcedClaim;
  decided?: VerificationLogEvent;
}

function flattenClaims(
  bullets: Pass3Bullet[],
  events: VerificationLogEvent[],
): FlatClaim[] {
  // Take the latest decision per (bullet_id, claim_index) pair — the API
  // appends every decision (so revisits are auditable) but the panel only
  // surfaces the user's most recent intent.
  const latestByKey = new Map<string, VerificationLogEvent>();
  for (const e of events) {
    latestByKey.set(`${e.bullet_id}#${e.claim_index}`, e);
  }
  const flat: FlatClaim[] = [];
  for (const b of bullets) {
    for (let i = 0; i < b.unsourced_claims.length; i++) {
      flat.push({
        bullet_id: b.bullet_id,
        claim_index: i,
        claim: b.unsourced_claims[i],
        decided: latestByKey.get(`${b.bullet_id}#${i}`),
      });
    }
  }
  return flat;
}

export function Pass3VerifyPanel({ runId }: Props) {
  const { data, isLoading, isError, error, refetch } = usePass3(runId);

  if (isLoading) {
    return (
      <section
        className="rounded-xl border border-attention/40 bg-attention/5 px-5 py-6 motion-reduce:animate-none"
        aria-busy="true"
        aria-label="Loading Pass 3 review"
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
          Loading truthfulness review…
        </div>
        <div className="mt-4 space-y-2">
          <div className="h-10 animate-pulse rounded-md bg-background/60 motion-reduce:animate-none" />
          <div className="h-10 animate-pulse rounded-md bg-background/60 motion-reduce:animate-none" />
        </div>
      </section>
    );
  }
  if (isError || !data) {
    // Pass 3 detail file may be missing on edge cases (FS error during
    // late_feedback persistence). Surface a degraded notice with no
    // per-claim buttons so the user knows what's wrong without seeing a
    // hard failure.
    const status = (error as { status?: number } | null)?.status;
    if (status === 404) {
      return (
        <section className="rounded-xl border border-attention/40 bg-attention/5 px-5 py-4">
          <h3 className="text-sm font-semibold text-foreground">
            Pass 3 detail unavailable
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            The verifier flagged this run but the per-claim breakdown could
            not be loaded. Inspect the .tex by hand before submitting.
          </p>
        </section>
      );
    }
    return (
      <section className="rounded-xl border border-error/30 bg-error/5 px-5 py-4">
        <h3 className="text-sm font-semibold text-foreground">Could not load Pass 3 review</h3>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {(error as Error)?.message ?? "Unknown error"}
        </p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-3 inline-flex h-11 min-h-11 items-center rounded-md border border-border bg-card px-4 text-xs font-medium transition hover:border-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 motion-reduce:transition-none"
        >
          Retry
        </button>
      </section>
    );
  }

  const flat = flattenClaims(data.bullets, data.verification_log.events);
  if (flat.length === 0) return null;

  const decidedCount = flat.filter((c) => c.decided).length;
  const total = flat.length;
  const allDecided = decidedCount >= total;

  return (
    <section
      className="rounded-xl border border-attention/40 bg-attention/5 overflow-hidden"
      aria-label="Pass 3 truthfulness review"
    >
      <header className="flex flex-wrap items-center gap-3 border-b border-attention/30 bg-attention/10 px-5 py-3.5">
        <h2
          className="text-base font-semibold text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          逐条核实 · Pass 3
        </h2>
        <span className="font-mono text-[10px] text-muted-foreground">
          Verify each unsourced claim before submit
        </span>
        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-[11px] font-medium ${
            allDecided
              ? "bg-verified/15 text-verified-foreground"
              : "bg-attention/15 text-attention-foreground"
          }`}
        >
          {decidedCount} / {total} decided
        </span>
      </header>

      <ol className="divide-y divide-attention/20">
        {flat.map((c) => (
          <ClaimRow
            key={`${c.bullet_id}#${c.claim_index}`}
            runId={runId}
            entry={c}
          />
        ))}
      </ol>

      {allDecided ? (
        <p className="border-t border-attention/30 bg-verified/5 px-5 py-3 text-xs text-verified-foreground">
          ✓ All claims decided — the run is unlocked. The .tex is unchanged;
          edit it by hand on the Tex preview tab if your decisions imply
          text changes.
        </p>
      ) : null}
    </section>
  );
}

/* --------------------------------- Rows --------------------------------- */

function ClaimRow({ runId, entry }: { runId: string; entry: FlatClaim }) {
  const verify = useVerifyClaim();
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState("");

  const submit = (decision: VerifyClaimDecision, editedText?: string) => {
    verify.mutate({
      id: runId,
      body: {
        bullet_id: entry.bullet_id,
        claim_index: entry.claim_index,
        decision,
        ...(editedText ? { edited_text: editedText } : {}),
      },
    });
  };

  const decided = entry.decided;
  const claim = entry.claim;

  return (
    <li className="px-5 py-4">
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-attention/15 px-1.5 text-[10px] font-mono text-attention-foreground"
          aria-hidden
        >
          {entry.bullet_id}
        </span>
        <div className="flex-1">
          <p
            className={`text-sm leading-relaxed ${
              decided ? "text-muted-foreground line-through" : "text-foreground"
            }`}
          >
            {claim.claim}
          </p>
          {claim.rationale ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {claim.rationale}
            </p>
          ) : null}
        </div>
      </div>

      {decided ? (
        <DecidedRow event={decided} />
      ) : editing ? (
        <div className="mt-3 space-y-2">
          <textarea
            value={edited}
            onChange={(e) => setEdited(e.target.value)}
            placeholder="Rewrite this claim with truthful, source-backed wording…"
            rows={3}
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
          />
          <div className="flex items-center gap-2">
            <button
              disabled={!edited.trim() || verify.isPending}
              onClick={() => submit("edit", edited)}
              className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" /> Save edit
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setEdited("");
              }}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:bg-muted"
            >
              <X className="h-3.5 w-3.5" /> Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            disabled={verify.isPending}
            onClick={() => submit("approve")}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-verified/40 bg-verified/10 px-3 text-xs font-medium text-verified-foreground transition hover:bg-verified/20 disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" /> Approve
          </button>
          <button
            disabled={verify.isPending}
            onClick={() => submit("reject")}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-error/40 bg-error/5 px-3 text-xs font-medium text-error transition hover:bg-error/10 disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5" /> Reject
          </button>
          <button
            disabled={verify.isPending}
            onClick={() => setEditing(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:bg-muted disabled:opacity-50"
          >
            <Pencil className="h-3.5 w-3.5" /> Edit
          </button>
          {verify.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : null}
        </div>
      )}
    </li>
  );
}

function DecidedRow({ event }: { event: VerificationLogEvent }) {
  const label =
    event.decision === "approve"
      ? "Approved"
      : event.decision === "reject"
        ? "Rejected"
        : "Edited";
  const when = (() => {
    try {
      return new Date(event.decided_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  })();
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <span className="inline-flex h-6 items-center gap-1.5 rounded-md bg-muted px-2 font-medium">
        <Check className="h-3 w-3" /> {label} {when ? `· ${when}` : ""}
      </span>
      {event.edited_text ? (
        <span className="text-foreground/70">→ "{event.edited_text}"</span>
      ) : null}
      {event.note ? <span className="italic">"{event.note}"</span> : null}
    </div>
  );
}
