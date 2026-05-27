import { createFileRoute } from "@tanstack/react-router";
import { Fragment, useState } from "react";
import { ChevronDown, ChevronUp, Library, X } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ExperiencesUpload } from "@/components/upload/ExperiencesUpload";
import { ScoringStatusPill } from "@/components/upload/ScoringStatusPill";
import { useDeleteExperience, useUserStatus } from "@/lib/queries";
import {
  LENSES,
  LENS_LABELS_ZH,
  type AiFluencyLevel,
  type ExperienceSummary,
  type FitLevel,
  type Lens,
  type RecognitionLevel,
} from "@/lib/api";

export const Route = createFileRoute("/experiences")({
  head: () => ({
    meta: [{ title: "Experiences — Resume Tailor" }],
  }),
  component: ExperiencesPage,
});

const RECOGNITION_LABELS: Record<string, string> = {
  consulting: "consulting",
  finance: "finance",
  internet_strategic: "internet · strategic",
  internet_operational: "internet · ops",
  internet_data: "internet · data",
  education: "education",
  market_research: "market research",
  brand_marketing: "brand & mktg",
};

const RECOGNITION_COLOR: Record<RecognitionLevel, string> = {
  high: "var(--verified)",
  medium: "var(--primary)",
  low: "var(--muted-foreground)",
  none: "var(--muted-foreground)",
};

const FLUENCY_COLOR: Record<AiFluencyLevel, string> = {
  high: "var(--verified)",
  moderate: "var(--primary)",
  low: "var(--attention)",
  none: "var(--muted-foreground)",
};

const LENS_SHORT_LABELS: Record<Lens, string> = {
  A_strategy_research: "A · Strategy",
  B_data_analytics: "B · Data",
  C_product_ops: "C · Product",
  D_finance_markets: "D · Finance",
  HC_human_capital: "HC · Talent",
};

