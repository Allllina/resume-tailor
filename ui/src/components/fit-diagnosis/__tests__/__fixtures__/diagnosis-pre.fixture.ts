// Phase A test fixture — pre_rewrite fit diagnosis for use across the
// FitDiagnosisPreRewritePanel component tests. Realistic Anker / AIGC
// theme mirroring MOCK_RUNS[0] in ui/src/lib/api.ts so panels render
// against representative narrative shape.
//
// IMPORTANT: at the moment Phase A tests are authored, ui/src/types/
// generated.ts ships `FitDiagnosisPostRewrite` but NOT
// `FitDiagnosisPreRewrite` — Phase B will regenerate the file from
// contracts/schemas/harness-tailor-output.schema.json (which already
// declares the pre_rewrite shape). To keep the test contract
// compileable today, we hand-type the interface here from the schema
// and re-export it. When the generated type lands, Phase B should:
//   1. delete the local interface below,
//   2. switch the import to `import type { FitDiagnosisPreRewrite } from "@/types/generated"`,
//   3. update the `FitDiagnosisPreRewritePanel` props to consume the
//      generated type.
// The hand-typed shape MUST stay byte-identical to the schema (any
// drift is a contract bug — fail loudly).

/* eslint-disable @typescript-eslint/no-explicit-any */

export type Verdict = "strong_match" | "transferable" | "missing";
export type Source =
  | "section_b_priority"
  | "section_c_tier_1"
  | "section_c_tier_2"
  | "section_c_tier_3";
export type Method = "llm" | "llm_partial" | "fallback_no_llm";
export type Confidence = "high" | "moderate" | "low";
export type CompetitivenessRating =
  | "high"
  | "above_mid"
  | "mid"
  | "below_mid"
  | "low";

export interface FitDiagnosisMatrixItem {
  text: string;
  evidence: string;
  verdict: Verdict;
  source: Source;
  bridging_or_closure: string;
}

export interface FitDiagnosisOptimizationBoundary {
  rewriting_can_solve: string[];
  rewriting_cannot_solve: string[];
}

export interface FitDiagnosisMultiJdCoverage {
  jd_id: string;
  jd_title: string;
  coverage_pct: number;
  note: string;
}

/**
 * Hand-typed mirror of the `fit_diagnosis_pre_rewrite` block in
 * contracts/schemas/harness-tailor-output.schema.json. Replace with
 * import from `@/types/generated` once the generator runs in Phase B.
 */
export interface FitDiagnosisPreRewrite {
  sub_skill: "fit-diagnosis-engine";
  mode: "pre_rewrite" | "post_rewrite";
  target_market: "north-america" | "mainland-china" | "hong-kong";
  ppaf_stage: "planning" | "late_feedback";
  invoked_at: string;
  inputs_signature: {
    jd_analysis_id: string;
    competency_profile_id: string;
    current_resume_hash: string | null;
  };
  multi_jd: boolean;
  confidence: Confidence;
  competitiveness_rating: CompetitivenessRating;
  _method: Method;
  matching_matrix: FitDiagnosisMatrixItem[];
  integrated_assessment: string;
  optimization_boundary: FitDiagnosisOptimizationBoundary;
  multi_jd_coverage?: FitDiagnosisMultiJdCoverage[] | null;
  spread_flag?: boolean | null;
}

// ─────────────────────── per-row builders ───────────────────────

export function makeStrongMatchItem(
  overrides: Partial<FitDiagnosisMatrixItem> = {},
): FitDiagnosisMatrixItem {
  return {
    text: "AIGC 内容生产经验,熟悉 Claude / ChatGPT 工作流",
    evidence: "Ipsos RAG pilot + SDIC LangChain pipeline 直接对应 Tier 1 关键词。",
    verdict: "strong_match",
    source: "section_b_priority",
    // Backward-compat invariant: strong_match items have empty
    // bridging_or_closure (no closure path needed when already strong).
    bridging_or_closure: "",
    ...overrides,
  };
}

export function makeTransferableItem(
  overrides: Partial<FitDiagnosisMatrixItem> = {},
): FitDiagnosisMatrixItem {
  return {
    text: "短视频脚本 / 图文模板等 AIGC 媒介产出",
    evidence:
      "现有 case 偏文本生成,需在 bullet 中显化短视频脚本的复用逻辑。",
    verdict: "transferable",
    source: "section_c_tier_1",
    bridging_or_closure:
      "preferred; 把 RAG pilot 重新框架为 AIGC 内容流水线案例,Tier 2 capability 显化",
    ...overrides,
  };
}

export function makeMissingItem(
  overrides: Partial<FitDiagnosisMatrixItem> = {},
): FitDiagnosisMatrixItem {
  return {
    text: "硬件出海 / 跨境电商的真实落地经验",
    evidence:
      "Anker 偏硬件出海,候选人主要 case 在咨询 / 互联网,缺直接硬件经验。",
    verdict: "missing",
    source: "section_c_tier_3",
    bridging_or_closure:
      "preferred; long_term — 1-2 个季度通过跨境内容相关项目积累背景",
    ...overrides,
  };
}

// ────────────────────────── full doc ──────────────────────────

export function makePreRewriteDiagnosis(
  overrides: Partial<FitDiagnosisPreRewrite> = {},
): FitDiagnosisPreRewrite {
  return {
    sub_skill: "fit-diagnosis-engine",
    mode: "pre_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "planning",
    invoked_at: "2026-05-08T10:00:00.000Z",
    inputs_signature: {
      jd_analysis_id: "jd-anker-aigc-001",
      competency_profile_id: "comp-anker-aigc-001",
      current_resume_hash: "sha256:test-hash",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    matching_matrix: [
      makeStrongMatchItem(),
      makeTransferableItem(),
      makeMissingItem(),
    ],
    integrated_assessment:
      "AI 工具实操与产品运营双背景与 JD 的 Tier 1 高度匹配,AIGC 内容生产是可包装项 — 现有 RAG / LangChain 经验需要在 bullet 中显式映射到内容生产流水线。最大缺口是硬件出海行业经验,但 JD 将其列为加分项而非硬卡,可在面试中通过迁移叙事覆盖。",
    optimization_boundary: {
      rewriting_can_solve: [
        "把 RAG pilot 重新框架为 AIGC 内容流水线案例",
        "Summary 中提前出现 AIGC + 产品运营双关键词",
        "技能行将 Claude / ChatGPT 提到首位",
      ],
      rewriting_cannot_solve: [
        "硬件出海 / 跨境电商的真实落地经验缺失",
      ],
    },
    multi_jd_coverage: null,
    spread_flag: null,
    ...overrides,
  };
}

// Stable handle used directly when a test doesn't need overrides.
export const MOCK_PRE_REWRITE: FitDiagnosisPreRewrite = makePreRewriteDiagnosis();
