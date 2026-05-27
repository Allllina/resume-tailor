/**
 * DemoDiagnosis — the run-detail DIAGNOSIS surface for the walkthrough.
 *
 * REUSES the real diagnosis panels verbatim (FitDiagnosisPreRewritePanel =
 * 匹配矩阵 + 整体评估 + 优化边界, FitDiagnosisPostRewritePanel = 双视角 + 6-axis
 * radar + 改进建议, ChangeCard). The production DraftReview wraps these but is
 * query-driven (useRun / useMasters); here we re-create only its header +
 * composition shell (classes copied from src/components/draft-review.tsx) and
 * feed the canned RunDetail straight in. So every panel is the real component
 * with real tokens — only the data source differs.
 *
 * The whole surface is rendered inside a fixed-height viewport with an
 * auto-scroll pan driven by `scroll` (0..1) from useDemoSequence, so it slowly
 * travels 匹配矩阵 → 双视角 → 雷达 → 改进建议 without any user input.
 */
import { useLayoutEffect, useRef, useState } from "react";
import { ChangeCard } from "@/components/change-card";
import { FitDiagnosisPreRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPreRewritePanel";
import { FitDiagnosisPostRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPostRewritePanel";
import { type Lens, type RunDetail } from "@/lib/api";
import { useLang } from "@/lib/lang-context";

const LENS_LABEL_EN: Record<Lens, string> = {
  A_strategy_research: "A Strategy Research",
  B_data_analytics: "B Data Analytics",
  C_product_ops: "C Product Ops",
  D_finance_markets: "D Finance & Markets",
  HC_human_capital: "HC Human Capital",
};

const LENS_LABEL_ZH: Record<Lens, string> = {
  A_strategy_research: "A 战略研究",
  B_data_analytics: "B 数据分析",
  C_product_ops: "C 产品运营",
  D_finance_markets: "D 金融市场",
  HC_human_capital: "HC 人力资本",
};

export function DemoDiagnosis({ run, scroll }: { run: RunDetail; scroll: number }) {
  const zh = useLang() === "zh";
  const LENS_LABEL = zh ? LENS_LABEL_ZH : LENS_LABEL_EN;

  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState(0);

  // Measure how far the content overflows the viewport so the pan covers the
  // full document exactly (no clipped tail, no overscroll).
  useLayoutEffect(() => {
    const measure = () => {
      const vp = viewportRef.current;
      const ct = contentRef.current;
      if (!vp || !ct) return;
      setOverflow(Math.max(0, ct.scrollHeight - vp.clientHeight));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [run]);

  const lens = run.lens_routing?.primary_lens;
  const cards = run.change_cards ?? [];
  const lensLabel = lens ? LENS_LABEL[lens] : null;

  const title =
    [run.jd_context?.company_hint, run.jd_context?.role_title_hint].filter(Boolean).join(" · ") ||
    (zh ? "未命名草稿" : "Untitled draft");
  const loc = run.jd_context?.location_hint;
  const subtitle = [loc, lensLabel && `${lensLabel} lens`].filter(Boolean).join(" · ");

  return (
    <div ref={viewportRef} className="relative h-full overflow-hidden bg-background">
      <div
        ref={contentRef}
        className="will-change-transform"
        style={{ transform: `translateY(${-scroll * overflow}px)` }}
      >
        <main className="mx-auto max-w-2xl px-6 pb-32 pt-8">
          {/* Header — copied from draft-review.tsx */}
          <div className="border-b border-border pb-8">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              {zh ? "草稿" : "Draft"} · {run.run_id.slice(0, 8)}
            </p>
            <h1 className="mt-3 text-3xl text-foreground" style={{ fontFamily: "var(--font-serif)" }}>
              {title}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          </div>

          {/* 匹配矩阵 + 整体评估 + 优化边界 (pre-rewrite) */}
          <div className="mt-6">
            <FitDiagnosisPreRewritePanel diagnosis={run.fit_diagnosis_pre_rewrite} />
          </div>

          {/* 双视角 (HM/HRBP) + 6-axis radar + 改进建议 (post-rewrite) */}
          <div className="mt-6">
            <FitDiagnosisPostRewritePanel diagnosis={run.fit_diagnosis_post_rewrite} />
          </div>

          {/* Changes — the "I made N changes" line + change cards. */}
          <div className="mt-8">
            <p className="text-sm leading-relaxed text-foreground">
              <span className="mr-2 text-primary">✦</span>
              {zh ? (
                <>
                  已从您的{" "}
                  <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {lensLabel ?? "master"}
                  </span>{" "}
                  版本做出 <span className="font-medium">{cards.length} 处修改</span>。
                </>
              ) : (
                <>
                  I made{" "}
                  <span className="font-medium">
                    {cards.length} {cards.length === 1 ? "change" : "changes"}
                  </span>{" "}
                  from your{" "}
                  <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {lensLabel ?? "master"}
                  </span>{" "}
                  master.
                </>
              )}
            </p>
            <div className="mt-4 space-y-3">
              {cards.map((c, i) => (
                <ChangeCard key={i} title={c.title} before={c.before} after={c.after} note={c.note} />
              ))}
            </div>
          </div>

          <div className="mt-12 border-t border-border pt-8">
            <p className="text-center text-xs text-muted-foreground">
              {lensLabel ?? (zh ? "已定制" : "Tailored")} · Pass-3 verify · {zh ? "下载 .tex / PDF 后投递" : "Download .tex / PDF to apply"}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
