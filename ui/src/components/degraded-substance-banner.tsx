// Gate 1 (v0.6.1, R-18) — degraded-substance banner.
//
// Renders when a run's verdict is `degraded_no_substance` (the R-18 quality
// floor demoted what would otherwise be `complete`). Picks one of four copy
// variants by reading substance_check diagnostic fields — the order matters
// because LLM-unreachable + low-rating can co-occur and the LLM-down message
// is the most actionable.
//
// Spec: docs/plans/2026-05-12-gate1-verdict-substance-floor.md Phase B.4
import type { SubstanceCheck } from "@/lib/api";

interface Props {
  check?: SubstanceCheck;
}

const RATING_LABEL: Record<SubstanceCheck["competitiveness_rating"], string> = {
  high: "高",
  above_mid: "中上",
  mid: "中等",
  below_mid: "中下",
  low: "低",
  unknown: "未知",
};

function pickVariant(check: SubstanceCheck): {
  headline: string;
  detail: string;
  cta?: string;
} {
  const methodMissing =
    check.post_rewrite_method === "fallback_no_llm" ||
    check.post_rewrite_method === "absent";

  if (methodMissing && check.diagnostic_llm_unreachable) {
    return {
      headline: "LLM 不可达，本次运行未真正改写简历",
      detail:
        "Post-rewrite 评估走了 fallback，没有 LLM 的真实输出。请确认 LLM proxy / API key 配置，然后点 Regenerate 重新跑这一次。",
      cta: "现在的 .tex 等同于你的 master，没有针对这份 JD 的改写。",
    };
  }

  if (methodMissing) {
    const failed = check.diagnostic_failed_sub_skills ?? [];
    return {
      headline: "Post-rewrite 评估服务异常",
      detail:
        failed.length > 0
          ? `下列 sub-skill 走了 fallback：${failed.join("、")}。`
          : "Post-rewrite 没有跑出 LLM 结果。",
      cta: "排查后重新生成，或先以当前 .tex 自行核对。",
    };
  }

  if (check.pass3_verdict === "failed") {
    return {
      headline: "真实性验证失败",
      detail:
        "Pass 3 真实性核查崩了，本次运行没有通过 R-1/R-2/R-3 兜底。",
      cta: "请检查日志后重跑。",
    };
  }

  const rating = check.competitiveness_rating;
  return {
    headline: `系统判定改写后简历对 JD 契合度仅到 ${RATING_LABEL[rating]}`,
    detail:
      "R-18 投递质量门槛要求至少 中上 (above_mid)。当前这版改写未达门槛——直接投可能浪费 HC 配额。",
    cta: "建议：换 lens 方向 (重选 direction)、补充 experience bank、或 Regenerate 让模型重新尝试。",
  };
}

export function DegradedSubstanceBanner({ check }: Props) {
  // Defensive — verdict could be degraded_no_substance on a legacy state.json
  // that predates the substance_check field. Surface a generic message rather
  // than crash.
  if (!check) {
    return (
      <section
        role="alert"
        className="mt-6 rounded-xl border border-error/30 bg-error/5 px-4 py-4"
      >
        <header className="flex items-center gap-2 text-sm font-medium text-error">
          <span aria-hidden>！</span>
          质量门槛未达标（R-18）
        </header>
        <p className="mt-2 text-sm text-foreground/85">
          这次运行未通过 R-18 投递质量门槛，但缺少诊断细节（可能是旧版 state.json）。
        </p>
      </section>
    );
  }

  const variant = pickVariant(check);

  return (
    <section
      role="alert"
      aria-labelledby="degraded-substance-headline"
      className="mt-6 rounded-xl border border-error/30 bg-error/5 px-4 py-4"
    >
      <header
        id="degraded-substance-headline"
        className="flex items-center gap-2 text-sm font-medium text-error"
      >
        <span aria-hidden>！</span>
        {variant.headline}
      </header>
      <p className="mt-2 text-sm text-foreground/85">{variant.detail}</p>
      {variant.cta ? (
        <p className="mt-1.5 text-xs text-muted-foreground">{variant.cta}</p>
      ) : null}
      <details className="mt-3 text-xs text-muted-foreground">
        <summary className="cursor-pointer hover:text-foreground">
          诊断细节
        </summary>
        <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono">
          <dt>competitiveness_rating</dt>
          <dd>{check.competitiveness_rating}</dd>
          <dt>post_rewrite_method</dt>
          <dd>{check.post_rewrite_method}</dd>
          <dt>pass3_verdict</dt>
          <dd>{check.pass3_verdict}</dd>
          {check.diagnostic_llm_unreachable ? (
            <>
              <dt>llm_unreachable</dt>
              <dd>true</dd>
            </>
          ) : null}
          {check.diagnostic_failed_sub_skills &&
          check.diagnostic_failed_sub_skills.length > 0 ? (
            <>
              <dt>failed_sub_skills</dt>
              <dd>{check.diagnostic_failed_sub_skills.join(", ")}</dd>
            </>
          ) : null}
          {typeof check.diagnostic_change_card_count === "number" ? (
            <>
              <dt>change_card_count</dt>
              <dd>{check.diagnostic_change_card_count}</dd>
            </>
          ) : null}
          <dt>method_version</dt>
          <dd>{check.method_version}</dd>
        </dl>
      </details>
    </section>
  );
}
