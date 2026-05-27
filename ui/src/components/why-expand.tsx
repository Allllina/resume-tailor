import { useState } from "react";
import type {
  CompetencyConfidence,
  CompetencyModel,
  LensRouting,
  RewriteEngineOutput,
} from "@/lib/api";
import { MethodBadge } from "@/components/shared/method-badge";

interface Props {
  lensRouting?: LensRouting;
  competencyModel?: CompetencyModel;
  rewriteEngineOutput?: RewriteEngineOutput;
}

const LENS_LABEL: Record<string, string> = {
  A_strategy_research: "A 战略研究",
  B_data_analytics: "B 数据分析",
  C_product_ops: "C 产品运营",
  D_finance_markets: "D 金融市场",
  HC_human_capital: "HC 人力资本",
};

function lensLabel(lens?: string): string {
  return lens ? (LENS_LABEL[lens] ?? lens) : "—";
}

function formatBlend(blend?: Record<string, number>): string {
  if (!blend) return "—";
  const entries = Object.entries(blend);
  if (entries.length === 0) return "—";
  return entries
    .sort(([, a], [, b]) => b - a)
    .map(([k, v]) => `${k} ${v}%`)
    .join(" · ");
}

const STRING_TRUNCATE = 200;
const BODY_TRUNCATE = 250;
const FIT_DIAGNOSIS_TRUNCATE = 400;
const MAX_BULLETS = 4;
const KEYWORDS_PER_TIER = 6;
const MAX_DECISION_LOG_ENTRIES = 6;

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max).trimEnd()}…` : s;
}

/** Section H subkeys can be `string | string[]`. Normalize to bullet array. */
function toBullets(v: string | string[] | undefined): string[] {
  if (!v) return [];
  if (Array.isArray(v)) {
    return v.filter((x) => typeof x === "string" && x.trim().length > 0);
  }
  return v.trim().length > 0 ? [v] : [];
}

const CONFIDENCE_LABEL: Record<CompetencyConfidence, string> = {
  high: "高",
  moderate: "中",
  low: "低",
};

const CONFIDENCE_TONE: Record<CompetencyConfidence, string> = {
  high: "text-verified",
  moderate: "text-attention",
  low: "text-muted-foreground",
};

export function WhyExpand({ lensRouting, competencyModel, rewriteEngineOutput }: Props) {
  const [open, setOpen] = useState(false);
  const r = lensRouting;
  const cm = competencyModel;

  return (
    <div className="rounded-xl border border-border bg-card/60 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center gap-2 text-left text-sm text-muted-foreground hover:text-foreground transition"
      >
        <span>{open ? "▾" : "▸"}</span>
        Why this version
        <span className="ml-auto text-[11px]">PPAF · 三轴 · Pass 3 trace</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 text-xs">
          <Row label="Primary lens" value={lensLabel(r?.primary_lens)} />
          {r?.secondary_lens ? (
            <Row label="Secondary lens" value={lensLabel(r.secondary_lens)} />
          ) : null}
          <Row label="Scenario" value={r?.scenario_loaded ?? "—"} />
          <Row label="Blend ratio" value={formatBlend(r?.blend_ratio)} />
          <Row label="Pipeline" value="Perception → Planning → Action → Feedback" />

          {cm ? (
            <div className="pt-3 mt-1 border-t border-border space-y-3">
              <div className="flex">
                <MethodBadge method={cm._method} />
              </div>
              <StrategySection h={cm.section_h_strategy_implications} />
              <ConfidenceSection i={cm.section_i_limitations_confidence} />
              <KeywordsSection d={cm.section_d_keyword_architecture} />
            </div>
          ) : null}

          <RewriteSection rewriteOutput={rewriteEngineOutput} />
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-3">
      <span className="text-muted-foreground font-mono">{label}</span>
      <span className="text-foreground/80 font-mono">{value}</span>
    </div>
  );
}

/* ---------------------------------- Strategy --------------------------------- */
// Section H — emphasize_most + top_half_content. Bullet-list form, max 4 each.

function StrategySection({
  h,
}: {
  h?: CompetencyModel["section_h_strategy_implications"];
}) {
  const emphasize = toBullets(h?.emphasize_most).slice(0, MAX_BULLETS);
  const topHalf = toBullets(h?.top_half_content).slice(0, MAX_BULLETS);
  if (emphasize.length === 0 && topHalf.length === 0) return null;

  return (
    <section className="space-y-2">
      <h4 className="font-mono text-muted-foreground">战略指引</h4>
      {emphasize.length > 0 ? (
        <BulletGroup label="重点强调" items={emphasize} />
      ) : null}
      {topHalf.length > 0 ? (
        <BulletGroup label="上半页内容" items={topHalf} />
      ) : null}
    </section>
  );
}

function BulletGroup({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-3">
      <span className="text-muted-foreground font-mono">{label}</span>
      <ul className="space-y-1 text-foreground/80">
        {items.map((it, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-muted-foreground select-none">·</span>
            <span>{truncate(it, STRING_TRUNCATE)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* --------------------------------- Confidence -------------------------------- */
// Section I — confidence enum + free-text body.

function ConfidenceSection({
  i,
}: {
  i?: CompetencyModel["section_i_limitations_confidence"];
}) {
  if (!i) return null;
  let confidence: CompetencyConfidence | undefined;
  let body = "";
  if (typeof i === "string") {
    body = i;
  } else {
    confidence = i.confidence;
    body = i.body ?? "";
  }
  if (!confidence && !body) return null;

  return (
    <section className="space-y-2">
      <h4 className="font-mono text-muted-foreground">信心度</h4>
      <div className="grid grid-cols-[120px_1fr] gap-3">
        <span className="text-muted-foreground font-mono">置信</span>
        <span className="font-mono">
          {confidence ? (
            <span className={CONFIDENCE_TONE[confidence]}>
              {CONFIDENCE_LABEL[confidence]} · {confidence}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </span>
      </div>
      {body ? (
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <span className="text-muted-foreground font-mono">说明</span>
          <span className="text-foreground/80 leading-relaxed">
            {truncate(body, BODY_TRUNCATE)}
          </span>
        </div>
      ) : null}
    </section>
  );
}

/* --------------------------------- Keywords ---------------------------------- */
// Section D — Tier 1 (core) + Tier 2 (capability), 6 chips each.

function KeywordsSection({
  d,
}: {
  d?: CompetencyModel["section_d_keyword_architecture"];
}) {
  const tier1 = (d?.tier_1_core_role ?? []).filter(Boolean).slice(0, KEYWORDS_PER_TIER);
  const tier2 = (d?.tier_2_capability ?? []).filter(Boolean).slice(0, KEYWORDS_PER_TIER);
  if (tier1.length === 0 && tier2.length === 0) return null;

  return (
    <section className="space-y-2">
      <h4 className="font-mono text-muted-foreground">JD 关键词</h4>
      {tier1.length > 0 ? <ChipGroup label="核心岗位" items={tier1} /> : null}
      {tier2.length > 0 ? <ChipGroup label="能力栈" items={tier2} /> : null}
    </section>
  );
}

function ChipGroup({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-3">
      <span className="text-muted-foreground font-mono">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {items.map((it, i) => (
          <span
            key={i}
            className="rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-[11px] text-foreground/80"
          >
            {it}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------- Rewrite --------------------------------- */
// Section A — Fit Diagnosis (4-6 sentence prose, truncate >400 chars).
// Section J — Decision Log (per-experience: chip + decision + rationale).
// Skip entirely on Tier 1 / legacy runs (rewriteOutput undefined or _method
// === "skipped_tier_1").

function RewriteSection({ rewriteOutput }: { rewriteOutput?: RewriteEngineOutput }) {
  const [fitOpen, setFitOpen] = useState(false);
  const [logOpen, setLogOpen] = useState(false);

  if (!rewriteOutput || rewriteOutput._method === "skipped_tier_1") return null;

  const fit = rewriteOutput.section_a_fit_diagnosis?.trim() ?? "";
  const log = rewriteOutput.section_j_decision_log ?? [];
  if (!fit && log.length === 0) return null;

  const fitTruncated = fit.length > FIT_DIAGNOSIS_TRUNCATE;
  const fitDisplay = fitOpen || !fitTruncated ? fit : truncate(fit, FIT_DIAGNOSIS_TRUNCATE);

  const logVisible = logOpen ? log : log.slice(0, MAX_DECISION_LOG_ENTRIES);
  const logHasMore = log.length > MAX_DECISION_LOG_ENTRIES;

  return (
    <section className="pt-3 mt-1 border-t border-border space-y-2">
      <div className="flex items-center gap-2">
        <h4 className="font-mono text-muted-foreground">改写决策</h4>
        <span className="text-muted-foreground/60 font-mono text-[10px]">Rewrite Engine</span>
        <div className="ml-auto">
          <MethodBadge method={rewriteOutput._method} />
        </div>
      </div>

      {fit ? (
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <span className="text-muted-foreground font-mono">适配诊断</span>
          <div className="text-foreground/80 leading-relaxed">
            <span>{fitDisplay}</span>
            {fitTruncated ? (
              <button
                type="button"
                onClick={() => setFitOpen((v) => !v)}
                className="ml-1.5 font-mono text-[11px] text-muted-foreground hover:text-foreground transition"
              >
                {fitOpen ? "Show less" : "Show more"}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {log.length > 0 ? (
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <span className="text-muted-foreground font-mono">改写日志</span>
          <div className="space-y-1.5">
            <ul className="space-y-1.5">
              {logVisible.map((entry, i) => (
                <li key={i} className="flex flex-wrap items-baseline gap-1.5 text-foreground/80">
                  <span className="rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-[10px] text-foreground/80">
                    {entry.experience_id}
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {entry.decision}
                  </span>
                  <span className="text-foreground/80">
                    — {truncate(entry.rationale, STRING_TRUNCATE)}
                  </span>
                </li>
              ))}
            </ul>
            {logHasMore ? (
              <button
                type="button"
                onClick={() => setLogOpen((v) => !v)}
                className="font-mono text-[11px] text-muted-foreground hover:text-foreground transition"
              >
                {logOpen
                  ? "Show less"
                  : `Show ${log.length - MAX_DECISION_LOG_ENTRIES} more`}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
