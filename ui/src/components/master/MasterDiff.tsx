import { useMemo } from "react";
import { diffLines } from "diff";

interface MasterDiffProps {
  before: string;
  after: string;
  beforeLabel?: string;
  afterLabel?: string;
  // When the "after" master is known to be a fallback copy of the upload,
  // the empty-diff state should explain WHY rather than implying the AI
  // ran and chose to make no changes.
  fallbackEmpty?: boolean;
}

/**
 * Inline line-level diff of two LaTeX master files. Renders compact
 * red/green stripes inline (not side-by-side) since master.tex content is
 * line-oriented and side-by-side eats horizontal space the /resume layout
 * doesn't have. Stats summary (+N added · -M removed) sits at the top so
 * users see "what changed" without scrolling the diff body.
 */
export function MasterDiff({
  before,
  after,
  beforeLabel = "Original",
  afterLabel = "AI-tailored",
  fallbackEmpty = false,
}: MasterDiffProps) {
  const { parts, added, removed } = useMemo(() => {
    const parts = diffLines(before, after, { ignoreWhitespace: false });
    let added = 0;
    let removed = 0;
    for (const p of parts) {
      const lines = (p.value.match(/\n/g) || []).length || (p.value.length > 0 ? 1 : 0);
      if (p.added) added += lines;
      else if (p.removed) removed += lines;
    }
    return { parts, added, removed };
  }, [before, after]);

  if (added === 0 && removed === 0) {
    return (
      <div
        className={`rounded-md border px-3 py-3 text-xs ${
          fallbackEmpty
            ? "border-attention/40 bg-attention/5 text-foreground"
            : "border-border bg-card text-muted-foreground"
        }`}
      >
        {fallbackEmpty ? (
          <>
            <p className="font-medium text-attention">No diff — AI didn't run.</p>
            <p className="mt-0.5 text-muted-foreground">
              The LLM was unreachable when this master was generated, so the per-lens master is an
              identical copy of your upload. Click <b>Regenerate</b> above to retry once your LLM
              backend is back online.
            </p>
          </>
        ) : (
          <>
            No textual differences between {beforeLabel.toLowerCase()} and {afterLabel.toLowerCase()}.
          </>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2 text-[11px]">
        <span className="text-muted-foreground">
          {beforeLabel} <span className="mx-1">→</span> {afterLabel}
        </span>
        <span className="font-mono">
          <span className="text-verified">+{added}</span>
          <span className="mx-1.5 text-muted-foreground/60">·</span>
          <span className="text-error">-{removed}</span>
        </span>
      </div>
      <div className="max-h-[420px] overflow-auto px-0 py-0 font-mono text-[11px] leading-relaxed">
        {parts.map((p, i) => {
          const lines = p.value.replace(/\n$/, "").split("\n");
          if (lines.length === 1 && lines[0] === "") return null;
          // Marker + color
          const cls = p.added
            ? "bg-verified/8 text-foreground border-l-2 border-verified"
            : p.removed
              ? "bg-error/8 text-foreground border-l-2 border-error"
              : "text-muted-foreground/80 border-l-2 border-transparent";
          const marker = p.added ? "+" : p.removed ? "-" : " ";
          return (
            <div key={i}>
              {lines.map((ln, j) => (
                <div key={j} className={`flex gap-2 ${cls} px-2 py-0.5`}>
                  <span className="select-none text-muted-foreground/50 w-3 shrink-0 text-center">
                    {marker}
                  </span>
                  <span className="break-all whitespace-pre-wrap">{ln || " "}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
