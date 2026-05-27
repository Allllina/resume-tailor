/**
 * Inbox V2 status metadata + grouping order.
 *
 * The design bundle's `STATUS` map (project/lib/shared.jsx) is a verbatim
 * mirror of the real `UiStatus` enum (see src/lib/api.ts) — the design author
 * noted "matches src/components/draft-card.tsx". So we reuse the exact same
 * 7 keys here, no invented statuses.
 *
 * `STATUS_GROUP_ORDER` is the design's "most urgent first" grouping: the
 * user's pending-action states (verify claims, deep rewrite, blocked) lead;
 * ready/submitted trail. Within each group we sort runs oldest-first (= the
 * longest-waiting row sits at the top of every group).
 */
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Eye,
  PencilLine,
  type LucideIcon,
} from "lucide-react";
import type { ConfidenceTier, RunSummary, UiStatus } from "@/lib/api";

export interface StatusMeta {
  /** CSS var driving the dot + group-header tint. */
  color: string;
  Icon: LucideIcon;
  /** Short pill label (matches DraftCard). */
  label: string;
  /** Status-group header label used in the dense list. */
  groupLabel: string;
}

export const STATUS_META: Record<UiStatus, StatusMeta> = {
  pending_human_verify: {
    color: "var(--attention)",
    Icon: Eye,
    label: "Verify claims",
    groupLabel: "Pending claim verification",
  },
  verify: {
    color: "var(--attention)",
    Icon: Clock3,
    label: "Verify",
    groupLabel: "Verify before submit",
  },
  needs_rewrite: {
    color: "var(--error)",
    Icon: PencilLine,
    label: "Deep rewrite",
    groupLabel: "Deep rewrite needed",
  },
  degraded_no_substance: {
    color: "var(--error)",
    Icon: AlertTriangle,
    label: "Quality floor failed",
    groupLabel: "Quality floor failed",
  },
  blocked: {
    color: "var(--error)",
    Icon: AlertTriangle,
    label: "Blocked",
    groupLabel: "Blocked",
  },
  ready: {
    color: "var(--verified)",
    Icon: CheckCircle2,
    label: "Ready",
    groupLabel: "Ready to submit",
  },
  submitted: {
    color: "var(--muted-foreground)",
    Icon: CheckCircle2,
    label: "Submitted",
    groupLabel: "Submitted",
  },
};

// Group render order — "most urgent first" (design's STATUS_GROUP_ORDER).
export const STATUS_GROUP_ORDER: UiStatus[] = [
  "pending_human_verify",
  "verify",
  "needs_rewrite",
  "degraded_no_substance",
  "blocked",
  "ready",
  "submitted",
];

export type ProductResumeStatus = "ready_to_go" | "review_recommended" | "needs_deep_rewrite";

export interface ProductStatusMeta {
  color: string;
  Icon: LucideIcon;
  label: string;
  groupLabel: string;
  short: string;
}

export const PRODUCT_STATUS_META: Record<ProductResumeStatus, ProductStatusMeta> = {
  ready_to_go: {
    color: "var(--verified)",
    Icon: CheckCircle2,
    label: "Ready to go",
    groupLabel: "Ready to submit",
    short: "Ready",
  },
  review_recommended: {
    color: "var(--attention)",
    Icon: Eye,
    label: "Review recommended",
    groupLabel: "Review before submit",
    short: "Review",
  },
  needs_deep_rewrite: {
    color: "var(--error)",
    Icon: PencilLine,
    label: "Needs deep rewrite",
    groupLabel: "Deep rewrite needed",
    short: "Rewrite",
  },
};

export const PRODUCT_STATUS_ORDER: ProductResumeStatus[] = [
  "review_recommended",
  "needs_deep_rewrite",
  "ready_to_go",
];

function productStatusFromConfidence(tier?: ConfidenceTier): ProductResumeStatus | null {
  switch (tier) {
    case "ready_to_go":
      return "ready_to_go";
    case "review_recommended":
      return "review_recommended";
    case "needs_deep_rewrite":
      return "needs_deep_rewrite";
    default:
      return null;
  }
}

/**
 * Product-facing status after a JD is uploaded. This is deliberately narrower
 * than `ui_status`: it answers "what is the resume quality state for this JD?"
 * while `ui_status` answers "what workflow action is currently blocking it?".
 */
export function productStatusForRun(run: RunSummary): ProductResumeStatus {
  const fromTier = productStatusFromConfidence(run.confidence_tier);
  if (fromTier) return fromTier;

  switch (run.ui_status) {
    case "ready":
    case "submitted":
      return "ready_to_go";
    case "needs_rewrite":
    case "degraded_no_substance":
      return "needs_deep_rewrite";
    case "verify":
    case "pending_human_verify":
    case "blocked":
    default:
      return "review_recommended";
  }
}

/**
 * fitColor — single source of truth for score thresholds (per the design +
 * the user's later instruction in chat1.md: "80+ green, 60-80 yellow, rest
 * red"):
 *   ≥ 80  sage / verified
 *   60–79 paper-yellow / attention
 *   < 60  brick-red / error
 */
export function fitColor(n: number): string {
  if (n >= 80) return "var(--verified)";
  if (n >= 60) return "var(--attention)";
  return "var(--error)";
}
