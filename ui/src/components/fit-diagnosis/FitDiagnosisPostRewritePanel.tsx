// F4 — Fit Diagnosis (post-rewrite) panel.
// Replaces the legacy DualReviewPanel against the new
// fit_diagnosis_post_rewrite schema (see
// contracts/schemas/harness-tailor-output.schema.json).
//
// Field migrations from D07.1 -> F3:
//   - top-level wrapper now carries sub_skill / mode /
//     inputs_signature / multi_jd / confidence (metadata, not rendered).
//   - radar.dimensions[*] gains a NEW per-dim `citation` caption that
//     surfaces below the chart so each axis has a one-line provenance
//     anchor (the F4 addition vs D07.1's name-only labels).
//
// Renders 4 sub-sections (visual order):
//   1. Header strip — title "双视角评估" + sub-line + RatingChip + MethodBadge
//   2. Two-column HM | HRBP cards (highlights/concerns/risk vs hit-rate /
//      hard filters / decision)
//   3. Hand-rolled SVG 6-axis radar + per-dim citation captions
//   4. improvement_suggestions ordered list (capped at 5) with effort pills
//
// GitBook design vocabulary applied:
//   - text-base font-semibold for primary section titles
//   - space-y-6 between sections, p-5 cards, subtle border-border/60
//   - emerald/amber/red palette via TonePill (long_term keeps the
//     pre-existing orange "info" tone — that's the only orange use case
//     and per dispatch we don't add new orange).
//   - hover:bg-muted/40 on interactive suggestion rows
//
// Renders nothing when diagnosis is undefined (graceful absence — historical
// runs / fallback skip; mirrors the legacy DualReviewPanel pattern).
import type { FitDiagnosisPostRewrite } from "@/types/generated";
import { MethodBadge } from "@/components/shared/method-badge";
import { RatingChip } from "@/components/shared/rating-chip";
import { TonePill, type Tone } from "@/components/shared/tone-pill";
import { RadarChart } from "@/components/fit-diagnosis/RadarChart";
import { useLang } from "@/lib/lang-context";

// Schema enforces maxItems: 5 on improvement_suggestions; UI enforces it
// defensively so a partial / fallback payload that ships more doesn't
// break the visual rhythm of the section.
const SUGGESTIONS_CAP = 5;

type HardFilterStatus = FitDiagnosisPostRewrite["hrbp"]["hard_filter_match"][string];
type AdvanceDecision = FitDiagnosisPostRewrite["hrbp"]["advance_decision"];
type Effort = FitDiagnosisPostRewrite["improvement_suggestions"][number]["effort"];

interface FitDiagnosisPostRewritePanelProps {
  diagnosis: FitDiagnosisPostRewrite | undefined;
}

const HARD_FILTER_LABEL_EN: Record<HardFilterStatus, string> = {
  match: "Match",
  mismatch: "Mismatch",
  uncertain: "Uncertain",
};

const HARD_FILTER_LABEL_ZH: Record<HardFilterStatus, string> = {
  match: "符合",
  mismatch: "不符",
  uncertain: "待定",
};

const HARD_FILTER_TONE: Record<HardFilterStatus, Tone> = {
  match: "positive",
  uncertain: "warn",
  mismatch: "negative",
};

const DECISION_LABEL_EN: Record<AdvanceDecision, string> = {
  push_direct: "Push direct",
  push_with_note: "Push with note",
  screen_out: "Screen out",
};

const DECISION_LABEL_ZH: Record<AdvanceDecision, string> = {
  push_direct: "直接推进",
  push_with_note: "附注推进",
  screen_out: "筛除",
};

const DECISION_EN: Record<AdvanceDecision, string> = {
  push_direct: "push direct",
  push_with_note: "push with note",
  screen_out: "screen out",
};

const DECISION_TONE: Record<AdvanceDecision, Tone> = {
  push_direct: "positive",
  push_with_note: "warn",
  screen_out: "negative",
};

const EFFORT_LABEL_EN: Record<Effort, string> = {
  wording: "Wording",
  supplement_project: "Supplement",
  long_term: "Long-term",
};

const EFFORT_LABEL_ZH: Record<Effort, string> = {
  wording: "措辞调整",
  supplement_project: "补充项目",
  long_term: "长期规划",
};

const EFFORT_TONE: Record<Effort, Tone> = {
  wording: "positive",
  supplement_project: "warn",
  // long_term keeps the legacy "info" tone (orange). Per F4 dispatch
  // we don't introduce new orange uses but we preserve existing ones.
  long_term: "info",
};

