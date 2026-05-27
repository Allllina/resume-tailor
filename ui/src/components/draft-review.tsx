import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import {
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Send,
} from "lucide-react";
import { ChangeCard } from "@/components/change-card";
import { DegradedSubstanceBanner } from "@/components/degraded-substance-banner";
import { SubSkillErrorBanner } from "@/components/SubSkillErrorBanner";
import { FitDiagnosisPostRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPostRewritePanel";
import { FitDiagnosisPreRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPreRewritePanel";
import { LifecyclePicker } from "@/components/lifecycle/LifecyclePicker";
import { Pass3VerifyPanel } from "@/components/pass3-verify-panel";
import { WhyExpand } from "@/components/why-expand";
import { useMasters, useRun } from "@/lib/queries";
import { getUserId } from "@/lib/user";
import {
  getPdfUrl,
  getTexUrl,
  type DegradationEvent,
  type Lens,
  type MastersResponse,
  type RunDetail,
} from "@/lib/api";

interface Props {
  draftId: string;
}

const LENS_LABEL: Record<Lens, string> = {
  A_strategy_research: "A 战略研究",
  B_data_analytics: "B 数据分析",
  C_product_ops: "C 产品运营",
  D_finance_markets: "D 金融市场",
  HC_human_capital: "HC 人力资本",
};

function titleFor(run?: RunDetail): string {
  const parts = [run?.jd_context?.company_hint, run?.jd_context?.role_title_hint].filter(Boolean);
  return parts.join(" · ") || "Untitled draft";
}

function subtitleFor(run?: RunDetail): string {
  const lens = run?.lens_routing?.primary_lens;
  const label = lens ? LENS_LABEL[lens] : "";
  const loc = run?.jd_context?.location_hint;
  return [loc, label && `${label} lens`].filter(Boolean).join(" · ");
}

function hasTexArtifact(run?: RunDetail): boolean {
  return Boolean(run?.tex_artifact_path?.trim());
}

export function DraftReview({ draftId }: Props) {
  const { data, isLoading, isError, error, refetch } = useRun(draftId);
  // Fetch per-lens master statuses so the "I made N changes from your master"
  // line can name the lens (e.g. "from your C 产品运营 master") when this
  // run was routed to a lens that has its own per-lens master generated.
  // Falls back to legacy "from your master (routed for ... fit)" otherwise.
  const { data: masters } = useMasters(true);

  const lifecycle = data?.lifecycle;
  const lifecycleState = lifecycle?.current_state ?? "tailored";
  const lastEvent = lifecycle?.events?.[lifecycle.events.length - 1];

  return (
    <main className="flex min-h-[100dvh] flex-col bg-background lg:h-screen">
      <header className="flex flex-wrap items-center gap-3 border-b border-border bg-background/85 px-4 py-3 sm:gap-4 sm:px-6">
        <a href="/" className="inline-flex items-center gap-1 text-xs text-muted-foreground transition hover:text-foreground">
          <ChevronRight className="h-3 w-3 rotate-180" />
          Inbox
        </a>
        <span className="h-4 w-px bg-border" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Draft · {draftId.slice(0, 8)}
          </p>
          <h1 className="truncate text-lg text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
            {isLoading ? "Loading…" : titleFor(data)}
          </h1>
          <p className="truncate text-[11.5px] text-muted-foreground">{subtitleFor(data)}</p>
        </div>
        {data ? <LifecyclePicker runId={draftId} current={lifecycleState} lastEvent={lastEvent} /> : null}
        <div className="hidden items-center gap-1.5 md:flex">
          <HeaderArtifactLinks draftId={draftId} loading={isLoading} available={hasTexArtifact(data)} />
          <button
            disabled
            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-muted px-2.5 text-[11px] font-medium text-muted-foreground"
          >
            <Send className="h-3 w-3" />
            Submit
          </button>
        </div>
      </header>
      {isError ? (
        <ErrorBlock
          message={error?.message ?? "Failed to load run."}
          onRetry={() => void refetch()}
        />
      ) : isLoading && !data ? (
        <RunDetailLoadingSkeleton />
      ) : (
        <RunReviewWorkspace
          draftId={draftId}
          data={data}
          loading={isLoading}
          masters={masters}
        />
      )}
    </main>
  );
}

function RunReviewWorkspace({
  draftId,
  data,
  loading,
  masters,
}: {
  draftId: string;
  data?: RunDetail;
  loading: boolean;
  masters?: MastersResponse;
}) {
  const [diagnosisOpen, setDiagnosisOpen] = useState(false);
  const [rewriteOpen, setRewriteOpen] = useState(true);
  // Preview pane: collapsible (desktop) + resizable split. leftPct is the
  // diagnosis/verify column width as a % of the workspace (desktop only;
  // panels stack on mobile). Resize + collapse are desktop power-features.
  const [previewCollapsed, setPreviewCollapsed] = useState(false);
  const [leftPct, setLeftPct] = useState(42);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const cards = data?.change_cards ?? [];
  const claimsLabel =
    data?.verdict === "partial_pending_user" ? "Needs claim decisions" : "No claim gate";
  const hasDiagnosisScore = Boolean(
    data?.match_scores?.resume_match_score ?? data?.fit_diagnosis_post_rewrite?.hrbp?.keyword_hit_rate,
  );

  const startDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    draggingRef.current = true;
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    setLeftPct(Math.min(72, Math.max(28, pct)));
  };
  const endDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    draggingRef.current = false;
    setDragging(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* pointer already released */
    }
  };

  return (
    <div
      ref={containerRef}
      className={`flex min-h-0 flex-1 flex-col lg:flex-row ${dragging ? "select-none" : ""}`}
      style={{ "--left-w": `${leftPct}%` } as CSSProperties}
    >
      <section
        className={
          previewCollapsed
            ? "min-h-0 w-full overflow-auto px-6 py-5"
            : "min-h-0 w-full overflow-auto border-b border-border px-6 py-5 lg:w-[var(--left-w)] lg:border-b-0"
        }
      >
        <SubSkillErrorBanner events={data?.degradation_events ?? []} />
        <CollapsibleSection
          eyebrow="Step 1"
          title="诊断"
          subtitle="Diagnosis · how this resume fits the JD"
          open={diagnosisOpen}
          onToggle={() => setDiagnosisOpen((v) => !v)}
          summary={
            <>
              <SummaryPill tone="verified">fit diagnosis</SummaryPill>
              <SummaryPill tone="attention">{hasDiagnosisScore ? "scored" : "pending"}</SummaryPill>
            </>
          }
        >
          {data && data.verdict === "degraded_no_substance" ? (
            <div className="mb-4">
              <DegradedSubstanceBanner check={data.substance_check} />
            </div>
          ) : null}
          <div className="space-y-4">
            <FitDiagnosisPostRewritePanel diagnosis={data?.fit_diagnosis_post_rewrite} />
            <FitDiagnosisPreRewritePanel diagnosis={data?.fit_diagnosis_pre_rewrite} />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          eyebrow="Step 2"
          title="逐条核实"
          subtitle="Rewrite · approve, reject, or edit inferred claims"
          open={rewriteOpen}
          onToggle={() => setRewriteOpen((v) => !v)}
          summary={
            <>
              <SummaryPill tone={data?.verdict === "partial_pending_user" ? "attention" : "verified"}>
                {claimsLabel}
              </SummaryPill>
              <SummaryPill tone="primary">{cards.length} changes</SummaryPill>
            </>
          }
        >
          {data && data.verdict === "partial_pending_user" ? (
            <div className="mb-5">
              <Pass3VerifyPanel runId={draftId} />
            </div>
          ) : null}
          <ChangesContent data={data} loading={loading} masters={masters} compact />
        </CollapsibleSection>
      </section>

      {/* Draggable divider — desktop only, only when preview is expanded */}
      {!previewCollapsed ? (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panels"
          onPointerDown={startDrag}
          onPointerMove={onDrag}
          onPointerUp={endDrag}
          className="group relative hidden w-1.5 shrink-0 cursor-col-resize touch-none border-l border-border bg-border/40 transition-colors hover:bg-primary/30 lg:block"
        >
          <span
            aria-hidden
            className="absolute left-1/2 top-1/2 h-9 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-border transition-colors group-hover:bg-primary/60"
          />
        </div>
      ) : null}

      {/* RIGHT: when collapsed, show a narrow strip with expand icon at top */}
      {previewCollapsed ? (
        <div className="hidden w-9 shrink-0 flex-col border-l border-border bg-card/30 pt-2 lg:flex">
          <button
            type="button"
            onClick={() => setPreviewCollapsed(false)}
            aria-label="Show preview"
            title="Show preview"
            className="mx-auto flex h-7 w-7 items-center justify-center rounded text-muted-foreground/50 transition hover:text-foreground"
          >
            <PanelRightOpen className="h-4 w-4" />
          </button>
        </div>
      ) : null}

      <section
        className={
          previewCollapsed
            ? "min-h-0 overflow-auto bg-card/30 px-7 py-5 lg:hidden"
            : "relative min-h-0 flex-1 overflow-auto bg-card/30 px-7 py-5"
        }
      >
        {/* Collapse icon — top-left corner, desktop only, no text/border */}
        <button
          type="button"
          onClick={() => setPreviewCollapsed(true)}
          aria-label="Collapse preview"
          title="Collapse preview"
          className="absolute left-3 top-3 hidden h-7 w-7 items-center justify-center rounded text-muted-foreground/50 transition hover:text-foreground lg:flex"
        >
          <PanelRightClose className="h-4 w-4" />
        </button>
        <div className="mx-auto max-w-3xl">
          <TexPreview draftId={draftId} artifactAvailable={data ? hasTexArtifact(data) : undefined} embedded />
        </div>
      </section>
    </div>
  );
}

