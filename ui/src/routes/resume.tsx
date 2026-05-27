import { createFileRoute, Link } from "@tanstack/react-router";
import { Fragment, useState } from "react";
import { Check, Download, Eye, FileText, Loader2, RotateCcw, Upload } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResumeUpload } from "@/components/upload/ResumeUpload";
import { MasterStatusPill } from "@/components/master/MasterStatusPill";
import { MasterDiff } from "@/components/master/MasterDiff";
import {
  useGenerateMaster,
  useLensMasterTex,
  useMasters,
  useUserMasterTex,
  useUserStatus,
} from "@/lib/queries";
import {
  API_BASE,
  LENSES,
  LENS_DESCRIPTIONS_EN,
  LENS_LABELS_ZH,
  type Lens,
} from "@/lib/api";
import { getUserId } from "@/lib/user";

export const Route = createFileRoute("/resume")({
  head: () => ({
    meta: [{ title: "Resume — Resume Tailor" }],
  }),
  component: ResumePage,
});

function humanizeAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 120_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)} min ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)} hours ago`;
  if (ms < 86_400_000 * 7) return `${Math.floor(ms / 86_400_000)} days ago`;
  return new Date(iso).toLocaleDateString();
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function errorMessageFromResponse(r: Response): Promise<string> {
  const text = await r.text().catch(() => "");
  if (!text) return `${r.status} ${r.statusText}`;
  try {
    const parsed = JSON.parse(text);
    const detail = parsed?.detail;
    if (typeof detail === "string") return detail;
    if (detail?.message) return detail.message;
  } catch {
    // Keep plain text below.
  }
  return text.slice(0, 220);
}

function ResumePage() {
  const { data: status, isLoading } = useUserStatus();
  const hasResume = status?.has_resume ?? false;
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const masterTex = useUserMasterTex(hasResume);

  const downloadMasterPdf = async () => {
    setPdfError(null);
    setPdfBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/users/me/master/pdf`, {
        headers: { "X-User-Id": getUserId() },
      });
      if (!r.ok) throw new Error(await errorMessageFromResponse(r));
      triggerBlobDownload(await r.blob(), "master.pdf");
    } catch (e) {
      setPdfError((e as Error).message);
    } finally {
      setPdfBusy(false);
    }
  };

  if (isLoading && !status) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="h-40 animate-pulse rounded-lg bg-card/50" />
      </div>
    );
  }

  if (!hasResume) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <Header
          eyebrow="Master + per-lens variants"
          title="Resume bank"
          subtitle="One master resume and the lens-routed variants the tailoring engine can start from."
        />
        <div className="mt-8">
          <div className="mb-5 text-center">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </span>
            <h2
              className="mt-4 text-lg text-foreground"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              No resume uploaded yet
            </h2>
            <p className="mx-auto mt-1.5 max-w-sm text-xs leading-relaxed text-muted-foreground">
              Drop your resume below to start tailoring. Accepted: .md · .tex · .docx · .pdf
            </p>
          </div>
          <ResumeUpload />
          <div className="mt-4 text-center">
            <Link
              to="/setup"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Or use the full setup wizard →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const profile = status?.profile;
  const fmt = profile?.master_format ?? "tex";
  const uploadedAt = profile?.master_uploaded_at;
  const confidence = profile?.master_parse_confidence ?? 1;
  const parseMeta = profile?.master_parse_meta;

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <Header
          eyebrow="Master + per-lens variants"
          title="Resume bank"
          subtitle="One master resume and the lens-routed variants the tailoring engine can start from."
        />

        <section className="mt-6 rounded-lg border border-border bg-card p-5">
          <div className="flex flex-col gap-5 md:flex-row md:items-center">
            <DocumentThumb />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  Master · default
                </span>
                <span className="inline-flex h-5 items-center gap-1 rounded-full bg-verified/10 px-2 text-[10px] font-medium text-verified">
                  <Check className="h-3 w-3" />
                  uploaded
                </span>
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                  {fmt}
                </span>
              </div>
              <h2
                className="mt-1 truncate text-xl text-foreground"
                style={{ fontFamily: "var(--font-serif)" }}
              >
                Master resume
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>{uploadedAt ? `uploaded ${humanizeAge(uploadedAt)}` : "upload time unavailable"}</span>
                <span
                  className="inline-flex items-center gap-2"
                  title="Parse confidence — how reliably we extracted text from your file. Format-driven (only .tex hits 100%); does not measure AI master quality."
                >
                  parse confidence
                  <ConfidenceBar value={confidence} />
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  onClick={() => setSourceOpen((v) => !v)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
                >
                  <Eye className="h-3.5 w-3.5" />
                  {sourceOpen ? "Hide source" : "View source"}
                </button>
                {masterTex.data ? (
                  <a
                    href={`data:text/plain;charset=utf-8,${encodeURIComponent(masterTex.data)}`}
                    download="master.tex"
                    className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
                  >
                    <Download className="h-3.5 w-3.5" />
                    .tex
                  </a>
                ) : null}
                <button
                  type="button"
                  onClick={downloadMasterPdf}
                  disabled={pdfBusy}
                  title="Compile master.tex to PDF and download it"
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {pdfBusy ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}
                  .pdf
                </button>
                <button
                  onClick={() => setReplaceOpen(true)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
                >
                  <Upload className="h-3.5 w-3.5" />
                  Replace
                </button>
              </div>
              {pdfError ? (
                <p className="mt-2 text-[11px] leading-relaxed text-error">
                  PDF download failed: {pdfError}
                </p>
              ) : null}
            </div>
          </div>
          <ParseDetailsCard fmt={fmt} confidence={confidence} meta={parseMeta} />
          {sourceOpen ? (
            <div className="mt-4 overflow-hidden rounded-lg border border-border bg-background/55">
              <div className="flex items-center justify-between border-b border-border px-3 py-2">
                <span className="text-xs font-medium text-foreground">master.tex (uploaded)</span>
                {masterTex.isFetching && masterTex.data ? (
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                ) : null}
              </div>
              <pre className="max-h-[420px] overflow-auto px-3 py-3 font-mono text-[11px] leading-relaxed text-foreground/85">
                {masterTex.isLoading
                  ? "Loading..."
                  : masterTex.isError
                    ? `Failed to load: ${(masterTex.error as Error).message}`
                    : (masterTex.data ?? "(empty)")}
              </pre>
            </div>
          ) : null}
        </section>

        <PerLensMasters />
      </div>

      <Dialog open={replaceOpen} onOpenChange={setReplaceOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Replace master resume</DialogTitle>
            <DialogDescription>
              Existing tailoring runs are unaffected. Future runs will use the new master.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <ResumeUpload onSuccess={() => setReplaceOpen(false)} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

function Header({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <header>
      <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        {eyebrow}
      </p>
      <h1
        className="mt-1 text-3xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        {title}
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
    </header>
  );
}

function DocumentThumb() {
  return (
    <div className="flex h-32 w-24 shrink-0 flex-col justify-center gap-1 rounded border border-border bg-white p-3 shadow-[0_1px_0_rgba(15,23,42,0.03)]">
      <span className="h-1.5 w-2/3 rounded bg-foreground" />
      <span className="mt-1 h-1 w-full rounded bg-border" />
      <span className="h-1 w-11/12 rounded bg-border" />
      <span className="h-1 w-2/3 rounded bg-border" />
      <span className="mt-2 h-1.5 w-1/2 rounded bg-foreground" />
      <span className="mt-1 h-1 w-full rounded bg-border" />
      <span className="h-1 w-5/6 rounded bg-border" />
      <span className="h-1 w-3/4 rounded bg-border" />
    </div>
  );
}

function PerLensMasters() {
  const { data: masters, isLoading } = useMasters();
  const rows = LENSES.map((lens) => ({
    lens,
    info: masters?.[lens],
  }));

  if (isLoading && !masters) {
    return (
      <div className="mt-7">
        <div className="mb-2 h-4 w-44 animate-pulse rounded bg-card/60" />
        <div className="h-40 animate-pulse rounded-lg bg-card/60" />
      </div>
    );
  }

  return (
    <section className="mt-7">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
          Lens variants · {rows.filter((row) => row.info?.status === "ready").length} ready
        </p>
        <Link
          to="/settings"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Manage in Settings
        </Link>
      </div>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-border text-left text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Lens</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Availability</th>
              <th className="px-3 py-2 font-medium">Last generated</th>
              <th className="py-2 pl-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ lens, info }) => (
              <LensMasterRow
                key={lens}
                lens={lens}
                status={info?.status ?? "absent"}
                generatedAt={info?.generated_at ?? null}
                method={info?.method ?? null}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LensMasterRow({
  lens,
  status,
  generatedAt,
  method,
}: {
  lens: Lens;
  status: "ready" | "generating" | "absent";
  generatedAt: string | null;
  method: string | null;
}) {
  // When master_gen falls back (LLM unreachable / failed), the engine
  // preserves the upload verbatim and the persisted method is "user_upload".
  // The diff in that case is empty — surface this to the user so they
  // understand the AI didn't actually run, instead of inferring "AI didn't
  // change anything" from an empty diff.
  const isFallback = method === "user_upload";
  const generateMut = useGenerateMaster();
  const regenerate = () => {
    generateMut.mutate(lens);
  };
  const [diffOpen, setDiffOpen] = useState(false);
  // Eagerly fetch when ready so Diff + Download share one payload.
  const tex = useLensMasterTex(lens, status === "ready");
  const originalTex = useUserMasterTex(status === "ready" && diffOpen);
  const [dlBusy, setDlBusy] = useState(false);
  const [dlError, setDlError] = useState<string | null>(null);

  const userIdHeader = (): string =>
    (typeof localStorage !== "undefined"
      ? localStorage.getItem("rt:user_id")
      : null) ?? "default";

  const triggerBlobDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownload = async (fmt: "tex" | "pdf") => {
    setDlError(null);
    setDlBusy(true);
    try {
      if (fmt === "tex") {
        const content =
          tex.data ??
          (await (async () => {
            const r = await fetch(`${API_BASE}/api/users/masters/${lens}/tex`, {
              headers: { "X-User-Id": userIdHeader() },
            });
            if (!r.ok) throw new Error(`HTTP ${r.status} on tex fetch`);
            return r.text();
          })());
        triggerBlobDownload(
          new Blob([content], { type: "text/x-tex;charset=utf-8" }),
          `master.${lens}.tex`,
        );
      } else {
        const r = await fetch(`${API_BASE}/api/users/masters/${lens}/pdf`, {
          headers: { "X-User-Id": userIdHeader() },
        });
        if (!r.ok) {
          const text = await r.text().catch(() => "");
          throw new Error(`HTTP ${r.status}: ${text.slice(0, 200) || r.statusText}`);
        }
        triggerBlobDownload(await r.blob(), `master.${lens}.pdf`);
      }
    } catch (e) {
      setDlError((e as Error).message);
    } finally {
      setDlBusy(false);
    }
  };

  const availability = status === "ready" ? (isFallback ? 45 : 100) : status === "generating" ? 35 : 0;

  return (
    <Fragment>
      <tr className="border-b border-border align-middle transition hover:bg-card/45">
        <td className="py-3 pr-4">
          <div className="flex min-w-64 items-center gap-2.5">
            <span
              className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md font-mono text-[10px] font-medium ${
                status === "ready"
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {lens === "HC_human_capital" ? "HC" : lens.slice(0, 1)}
            </span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-foreground">{LENS_LABELS_ZH[lens]}</div>
              <div className="truncate text-[11px] text-muted-foreground">{LENS_DESCRIPTIONS_EN[lens]}</div>
            </div>
          </div>
        </td>
        <td className="px-3 py-3">
          <div className="flex items-center gap-1.5">
            {isFallback ? (
              <span
                className="inline-flex h-5 items-center rounded-full bg-attention/15 px-2 text-[10px] font-medium text-attention"
                title="LLM was unreachable when this master was generated — content is identical to your upload. Click Regenerate to retry."
              >
                fallback
              </span>
            ) : null}
            <MasterStatusPill status={status} />
          </div>
        </td>
        <td className="px-3 py-3">
          <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
            <span className="w-8 text-foreground">{availability}%</span>
            <span className="h-1 w-20 overflow-hidden rounded-full bg-muted">
              <span
                className="block h-full rounded-full bg-verified"
                style={{ width: `${availability}%` }}
              />
            </span>
          </div>
        </td>
        <td className="px-3 py-3 text-xs text-muted-foreground">
          {generatedAt ? humanizeAge(generatedAt) : "not yet"}
        </td>
        <td className="py-3 pl-3">
          <div className="flex justify-end gap-1.5">
            {status === "ready" ? (
              <>
                <button
                  onClick={() => setDiffOpen((v) => !v)}
                  title="Compare with the uploaded master.tex"
                  className={`inline-flex h-7 items-center gap-1 rounded-md border px-2 text-[11px] font-medium transition ${
                    diffOpen
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border bg-card hover:border-foreground/20"
                  }`}
                >
                  Diff
                </button>
                <select
                  aria-label="Download master"
                  value=""
                  disabled={dlBusy}
                  onChange={(e) => {
                    const v = e.target.value as "" | "tex" | "pdf";
                    if (v) handleDownload(v);
                    e.target.value = "";
                  }}
                  className="h-7 rounded-md border border-border bg-card px-2 text-[11px] font-medium transition hover:border-foreground/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="" disabled>
                    {dlBusy ? "Downloading..." : "Download..."}
                  </option>
                  <option value="tex">.tex source</option>
                  <option value="pdf">.pdf compiled</option>
                </select>
              </>
            ) : (
              <button
                onClick={regenerate}
                disabled={generateMut.isPending}
                className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2 text-[11px] font-medium transition hover:border-foreground/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generateMut.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RotateCcw className="h-3 w-3" />
                )}
                Generate
              </button>
            )}
          </div>
        </td>
      </tr>
      {isFallback ? (
        <tr className="border-b border-border">
          <td colSpan={5} className="bg-attention/5 px-3 py-2 text-[11px] leading-relaxed">
            <span className="font-medium text-attention">AI generation fell back to your upload.</span>{" "}
            <span className="text-muted-foreground">
              The per-lens master is currently an identical copy of your uploaded .tex.
            </span>{" "}
            <button
              onClick={regenerate}
              disabled={generateMut.isPending}
              className="ml-1 font-medium text-foreground underline-offset-2 hover:underline disabled:opacity-50"
            >
              Regenerate
            </button>
          </td>
        </tr>
      ) : null}
      {dlError ? (
        <tr className="border-b border-border">
          <td colSpan={5} className="px-3 py-2 text-[11px] text-error">
            Download failed: {dlError}
          </td>
        </tr>
      ) : null}
      {diffOpen && status === "ready" ? (
        <tr className="border-b border-border">
          <td colSpan={5} className="bg-card/35 px-3 py-3">
            {tex.isLoading || originalTex.isLoading ? (
              <p className="text-xs text-muted-foreground">Loading diff...</p>
            ) : tex.isError || originalTex.isError ? (
              <p className="text-xs text-error">
                Failed to load: {((tex.error ?? originalTex.error) as Error).message}
              </p>
            ) : tex.data && originalTex.data ? (
              <MasterDiff
                before={originalTex.data}
                after={tex.data}
                beforeLabel="Uploaded master"
                afterLabel={`AI master · ${LENS_LABELS_ZH[lens]}`}
                fallbackEmpty={isFallback}
              />
            ) : (
              <p className="text-xs text-muted-foreground">Diff unavailable (missing data).</p>
            )}
          </td>
        </tr>
      ) : null}
    </Fragment>
  );
}

function ParseDetailsCard({
  fmt,
  confidence,
  meta,
}: {
  fmt: string;
  confidence: number;
  meta:
    | {
        format?: string;
        file_bytes?: number;
        warnings?: string[];
        section_count?: number;
        section_names?: string[];
        raw_tex_bytes?: number;
      }
    | undefined;
}) {
  const [open, setOpen] = useState(false);
  const pct = Math.round(Math.max(0, Math.min(1, confidence)) * 100);
  // Per-format reasoning text — explains the cap, not the measurement.
  const reasoning: Record<string, string> = {
    tex: "Native .tex is parsed losslessly — start at 100%. Drops to 85% only if structural warnings (missing \\documentclass / \\begin{document}) fire.",
    md: ".md is converted to .tex via a structured pipeline — start at 95% because the section-header heuristic occasionally misses unusual headers.",
    docx: ".docx → .tex conversion preserves text but loses some formatting; rich structural data is approximated, so the cap is 85%.",
    pdf: "PDF parsing relies on layout heuristics and can mis-order columns or drop links — the cap is 60%. Re-uploading as .tex or .md will push parse confidence higher.",
  };
  const warnings = meta?.warnings ?? [];
  const sectionCount = meta?.section_count;
  const sectionNames = meta?.section_names ?? [];
  const fileBytes = meta?.file_bytes;

  return (
    <div className="mt-3 rounded-xl border border-border bg-card">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex flex-wrap items-baseline gap-2 text-xs">
          <span className="font-medium text-foreground">Parse details</span>
          <span className="text-muted-foreground">
            {pct}% · {fmt.toUpperCase()} ·{" "}
            {warnings.length > 0
              ? `${warnings.length} warning${warnings.length === 1 ? "" : "s"}`
              : "no warnings"}
            {sectionCount !== undefined ? ` · ${sectionCount} section${sectionCount === 1 ? "" : "s"}` : ""}
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-border px-4 py-3 text-xs leading-relaxed text-foreground">
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Parse confidence ≠ master quality.</span>{" "}
            This score reflects how reliably we extracted your resume into structured form — it's
            capped by file format and doesn't change when AI tailors a new master. (Master quality
            scoring is a separate v0.6 item.)
          </p>
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Why {pct}%?
            </p>
            <p className="mt-1">{reasoning[fmt] ?? "Format-driven cap based on parser reliability."}</p>
          </div>
          {warnings.length > 0 ? (
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Warnings ({warnings.length})
              </p>
              <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
            <Fact label="Format" value={fmt} />
            <Fact label="File size" value={fileBytes !== undefined ? `${(fileBytes / 1024).toFixed(1)} KB` : "—"} />
            <Fact label="Sections" value={sectionCount !== undefined ? String(sectionCount) : "—"} />
            <Fact label="Warnings" value={String(warnings.length)} />
          </div>
          {sectionNames.length > 0 ? (
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Detected sections
              </p>
              <div className="mt-1 flex flex-wrap gap-1">
                {sectionNames.map((n, i) => (
                  <span
                    key={i}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {n}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {fmt === "pdf" || fmt === "docx" ? (
            <p className="text-[11px] text-muted-foreground italic">
              Tip: re-upload as <span className="font-mono">.tex</span> or{" "}
              <span className="font-mono">.md</span> to lift the parse cap.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="font-mono text-xs text-foreground">{value}</p>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  const color =
    pct >= 0.85 ? "var(--verified)" : pct >= 0.7 ? "var(--primary)" : "var(--attention)";
  return (
    <>
      <span
        className="inline-block h-1.5 w-12 overflow-hidden rounded-full bg-muted align-middle"
        aria-label={`Confidence ${(pct * 100).toFixed(0)}%`}
      >
        <span
          className="block h-full rounded-full"
          style={{ width: `${pct * 100}%`, background: color }}
        />
      </span>
      <span className="font-mono text-[10px]">{(pct * 100).toFixed(0)}%</span>
    </>
  );
}