export function FitDiagnosisPostRewritePanel({
  diagnosis,
}: FitDiagnosisPostRewritePanelProps) {
  const zh = useLang() === "zh";
  // Graceful absence: historical runs from before F3 won't have this
  // field; render nothing rather than a stub card.
  if (!diagnosis) return null;

  return (
    <section
      className="rounded-xl border border-border/60 bg-card overflow-hidden"
      aria-label={zh ? "双视角评估" : "Dual-perspective analysis"}
      role="region"
    >
      {/* Header strip — section title + competitiveness rating chip.
          GitBook vocabulary: heavier title, low-density padding, subtle
          separator. */}
      <header className="flex flex-wrap items-center gap-3 border-b border-border/60 bg-muted/30 px-5 py-3.5">
        <h2
          className="text-base font-semibold text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {zh ? "双视角评估" : "Dual-Perspective Analysis"}
        </h2>
        <span className="font-mono text-[10px] text-muted-foreground">
          {zh ? "契合诊断 · 招聘经理 + HRBP" : "Fit diagnosis · Hiring Manager + HRBP"}
        </span>
        <RatingChip rating={diagnosis.competitiveness_rating} />
        <MethodBadge method={diagnosis._method} />
      </header>

      <div className="px-5 py-5 space-y-6">
        {/* 1. Two-column HM / HRBP cards */}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <HMCard hm={diagnosis.hm} />
          <HRBPCard hrbp={diagnosis.hrbp} />
        </div>

        {/* 2. 6-axis radar chart + per-axis citation captions */}
        <RadarSection dimensions={diagnosis.radar.dimensions} />

        {/* 3. Improvement suggestions (cap at 5) */}
        <ImprovementSuggestions items={diagnosis.improvement_suggestions} />
      </div>
    </section>
  );
}

/* --------------------------------- HM card --------------------------------- */

function HMCard({ hm }: { hm: FitDiagnosisPostRewrite["hm"] }) {
  const zh = useLang() === "zh";
  return (
    <article
      aria-label={zh ? "招聘经理视角" : "Hiring manager view"}
      className="rounded-lg border border-border/60 bg-background/40 px-5 py-4 space-y-3.5"
    >
      <header className="flex items-baseline gap-2">
        <h3 className="text-base font-semibold text-foreground">{zh ? "招聘经理" : "Hiring Manager"}</h3>
        <span className="font-mono text-[10px] text-muted-foreground">HM</span>
      </header>

      <SubList label={zh ? "亮点" : "Highlights"} subLabel="" tone="positive" items={hm.highlights} />
      <SubList label={zh ? "顾虑" : "Concerns"} subLabel="" tone="negative" items={hm.concerns} />

      <div className="space-y-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs font-medium text-foreground">{zh ? "比较风险" : "Comparison Risk"}</span>
        </div>
        <p className="text-xs leading-relaxed text-foreground/85">
          {hm.comparison_risk?.trim() ? hm.comparison_risk : "—"}
        </p>
      </div>
    </article>
  );
}

