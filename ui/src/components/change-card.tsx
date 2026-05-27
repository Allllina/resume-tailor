import { useState } from "react";
import { Check, ChevronRight, Pencil, RotateCcw } from "lucide-react";

interface Props {
  title: string;
  before: string;
  after: string;
  note?: string;
}

export function ChangeCard({ title, before, after, note }: Props) {
  const [open, setOpen] = useState(false);
  const [kept, setKept] = useState(false);

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="block w-full p-4 text-left transition hover:bg-accent/30"
        aria-expanded={open}
      >
        <div className="flex items-start gap-2">
          <ChevronRight
            className={`mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground transition ${
              open ? "rotate-90" : ""
            }`}
          />
          <div className="min-w-0 flex-1">
            <h4 className="truncate text-sm font-medium text-foreground">{title}</h4>
            {note ? <p className="mt-0.5 text-xs text-muted-foreground">{note}</p> : null}

            {!open ? (
              <p className="mt-2 truncate font-mono text-[11px] text-muted-foreground">
                <span className="line-through opacity-70">{before}</span>
                <span className="mx-1.5 text-foreground/40">→</span>
                <span className="text-foreground/85">{after}</span>
              </p>
            ) : null}
          </div>
          {kept ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-verified/15 px-2 py-0.5 text-[10px] text-verified">
              <Check className="h-3 w-3" /> kept
            </span>
          ) : null}
        </div>
      </button>

      {open ? (
        <div className="border-t border-border bg-muted/30 px-4 py-4 space-y-4">
          <div className="space-y-1.5 font-mono text-[12px]">
            <div className="flex items-start gap-2">
              <span className="select-none text-muted-foreground">−</span>
              <span className="break-all text-muted-foreground line-through opacity-70">
                {before}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="select-none text-verified">+</span>
              <span className="break-all text-foreground">{after}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setKept(true)}
              disabled={kept}
              className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs transition hover:border-foreground/20 disabled:opacity-50 disabled:hover:border-border"
            >
              <Check className="h-3 w-3 text-verified" />
              Looks good
            </button>
            <button className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs transition hover:border-foreground/20">
              <RotateCcw className="h-3 w-3" />
              Redo
            </button>
            <button className="inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-xs text-muted-foreground transition hover:text-foreground">
              <Pencil className="h-3 w-3" />
              Edit manually
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
