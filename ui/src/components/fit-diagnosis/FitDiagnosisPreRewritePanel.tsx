// F4 — Fit Diagnosis (pre-rewrite) panel.
// Replaces the legacy MatchMatrixPanel against the new
// fit_diagnosis_pre_rewrite schema (see
// contracts/schemas/harness-tailor-output.schema.json).
//
// Field migrations from D06.1 -> F1:
//   - requirements -> matching_matrix
//   - per-row: NEW bridging_or_closure caption (visible on transferable
//     + missing rows; suppressed on strong_match where it's empty by spec)
//   - optimization_boundary.can_solve / cannot_solve ->
//     rewriting_can_solve / rewriting_cannot_solve
//   - top-level wrapper now carries sub_skill / mode /
//     inputs_signature / multi_jd / confidence (we don't render these,
//     they're metadata for backend correlation).
//
// Renders 4 sub-sections (visual order):
//   1. Header strip — title "匹配矩阵" + sub-line + RatingChip + MethodBadge
//   2. matching_matrix items as rows (verdict pill + text + evidence +
//      source + bridging_or_closure caption on transferable / missing)
//   3. integrated_assessment paragraph
//   4. optimization_boundary two-column (rewriting_can_solve /
//      rewriting_cannot_solve)
//
// GitBook design vocabulary applied:
//   - text-base font-semibold for primary section titles
//   - space-y-6 between sections, p-5 cards
//   - subtle border-border/60 on cards
//   - emerald/amber/red palette preserved via TonePill
//   - hover:bg-muted/40 transition on interactive matrix rows
//
// Renders nothing when diagnosis is undefined (graceful absence — historical
// runs / fallback skip; mirrors the legacy MatchMatrixPanel pattern).
import type { FitDiagnosisPreRewrite } from "@/types/generated";
import { MethodBadge } from "@/components/shared/method-badge";
import { RatingChip } from "@/components/shared/rating-chip";
import { TonePill, type Tone } from "@/components/shared/tone-pill";
import { useLang } from "@/lib/lang-context";

interface FitDiagnosisPreRewritePanelProps {
  diagnosis: FitDiagnosisPreRewrite | undefined;
}

type MatrixItem = FitDiagnosisPreRewrite["matching_matrix"][number];
type Verdict = MatrixItem["verdict"];
type Source = MatrixItem["source"];

const VERDICT_LABEL_EN: Record<Verdict, string> = {
  strong_match: "Strong match",
  transferable: "Transferable",
  missing: "Missing",
};

const VERDICT_LABEL_ZH: Record<Verdict, string> = {
  strong_match: "强匹配",
  transferable: "可包装",
  missing: "缺失",
};

const VERDICT_ICON: Record<Verdict, string> = {
  strong_match: "✅",
  transferable: "⚠️",
  missing: "❌",
};

// Aria-label text — describes the verdict in words for screen readers
// (the icon is purely decorative).
const VERDICT_ARIA_EN: Record<Verdict, string> = {
  strong_match: "Strong match",
  transferable: "Transferable",
  missing: "Missing",
};

const VERDICT_ARIA_ZH: Record<Verdict, string> = {
  strong_match: "强匹配 strong match",
  transferable: "可包装 transferable",
  missing: "缺失 missing",
};

const VERDICT_TONE: Record<Verdict, Tone> = {
  strong_match: "positive",
  transferable: "warn",
  missing: "neutral",
};

const SOURCE_LABEL: Record<Source, string> = {
  section_b_priority: "Section B priority",
  section_c_tier_1: "Section C · Tier 1",
  section_c_tier_2: "Section C · Tier 2",
  section_c_tier_3: "Section C · Tier 3",
};

export function FitDiagnosisPreRewritePanel({
  diagnosis,
}: FitDiagnosisPreRewritePanelProps) {
  const lang = useLang();
  const zh = lang === "zh";

  // Graceful absence: historical runs from before F1 won't have this
  // field; render nothing rather than a stub card.
  if (!diagnosis) return null;

  const items = diagnosis.matching_matrix ?? [];
  const canSolve = diagnosis.optimization_boundary?.rewriting_can_solve ?? [];
  const cannotSolve =
    diagnosis.optimization_boundary?.rewriting_cannot_solve ?? [];

  return (
    <section
      className="rounded-xl border border-border/60 bg-card overflow-hidden"
      aria-label={zh ? "匹配矩阵" : "Match matrix"}
    >
      {/* Header strip — section title + competitiveness rating chip.
          GitBook vocabulary: heavier title (text-base font-semibold), low-
          density padding, subtle separator. */}
      <header className="flex flex-wrap items-center gap-3 border-b border-border/60 bg-muted/30 px-5 py-3.5">
        <h2
          className="text-base font-semibold text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {zh ? "匹配矩阵" : "Match Matrix"}
        </h2>
        <span className="font-mono text-[10px] text-muted-foreground">
          {zh ? "Match matrix · 整体评估 · 优化边界" : "Match matrix · Integrated assessment · Optimization boundary"}
        </span>
        <RatingChip rating={diagnosis.competitiveness_rating} />
        <MethodBadge method={diagnosis._method} />
      </header>

      <div className="px-5 py-5 space-y-6">
        {/* 1. matching_matrix rows */}
        <MatrixList items={items} />

        {/* 2. Integrated assessment paragraph */}
        {diagnosis.integrated_assessment ? (
          <IntegratedAssessment text={diagnosis.integrated_assessment} />
        ) : null}

        {/* 3. Optimization boundary */}
        <OptimizationBoundary canSolve={canSolve} cannotSolve={cannotSolve} zh={zh} />
      </div>
    </section>
  );
}