function SubList({
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
  const zh = useLang() === "zh";
  // emerald for highlights, red for concerns — matches the dispatch's
  // "preserve emerald/amber/red palette" instruction.
  const bullet =
    tone === "positive"
      ? "text-emerald-600 dark:text-emerald-400"
      : "text-red-600 dark:text-red-400";

  return (
    <div className="space-y-1">
      <div className="flex items-baseline gap-1.5">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <span className="font-mono text-[10px] text-muted-foreground">{subLabel}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">{zh ? "无" : "None"}</p>
      ) : (
        <ul className="space-y-1">
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

/* -------------------------------- HRBP card -------------------------------- */

function HRBPCard({ hrbp }: { hrbp: FitDiagnosisPostRewrite["hrbp"] }) {
  const zh = useLang() === "zh";
  const hitPct = Math.round(Math.max(0, Math.min(1, hrbp.keyword_hit_rate)) * 100);
  const filterEntries = Object.entries(hrbp.hard_filter_match) as Array<
    [string, HardFilterStatus]
  >;

  return (
    <article
      aria-label={zh ? "HRBP 视角" : "HRBP view"}
      className="rounded-lg border border-border/60 bg-background/40 px-5 py-4 space-y-3.5"
    >
      <header className="flex items-baseline gap-2">
        <h3 className="text-base font-semibold text-foreground">{zh ? "人力资源" : "HRBP"}</h3>
        <span className="font-mono text-[10px] text-muted-foreground">
          {zh ? "招聘筛选" : "Recruiter screen"}
        </span>
      </header>

      {/* Keyword hit rate — single big-number row with progress bar. */}
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-baseline gap-1.5">
            <span className="text-xs font-medium text-foreground">{zh ? "关键词命中率" : "Keyword Hit Rate"}</span>
          </div>
          <span
            className="font-mono text-sm tabular-nums text-foreground"
            aria-label={`Keyword hit rate ${hitPct}%`}
          >
            {hitPct}%
          </span>
        </div>
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={hitPct}
        >
          <div
            className="h-full bg-emerald-500/70"
            style={{ width: `${hitPct}%` }}
          />
        </div>
      </div>

      {/* Hard filters — key/value pills grid. */}
      <div className="space-y-1.5">
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs font-medium text-foreground">{zh ? "硬性筛选" : "Hard Filters"}</span>
        </div>
        {filterEntries.length === 0 ? (
          <p className="text-xs text-muted-foreground">—</p>
        ) : (
          <ul className="flex flex-wrap gap-1.5">
            {filterEntries.map(([key, status]) => (
              <li key={key}>
                <HardFilterPill name={key} status={status} />
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Advance decision — colored pill + rationale. */}
      <div className="space-y-1.5">
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs font-medium text-foreground">{zh ? "推进决策" : "Advance Decision"}</span>
        </div>
        <DecisionPill decision={hrbp.advance_decision} />
        {hrbp.decision_rationale?.trim() ? (
          <p className="text-xs leading-relaxed text-foreground/85">
            <span className="mr-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {zh ? "说明" : "Rationale"}
            </span>
            {hrbp.decision_rationale}
          </p>
        ) : null}
      </div>
    </article>
  );
}

function HardFilterPill({
  name,
  status,
}: {
  name: string;
  status: HardFilterStatus;
}) {
  const zh = useLang() === "zh";
  const label = zh ? HARD_FILTER_LABEL_ZH[status] : HARD_FILTER_LABEL_EN[status];
  return (
    <TonePill
      tone={HARD_FILTER_TONE[status]}
      ariaLabel={`${name} ${label}`}
    >
      <span className="font-mono text-[10px] opacity-80">{name}</span>
      <span>{label}</span>
    </TonePill>
  );
}

function DecisionPill({ decision }: { decision: AdvanceDecision }) {
  const zh = useLang() === "zh";
  const label = zh ? DECISION_LABEL_ZH[decision] : DECISION_LABEL_EN[decision];
  return (
    <TonePill
      tone={DECISION_TONE[decision]}
      ariaLabel={zh ? `推进决策 ${label}` : `${DECISION_EN[decision]} decision`}
    >
      <span className="font-mono text-[10px] uppercase tracking-wider opacity-80">
        {zh ? "决策" : "Decision"}
      </span>
      <span>{label}</span>
    </TonePill>
  );
}

/* --------------------------------- Radar --------------------------------- */

function RadarSection({
  dimensions,
}: {
  dimensions: FitDiagnosisPostRewrite["radar"]["dimensions"];
}) {
  const zh = useLang() === "zh";
  return (
    <section
      aria-label={zh ? "6维能力雷达" : "6-axis competency radar"}
      className="rounded-lg border border-border/60 bg-muted/20 px-5 py-4 space-y-4"
    >
      <h3 className="text-base font-semibold text-foreground">
        {zh ? "能力雷达" : "Competency Radar"}
        <span className="ml-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground font-normal">
          {zh ? "6维" : "6-axis"}
        </span>
      </h3>
      <RadarChart dimensions={dimensions} />

      {/* Per-axis citation captions — F4 addition. Each axis name + its
          one-line provenance anchor (e.g. "Section G bullet 03"). The
          chart itself is purely visual; this list is the textual / a11y
          anchor that connects each polygon vertex back to a source. */}
      {dimensions.length > 0 ? (
        <ul aria-label="Radar citations" className="space-y-1.5 pt-2">
          {dimensions.map((d, i) => (
            <li
              key={`${d.name}-${i}`}
              className="flex flex-col gap-0.5 text-xs leading-relaxed sm:flex-row sm:items-baseline sm:gap-2"
            >
              <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted-foreground sm:w-[80px]">
                {d.name}
              </span>
              <span className="text-foreground/80">{d.citation}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

/* --------------------------- Improvement suggestions --------------------------- */

function ImprovementSuggestions({
  items,
}: {
  items: FitDiagnosisPostRewrite["improvement_suggestions"];
}) {
  const zh = useLang() === "zh";
  // Defensive cap: schema enforces maxItems: 5, but partial / fallback
  // paths could ship more — slice so the visual rhythm holds.
  const capped = items.slice(0, SUGGESTIONS_CAP);
  return (
    <section aria-label={zh ? "改进建议" : "Improvement suggestions"} className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">
        {zh ? "改进建议" : "Improvement Suggestions"}
      </h3>
      {capped.length === 0 ? (
        <p className="text-xs text-muted-foreground">{zh ? "无" : "None"}</p>
      ) : (
        <ol className="space-y-2">
          {capped.map((item, i) => (
            <li
              key={i}
              className="flex flex-col gap-1.5 rounded-lg border border-border/60 bg-background/40 px-4 py-3 transition hover:bg-muted/40 sm:flex-row sm:items-start sm:gap-3"
            >
              <div className="shrink-0 sm:w-[88px]">
                <EffortPill effort={item.effort} />
              </div>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-sm leading-snug text-foreground">
                  <span className="mr-1.5 font-mono text-[10px] text-muted-foreground tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {item.text}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function EffortPill({ effort }: { effort: Effort }) {
  const zh = useLang() === "zh";
  const label = zh ? EFFORT_LABEL_ZH[effort] : EFFORT_LABEL_EN[effort];
  return (
    <TonePill
      tone={EFFORT_TONE[effort]}
      ariaLabel={zh ? `难度: ${label}` : `Effort: ${label}`}
    >
      <span>{label}</span>
    </TonePill>
  );
}