function ExperiencesPage() {
  const { data: status, isLoading } = useUserStatus();
  const items: ExperienceSummary[] = status?.experiences ?? [];
  const total = status?.experience_count ?? 0;
  const scored = status?.experiences_scored_count ?? 0;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <header>
        <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
          Source pool · {total} experiences · {scored}/{Math.max(total, 1)} scored
        </p>
        <h1
          className="mt-1 text-3xl text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Experience bank
        </h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Each experience is scored against the five role lenses — strategy, data, product, finance,
          and talent. Stronger coverage means better evidence selection when the rewrite engine
          routes a JD to that lens.
        </p>
      </header>

      <div className="mt-8">
        {isLoading && items.length === 0 ? (
          <div className="h-40 animate-pulse rounded-lg bg-card/50" />
        ) : items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-card/40 px-6 py-10">
            <div className="mx-auto max-w-md text-center">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Library className="h-4 w-4" />
              </span>
              <p className="mt-3 text-sm font-medium text-foreground">No experiences yet</p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                Upload past role write-ups, project briefs, or internship reports — one file per
                role works best. Each is auto-scored against the five lenses so the rewrite engine
                can pull the strongest evidence for any JD. Supports{" "}
                <span className="font-mono">.md</span> ·{" "}
                <span className="font-mono">.tex</span> ·{" "}
                <span className="font-mono">.docx</span> ·{" "}
                <span className="font-mono">.pdf</span> — up to 2 MB each, 30 at once.
              </p>
              <div className="mt-5">
                <ExperiencesUpload />
              </div>
            </div>
          </div>
        ) : (
          <>
            <ExperienceCoverageTable items={items} />
            <div className="mt-6">
              <p className="mb-2 text-xs text-muted-foreground">Add more experiences</p>
              <ExperiencesUpload compact />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ExperienceCoverageTable({ items }: { items: ExperienceSummary[] }) {
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full table-fixed border-collapse">
          <colgroup>
            <col className="w-[34%]" />
            {LENSES.map((lens) => (
              <col key={lens} className="w-[11%]" />
            ))}
            <col className="w-[11%]" />
          </colgroup>
          <thead>
            <tr>
              <th className="border-b border-border py-2 pr-4 text-left text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Experience
              </th>
              {LENSES.map((lens) => (
                <th
                  key={lens}
                  className="border-b border-border px-2 py-2 text-center text-[11px] font-medium text-muted-foreground"
                >
                  {lensLabel(lens)}
                </th>
              ))}
              <th className="border-b border-border py-2 pl-3 text-right text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <ExperienceRow key={item.id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-muted-foreground">
        <span className="text-[10px] uppercase tracking-[0.16em]">Coverage</span>
        {[
          ["Low", 0.25],
          ["Medium", 0.5],
          ["Strong", 0.75],
          ["Core", 1],
        ].map(([label, value]) => (
          <span key={label as string} className="inline-flex items-center gap-2">
            <span
              className="h-1.5 w-6 rounded-full"
              style={{ background: heatBackground(value as number) }}
            />
            {label}
          </span>
        ))}
      </div>
    </>
  );
}

function ExperienceRow({ item }: { item: ExperienceSummary }) {
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const del = useDeleteExperience();

  const handleDelete = () => {
    del.mutate(item.id, {
      onSuccess: () => {
        toast.success("Experience deleted");
        setConfirmDelete(false);
      },
      onError: (err) => {
        toast.error((err as Error).message);
      },
    });
  };

  const hasDetails =
    item.scoring_status === "done" &&
    (item.recognition_per_industry || item.vertical_fit_per_lens || item.ai_digital_fluency);

  return (
    <Fragment>
      <tr className="border-b border-border align-middle transition hover:bg-card/45">
        <td className="py-4 pr-4">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <p className="truncate text-sm font-medium text-foreground">
                {displayName(item.file_name || item.id)}
              </p>
              <ScoringStatusPill status={item.scoring_status} />
              {item.scoring_fallback ? (
                <span
                  className="inline-flex h-5 shrink-0 items-center rounded-full bg-attention/15 px-2 text-[10px] font-medium text-attention"
                  title="Fallback scoring was used because the scorer was unavailable."
                >
                  fallback
                </span>
              ) : null}
            </div>
            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
              {item.scored_at
                ? `scored ${humanizeAge(item.scored_at)}`
                : item.uploaded_at
                  ? `uploaded ${humanizeAge(item.uploaded_at)}`
                  : item.id}
            </p>
          </div>
        </td>
        {LENSES.map((lens) => (
          <HeatCell key={lens} value={fitScore(item.vertical_fit_per_lens?.[lens])} />
        ))}
        <td className="py-4 pl-3">
          <div className="flex justify-end gap-1">
            <button
              disabled={!hasDetails}
              onClick={() => setExpanded((e) => !e)}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              disabled={del.isPending}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition hover:bg-error/10 hover:text-error disabled:opacity-50"
              aria-label="Delete"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </td>
      </tr>

      {expanded && hasDetails ? (
        <tr className="border-b border-border">
          <td colSpan={LENSES.length + 2} className="bg-card/35 px-3 py-3">
            <ExpandedDetails item={item} />
          </td>
        </tr>
      ) : null}

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this experience?</AlertDialogTitle>
            <AlertDialogDescription>
              Tailoring runs that referenced it stay intact. The file{" "}
              <span className="font-mono text-xs">{item.file_name}</span> will be removed from
              your bank.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-error text-error-foreground hover:bg-error/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Fragment>
  );
}

function HeatCell({ value }: { value: number | null }) {
  return (
    <td className="px-2 py-4 text-center align-middle">
      {value === null ? (
        <span className="font-mono text-xs text-muted-foreground">—</span>
      ) : (
        <>
          <div
            className={`font-mono text-xs leading-none ${
              value >= 0.5 ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {value.toFixed(2)}
          </div>
          <div className="mt-2 h-1 rounded-full bg-muted">
            <div
              className="h-full rounded-full"
              style={{ width: `${value * 100}%`, background: heatBackground(value) }}
            />
          </div>
        </>
      )}
    </td>
  );
}

function ExpandedDetails({ item }: { item: ExperienceSummary }) {
  return (
    <div className="grid gap-4 text-xs md:grid-cols-[1fr_1fr_auto]">
      {item.recognition_per_industry ? (
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Recognition
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(item.recognition_per_industry).map(([key, val]) => (
              <Pill
                key={key}
                label={`${RECOGNITION_LABELS[key] ?? key}=${val}`}
                color={RECOGNITION_COLOR[val] ?? "var(--muted-foreground)"}
                dim={val === "low" || val === "none"}
              />
            ))}
          </div>
        </div>
      ) : null}
      {item.vertical_fit_per_lens ? (
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Lens fit
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(item.vertical_fit_per_lens).map(([key, val]) => (
              <Pill
                key={key}
                label={`${lensLabel(key as Lens)}=${val}`}
                color={fitColor(val)}
                dim={val === "weak" || val === "missing"}
              />
            ))}
          </div>
        </div>
      ) : null}
      {item.ai_digital_fluency ? (
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            AI / digital fluency
          </p>
          <div className="mt-2">
            <Pill
              label={item.ai_digital_fluency}
              color={FLUENCY_COLOR[item.ai_digital_fluency]}
              dim={item.ai_digital_fluency === "low" || item.ai_digital_fluency === "none"}
            />
          </div>
        </div>
      ) : null}
      {item.scoring_fallback ? (
        <p className="md:col-span-3 text-[11px] text-attention-foreground/80">
          Note: fallback scoring was used because the LLM scorer was unavailable; values are
          conservative defaults.
        </p>
      ) : null}
    </div>
  );
}

function Pill({
  label,
  color,
  dim,
}: {
  label: string;
  color: string;
  dim?: boolean;
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium"
      style={{
        color,
        background: `color-mix(in oklab, ${color} ${dim ? 6 : 12}%, transparent)`,
        opacity: dim ? 0.75 : 1,
      }}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function fitScore(value: FitLevel | undefined): number | null {
  if (!value) return null;
  return (
    {
      core: 1,
      adjacent: 0.68,
      weak: 0.35,
      missing: 0.08,
    } satisfies Record<FitLevel, number>
  )[value];
}

function fitColor(value: FitLevel): string {
  return (
    {
      core: "var(--verified)",
      adjacent: "var(--primary)",
      weak: "var(--attention)",
      missing: "var(--muted-foreground)",
    } satisfies Record<FitLevel, string>
  )[value];
}

function heatBackground(value: number): string {
  const pct = Math.round(12 + Math.max(0, Math.min(1, value)) * 66);
  return `color-mix(in oklab, var(--verified) ${pct}%, transparent)`;
}

function lensLabel(lens: Lens): string {
  return LENS_SHORT_LABELS[lens] ?? LENS_LABELS_ZH[lens];
}

function displayName(name: string): string {
  return name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
}

function humanizeAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 120_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)} min ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)} hours ago`;
  if (ms < 86_400_000 * 7) return `${Math.floor(ms / 86_400_000)} days ago`;
  return new Date(iso).toLocaleDateString();
}