/* ------------------------------ Matrix list ------------------------------ */

function MatrixList({ items }: { items: MatrixItem[] }) {
  const zh = useLang() === "zh";
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 px-4 py-6 text-center text-xs text-muted-foreground">
        {zh ? "暂无匹配项目" : "No requirements found"}
      </div>
    );
  }

  return (
    <ul aria-label={zh ? "JD 要求与简历匹配项" : "JD requirements vs resume matches"} className="space-y-2">
      {items.map((item, i) => (
        <MatrixRow key={`${item.text}-${i}`} item={item} />
      ))}
    </ul>
  );
}

function MatrixRow({ item }: { item: MatrixItem }) {
  const zh = useLang() === "zh";
  const showBridging =
    item.verdict !== "strong_match" && Boolean(item.bridging_or_closure?.trim());

  return (
    <li className="flex flex-col gap-1.5 rounded-lg border border-border/60 bg-background/40 px-4 py-3 transition hover:bg-muted/40 sm:flex-row sm:items-start sm:gap-3">
      <div className="shrink-0 sm:w-[88px]">
        <VerdictPill verdict={item.verdict} />
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        <p className="text-sm leading-snug text-foreground">{item.text}</p>
        {item.evidence ? (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {item.evidence}
          </p>
        ) : null}
        {item.source ? (
          <p className="font-mono text-[10px] text-muted-foreground/80">
            {SOURCE_LABEL[item.source]}
          </p>
        ) : null}
        {showBridging ? (
          <p
            aria-label="bridging or closure"
            className="border-l-2 border-amber-500/40 pl-2.5 text-xs leading-relaxed text-foreground/80"
          >
            <span className="mr-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {zh ? "过渡" : "Bridging"}
            </span>
            {item.bridging_or_closure}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function VerdictPill({ verdict }: { verdict: Verdict }) {
  const zh = useLang() === "zh";
  const label = zh ? VERDICT_LABEL_ZH[verdict] : VERDICT_LABEL_EN[verdict];
  const aria = zh ? VERDICT_ARIA_ZH[verdict] : VERDICT_ARIA_EN[verdict];
  return (
    <TonePill tone={VERDICT_TONE[verdict]} ariaLabel={aria}>
      <span aria-hidden="true">{VERDICT_ICON[verdict]}</span>
      <span>{label}</span>
    </TonePill>
  );
}

/* -------------------------- Integrated assessment -------------------------- */

function IntegratedAssessment({ text }: { text: string }) {
  const zh = useLang() === "zh";
  return (
    <section
      aria-label="Integrated assessment"
      className="rounded-lg border border-border/60 bg-muted/20 px-5 py-4 space-y-2"
    >
      <h3 className="text-base font-semibold text-foreground">
        {zh ? "整体评估" : "Integrated Assessment"}
      </h3>
      <p className="text-sm leading-relaxed text-foreground/90">{text}</p>
    </section>
  );
}

/* -------------------------- Optimization boundary -------------------------- */

function OptimizationBoundary({
  canSolve,
  cannotSolve,
  zh,
}: {
  canSolve: string[];
  cannotSolve: string[];
  zh: boolean;
}) {
  return (
    <section aria-label="Optimization boundary" className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">
        {zh ? "优化边界" : "Optimization Boundary"}
      </h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <BoundaryColumn
          label={zh ? "改写可解决" : "Rewriting can solve"}
          subLabel=""
          items={canSolve}
          tone="positive"
        />
        <BoundaryColumn
          label={zh ? "改写无法解决" : "Rewriting cannot solve"}
          subLabel=""
          items={cannotSolve}
          tone="negative"
        />
      </div>
    </section>
  );
}

function BoundaryColumn({
  label,
  subLabel,
  items,
  tone,
}: {
  label: string;
  subLabel: string;
  items: string[];
  tone: "positive" | "negative";
}) {
  // Preserve the emerald/red palette via inline border + bg accents.
  // GitBook vocabulary: subtle border-foo-500/20 + bg-foo-500/5.
  const accent =
    tone === "positive"
      ? "border-emerald-500/20 bg-emerald-500/5"
      : "border-red-500/20 bg-red-500/5";
  const bullet =
    tone === "positive"
      ? "text-emerald-600 dark:text-emerald-400"
      : "text-red-600 dark:text-red-400";

  return (
    <div className={`rounded-lg border ${accent} px-4 py-3`}>
      <div className="mb-2 flex items-baseline gap-1.5">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <span className="font-mono text-[10px] text-muted-foreground">{subLabel}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">—</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="flex gap-1.5 text-xs text-foreground/85">
              <span className={`select-none ${bullet}`} aria-hidden="true">
                ·
              </span>
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
