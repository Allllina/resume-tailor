// Shared MethodBadge — surfaces the `_method` provenance marker that every
// LLM-driven backend module (competency, rewrite engine, match matrix,
// dual review) emits per docs/HANDSHAKE.md L0. Renders nothing on the
// happy path ("llm" or "skipped_tier_1"), a labeled pill on partial /
// fallback paths so users see when a section was degraded.
//
// Single source of truth for the "Inferred (...)" vocabulary that
// previously lived as duplicated METHOD_LABEL + METHOD_TONE maps in
// why-expand.tsx (twice — competency + rewrite) and MatchMatrixPanel.tsx.

const LABEL: Record<string, string> = {
  llm: "",
  llm_partial: "Inferred (partial)",
  fallback_no_llm: "Inferred (fallback)",
  skipped_tier_1: "",
};

const TONE: Record<string, string> = {
  llm_partial: "border-attention/40 bg-attention/10 text-attention",
  fallback_no_llm: "border-border bg-muted/40 text-muted-foreground",
};

interface MethodBadgeProps {
  method: string | null | undefined;
}

export function MethodBadge({ method }: MethodBadgeProps) {
  if (!method) return null;
  const label = LABEL[method] ?? "";
  if (!label) return null;
  const tone = TONE[method] ?? "";
  return (
    <span className={`rounded border px-2 py-0.5 font-mono text-[10px] ${tone}`}>
      {label}
    </span>
  );
}