function HeaderArtifactLinks({
  draftId,
  loading,
  available,
}: {
  draftId: string;
  loading: boolean;
  available: boolean;
}) {
  if (loading) {
    return (
      <>
        <span className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          .tex
        </span>
        <span className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          PDF
        </span>
      </>
    );
  }
  if (!available) {
    return (
      <>
        <span
          title="No resume artifact was produced for this run."
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-muted px-2.5 text-[11px] font-medium text-muted-foreground"
        >
          <Download className="h-3 w-3" />
          .tex unavailable
        </span>
        <span
          title="No resume artifact was produced for this run."
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-muted px-2.5 text-[11px] font-medium text-muted-foreground"
        >
          <ExternalLink className="h-3 w-3" />
          PDF unavailable
        </span>
      </>
    );
  }
  return (
    <>
      <a
        href={getTexUrl(draftId)}
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium transition hover:border-foreground/20"
      >
        <Download className="h-3 w-3" />
        .tex
      </a>
      <a
        href={getPdfUrl(draftId)}
        target="_blank"
        rel="noreferrer"
        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium transition hover:border-foreground/20"
      >
        <ExternalLink className="h-3 w-3" />
        PDF
      </a>
    </>
  );
}

function CollapsibleSection({
  eyebrow,
  title,
  subtitle,
  open,
  onToggle,
  summary,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  open: boolean;
  onToggle: () => void;
  summary?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border-t border-border first:border-t-0">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-0.5 py-3 text-left"
        aria-expanded={open}
      >
        <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition ${open ? "rotate-90" : ""}`} />
        <div className="min-w-0 flex-1">
          <p className="text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </p>
          <div className="mt-0.5 flex min-w-0 items-baseline gap-2">
            <h2 className="text-[17px] text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
              {title}
            </h2>
            <span className="truncate font-mono text-[10.5px] text-muted-foreground">{subtitle}</span>
          </div>
        </div>
        {!open && summary ? <div className="hidden flex-wrap gap-1.5 md:flex">{summary}</div> : null}
      </button>
      {open ? <div className="pb-6 pl-6">{children}</div> : null}
    </section>
  );
}

function SummaryPill({
  tone,
  children,
}: {
  tone: "verified" | "attention" | "error" | "primary";
  children: ReactNode;
}) {
  const cls =
    tone === "verified"
      ? "bg-verified/10 text-verified"
      : tone === "attention"
        ? "bg-attention/15 text-attention-foreground"
        : tone === "error"
          ? "bg-error/10 text-error"
          : "bg-primary/10 text-primary";
  return (
    <span className={`inline-flex h-5 items-center rounded-full px-2 text-[10.5px] font-medium ${cls}`}>
      {children}
    </span>
  );
}

/* ---------------------------------- Changes ---------------------------------- */

function ChangesContent({
  data,
  loading,
  masters,
  compact = false,
}: {
  data?: RunDetail;
  loading: boolean;
  masters?: MastersResponse;
  compact?: boolean;
}) {
  if (loading)
    return <div className="h-32 rounded-xl border border-border bg-card/50 animate-pulse" />;
  if (!data) return null;

  const cards = data.change_cards ?? [];
  const lens = data.lens_routing?.primary_lens;
  const lensLabel = lens ? LENS_LABEL[lens] : null;
  const isCustomMaster = data.matched_resume_version === "custom";

  // C.2.3 — when the run was routed to a lens that has its own per-lens
  // master generated, name the lens explicitly and surface generated_at.
  // When the run is "custom" but the lens has no per-lens master (legacy
  // single-master case), fall back to the existing "routed for ... fit"
  // wording so we don't claim a generation that didn't happen.
  const perLensMaster = lens && masters ? masters[lens] : undefined;
  const hasPerLensMaster =
    isCustomMaster && perLensMaster?.has_master && perLensMaster.status === "ready";
  const generatedDate = (() => {
    const iso = perLensMaster?.generated_at ?? null;
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleDateString();
    } catch {
      return iso.slice(0, 10);
    }
  })();

  return (
    <>
      <div className={compact ? "pb-4" : "pb-6"}>
        <p className="text-sm leading-relaxed text-foreground">
          <span className="text-primary mr-2">✦</span>I made{" "}
          <span className="font-medium">
            {cards.length} {cards.length === 1 ? "change" : "changes"}
          </span>{" "}
          {isCustomMaster ? (
            hasPerLensMaster && lensLabel ? (
              <>
                from your{" "}
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  {lensLabel}
                </span>{" "}
                master (custom{generatedDate ? `, generated ${generatedDate}` : ""}).
              </>
            ) : (
              <>
                from <span className="font-medium">your master</span>
                {lensLabel ? (
                  <>
                    {" "}(routed for{" "}
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                      {lensLabel}
                    </span>{" "}
                    fit)
                  </>
                ) : null}
                .
              </>
            )
          ) : (
            <>
              from your{" "}
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                {lensLabel ?? "master"}
              </span>{" "}
              master ({data.matched_resume_version ?? "default"}).
            </>
          )}
        </p>
      </div>

      {cards.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card/40 px-4 py-6 text-center text-sm text-muted-foreground">
          No changes — your master fit the JD as-is.
        </div>
      ) : (
        <div className="space-y-3">
          {cards.map((c, i) => (
            <ChangeCard key={i} title={c.title} before={c.before} after={c.after} note={c.note} />
          ))}
        </div>
      )}

      <div className={compact ? "mt-8 border-t border-border pt-5" : "mt-12 pt-8 border-t border-border"}>
        <button
          disabled
          title="Auto-submit channels (LinkedIn / Boss / Workday / Email) arrive in Wave 3."
          className="flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-muted font-medium text-muted-foreground cursor-not-allowed"
        >
          <Send className="h-4 w-4" />
          Submit · coming in Wave 3
        </button>
        <p className="mt-3 text-center text-xs text-muted-foreground">
          For now: download the .tex / PDF from the preview tab and submit on the company site
          yourself.
        </p>
      </div>

      <div className={compact ? "mt-6" : "mt-10"}>
        <WhyExpand
          lensRouting={data.lens_routing}
          competencyModel={data.competency_model}
          rewriteEngineOutput={data.rewrite_engine_output}
        />
      </div>

      <DegradationsList events={data.degradation_events ?? []} />
    </>
  );
}

function DegradationsList({ events }: { events: DegradationEvent[] }) {
  if (events.length === 0) return null;
  return (
    <details className="mt-6 rounded-xl border border-border bg-attention/5 px-4 py-3 text-xs">
      <summary className="cursor-pointer text-attention-foreground/80">
        ◷ {events.length} {events.length === 1 ? "stage" : "stages"} degraded — verify before submit
      </summary>
      <ul className="mt-3 space-y-2">
        {events.map((e, i) => (
          <li key={i} className="flex items-start gap-2 text-muted-foreground">
            <span className="font-mono text-foreground/70">{e.stage}</span>
            <span>
              {e.reason} → {e.fallback_taken}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function RunDetailLoadingSkeleton() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-4 py-6 sm:px-6 motion-reduce:animate-none" aria-busy="true" aria-label="Loading run">
      <div className="h-24 animate-pulse rounded-xl bg-card/60 motion-reduce:animate-none" />
      <div className="h-40 animate-pulse rounded-xl bg-card/60 motion-reduce:animate-none" />
      <div className="h-64 flex-1 animate-pulse rounded-xl bg-card/60 motion-reduce:animate-none" />
    </div>
  );
}

function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mx-4 mt-6 rounded-2xl border border-border bg-card/40 px-6 py-8 text-center sm:mx-6">
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

/* -------------------------------- Tex preview ------------------------------- */

function TexPreview({
  draftId,
  artifactAvailable,
  embedded = false,
}: {
  draftId: string;
  artifactAvailable?: boolean;
  embedded?: boolean;
}) {
  const [tex, setTex] = useState<string | null>(null);
  const [texError, setTexError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [pdfState, setPdfState] = useState<"loading" | "ready" | "error">("loading");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfErrorMsg, setPdfErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTex(null);
    setTexError(null);
    if (artifactAvailable === undefined) return;
    if (!artifactAvailable) {
      setTexError("No .tex artifact was produced for this run.");
      return;
    }
    fetch(getTexUrl(draftId), { headers: { "X-User-Id": getUserId() } })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.text();
      })
      .then((t) => {
        if (!cancelled) setTex(t);
      })
      .catch((e) => {
        if (!cancelled) setTexError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, artifactAvailable]);

  // Fetch the PDF as a blob with an explicit status check. An <iframe src=/pdf>
  // cannot detect HTTP errors — onError does NOT fire for 4xx/5xx, so the iframe
  // would render the error body, which showed up as 乱码 when the compile failed
  // (e.g. Docker daemon down). Fetching lets us check r.ok and surface a clean
  // message + the .tex download instead of garbage.
  useEffect(() => {
    let cancelled = false;
    let objUrl: string | null = null;
    setPdfState("loading");
    setPdfUrl(null);
    setPdfErrorMsg(null);
    if (artifactAvailable === undefined) return;
    if (!artifactAvailable) {
      setPdfErrorMsg("No resume artifact was produced for this run.");
      setPdfState("error");
      return;
    }
    fetch(getPdfUrl(draftId), { headers: { "X-User-Id": getUserId() } })
      .then(async (r) => {
        if (!r.ok) {
          let msg = `${r.status} ${r.statusText}`;
          try {
            const body = await r.json();
            const detail = body?.detail;
            if (detail) msg = typeof detail === "string" ? detail : (detail.message ?? msg);
          } catch {
            /* non-JSON error body — keep the status line */
          }
          throw new Error(msg);
        }
        return r.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objUrl = URL.createObjectURL(blob);
        setPdfUrl(objUrl);
        setPdfState("ready");
      })
      .catch((e) => {
        if (cancelled) return;
        setPdfErrorMsg(e instanceof Error ? e.message : String(e));
        setPdfState("error");
      });
    return () => {
      cancelled = true;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [draftId, artifactAvailable]);

  const onCopy = async () => {
    if (!tex || typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(tex);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const downloadHref = tex
    ? "data:text/plain;charset=utf-8," + encodeURIComponent(tex)
    : getTexUrl(draftId);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onCopy}
          disabled={!tex}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20 disabled:opacity-50"
        >
          <Copy className="h-3.5 w-3.5" />
          {copied ? "Copied!" : "Copy .tex"}
        </button>
        {artifactAvailable === undefined ? (
          <>
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading .tex
            </span>
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading PDF
            </span>
          </>
        ) : artifactAvailable ? (
          <>
            <a
              href={downloadHref}
              download="resume.tex"
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
            >
              <Download className="h-3.5 w-3.5" />
              Download .tex
            </a>
            <a
              href={getPdfUrl(draftId)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open PDF
            </a>
          </>
        ) : (
          <>
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-medium text-muted-foreground">
              <Download className="h-3.5 w-3.5" />
              .tex unavailable
            </span>
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-medium text-muted-foreground">
              <ExternalLink className="h-3.5 w-3.5" />
              PDF unavailable
            </span>
          </>
        )}
      </div>

      <div className="relative overflow-hidden rounded-md border border-border bg-card min-h-[200px] shadow-[0_1px_0_rgba(0,0,0,0.02),0_6px_24px_rgba(0,0,0,0.04)]">
        {pdfState === "loading" ? (
          <div className="flex h-[200px] items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : pdfState === "error" ? (
          <div className="px-4 py-10 text-center sm:px-6">
            <p className="text-sm font-medium text-foreground">PDF preview unavailable</p>
            <p className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-muted-foreground">
              {pdfErrorMsg?.includes("503") || /unavailable|docker|tex/i.test(pdfErrorMsg ?? "")
                ? "Install Docker or TeX Live for in-app PDF preview (see KNOWN_ISSUES.md). Your .tex file is still available below."
                : (pdfErrorMsg ?? "Compile failed.")}
            </p>
            <p className="mt-3 text-xs text-muted-foreground">
              Use <span className="text-foreground">Download .tex</span> above, or{" "}
              <span className="text-foreground">Open PDF</span> to retry after fixing the toolchain.
            </p>
          </div>
        ) : (
          <iframe
            src={pdfUrl ?? undefined}
            title="Resume PDF preview"
            className={`w-full ${embedded ? "h-[calc(100vh-190px)] min-h-[640px]" : "h-[640px]"}`}
          />
        )}
      </div>

      <details className="rounded-lg border border-border bg-muted/30 text-xs">
        <summary className="cursor-pointer px-3 py-2 text-muted-foreground hover:text-foreground">
          View raw .tex source
        </summary>
        <pre className="overflow-x-auto border-t border-border px-3 py-3 font-mono text-[11px] text-foreground/85">
          {texError ? `Failed to load: ${texError}` : (tex ?? "Loading…")}
        </pre>
      </details>
    </div>
  );
}
