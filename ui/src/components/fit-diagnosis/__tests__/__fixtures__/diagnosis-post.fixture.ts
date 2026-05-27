// Phase A test fixture — post_rewrite fit diagnosis for use across the
// FitDiagnosisPostRewritePanel + RadarChart component tests. Realistic
// Anker / AIGC theme mirroring MOCK_RUNS[0].dual_review in
// ui/src/lib/api.ts but updated for the new schema:
//   - radar.dimensions[*].citation is a NEW field (per
//     contracts/schemas/harness-tailor-output.schema.json#fit_diagnosis_post_rewrite)
//   - top-level wrapper now carries sub_skill / mode / inputs_signature etc.
//
// `FitDiagnosisPostRewrite` already exists in @/types/generated, so we
// import it directly from there (no hand-typed shadow needed).
import type { FitDiagnosisPostRewrite } from "@/types/generated";

export type Effort = FitDiagnosisPostRewrite["improvement_suggestions"][number]["effort"];

export function makePostRewriteDiagnosis(
  overrides: Partial<FitDiagnosisPostRewrite> = {},
): FitDiagnosisPostRewrite {
  return {
    sub_skill: "fit-diagnosis-engine",
    mode: "post_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "late_feedback",
    invoked_at: "2026-05-08T10:30:00.000Z",
    inputs_signature: {
      jd_analysis_id: "jd-anker-aigc-001",
      competency_profile_id: "comp-anker-aigc-001",
      current_resume_hash: "sha256:test-hash-post",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    hm: {
      highlights: [
        "Ipsos RAG pilot 直接对应 AIGC 内容流水线 — 用真实 case 而非堆砌关键词",
        "Kearney + Mercer 量化背景给 BA 思维背书,产品运营叙事可信",
        "Claude / LangChain hands-on 经验稀缺,在内容方向尤为加分",
      ],
      concerns: [
        "短视频脚本 / 图文模板的端到端落地 case 偏少,需在面试中补足",
        "硬件出海行业经验缺失,跨境内容场景下需要叙事迁移",
      ],
      comparison_risk:
        "对比同样投递 Anker AIGC 实习的候选人,在硬件 / 跨境电商的直接经验上略弱;但在 AI 工具实操深度与咨询出身的结构化能力上明显胜出。",
    },
    hrbp: {
      keyword_hit_rate: 0.74,
      hard_filter_match: {
        学历: "match",
        语言: "match",
        地点: "uncertain",
        时间: "match",
      },
      advance_decision: "push_with_note",
      decision_rationale:
        "Tier 1 关键词命中率高,硬性条件除地点存疑外全部通过。建议附备注转招聘经理:面试聚焦短视频脚本生产经验与跨境内容场景适配能力。",
    },
    radar: {
      dimensions: [
        {
          name: "AI 工具",
          resume_score: 82,
          jd_required: 85,
          citation: "Ipsos RAG pilot bullet 1 — Claude 工作流端到端落地",
        },
        {
          name: "内容生产",
          resume_score: 65,
          jd_required: 80,
          citation: "Section G bullet 03 — 内容流水线案例",
        },
        {
          name: "产品运营",
          resume_score: 78,
          jd_required: 75,
          citation: "Kearney 战略框架 + Mercer 量化背景",
        },
        {
          name: "数据分析",
          resume_score: 85,
          jd_required: 70,
          citation: "Mercer 模型 + Kearney 数据驱动",
        },
        {
          name: "行业经验",
          resume_score: 55,
          jd_required: 70,
          citation: "无硬件出海经验 — 跨境电商 case 缺失",
        },
        {
          name: "沟通协作",
          resume_score: 80,
          jd_required: 70,
          citation: "Section D bullet 02 — cross-functional ownership",
        },
      ],
    },
    improvement_suggestions: [
      {
        text: "把 Ipsos RAG pilot 的 bullet 显式标注为 'AIGC 内容流水线' 案例,Tier 1 关键词前置",
        effort: "wording",
      },
      {
        text: "Summary 首句加入 'AIGC 内容生产 + 产品运营' 双关键词,匹配 JD 顶部表述",
        effort: "wording",
      },
      {
        text: "技能行把 Claude / ChatGPT / Midjourney 提到首位,显化 AI 工具栈优先级",
        effort: "wording",
      },
      {
        text: "补充一段短视频脚本 / 图文模板的小型 side project,直接覆盖 JD Tier 2 capability 缺口",
        effort: "supplement_project",
      },
      {
        text: "硬件出海行业经验属于结构性缺口,建议未来 1-2 个季度通过跨境内容相关项目积累背景",
        effort: "long_term",
      },
    ],
    ...overrides,
  };
}

export const MOCK_POST_REWRITE: FitDiagnosisPostRewrite = makePostRewriteDiagnosis();
