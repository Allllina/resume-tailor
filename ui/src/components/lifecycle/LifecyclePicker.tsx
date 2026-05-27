/**
 * LifecyclePicker — horizontal pill row showing the current lifecycle state
 * plus buttons for each valid next transition. Renders at the top of the
 * DraftReview page header.
 *
 * NOTE: VALID_TRANSITIONS below mirrors the backend's
 *   packages/harness/src/harness/lifecycle/state_machine.py
 * map. Keep in sync. The backend remains the source of truth — invalid
 * transitions surface as a 400 from PATCH /api/runs/{id}/lifecycle and we
 * show the error inline.
 */
import { useState } from "react";
import { Loader2 } from "lucide-react";
import type { LifecycleState } from "@/lib/api";
import { usePatchRunLifecycle } from "@/lib/queries";
import { LifecycleBadge } from "./LifecycleBadge";

// Mirrors backend VALID_TRANSITIONS — see file header.
const VALID_TRANSITIONS: Record<LifecycleState, LifecycleState[]> = {
  tailored: ["applied", "dismissed", "archived"],
  applied: ["oa", "interview", "rejected", "offer", "archived", "tailored"],
  oa: ["interview", "rejected", "offer", "archived", "applied"],
  interview: ["rejected", "offer", "archived", "oa"],
  rejected: ["archived"],
  offer: ["archived"],
  archived: ["tailored"],
  dismissed: [],
};

const ACTION_LABEL: Record<LifecycleState, string> = {
  tailored: "Move back to tailored",
  applied: "I submitted this",
  oa: "Got OA",
  interview: "Got interview",
  rejected: "Rejected",
  offer: "Got offer",
  archived: "Archive",
  dismissed: "Dismiss",
};

interface Props {
  runId: string;
  current: LifecycleState;
  /** Last lifecycle event (passed through to the badge). */
  lastEvent?: import("@/lib/api").LifecycleEvent;
}

export function LifecyclePicker({ runId, current, lastEvent }: Props) {
  const mutation = usePatchRunLifecycle();
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const transitions = VALID_TRANSITIONS[current] ?? [];

  const onClick = (target: LifecycleState) => {
    setError(null);
    setToast(null);
    mutation.mutate(
      { id: runId, body: { state: target } },
      {
        onSuccess: () => {
          setToast(`Moved to ${target}`);
          setTimeout(() => setToast(null), 2000);
        },
        onError: (e: unknown) => {
          const msg = e instanceof Error ? e.message : "Update failed";
          setError(msg);
        },
      },
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <LifecycleBadge state={current} lastEvent={lastEvent} />

      {transitions.length > 0 ? <span className="text-muted-foreground text-xs">→</span> : null}

      <div className="flex flex-wrap gap-1.5">
        {transitions.map((target) => (
          <button
            key={target}
            onClick={() => onClick(target)}
            disabled={mutation.isPending}
            className="inline-flex h-7 items-center rounded-md border border-border bg-card px-2.5 text-xs font-medium text-foreground/85 transition hover:border-foreground/20 hover:bg-accent disabled:opacity-50"
          >
            {mutation.isPending && mutation.variables?.body.state === target ? (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            ) : null}
            {ACTION_LABEL[target]}
          </button>
        ))}
      </div>

      {toast ? (
        <span className="text-xs text-verified" role="status">
          {toast}
        </span>
      ) : null}
      {error ? (
        <span className="text-xs text-error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
