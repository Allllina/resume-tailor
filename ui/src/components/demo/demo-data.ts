/**
 * Canned, deterministic demo data for the /demo product walkthrough.
 *
 * WHY this exists (and doesn't reuse mockListRuns / mockGetRun): the app runs
 * with VITE_USE_MOCK=false in .env.local, so the real query layer hits the live
 * backend. The demo must be hermetic (no network, fully reproducible), so we
 * carry our own canned RunSummary[] + RunDetail here and feed them straight
 * into the REAL presentational components as props.
 *
 * Shapes are the real types from lib/api.ts / types/generated.ts — the
 * fit-diagnosis RunDetail mirrors the structure of MOCK_RUNS["mock-anker-aigc"]
 * so the diagnosis panels render 1:1 with production.
 */
import type { RunDetail, RunSummary } from "@/lib/api";

// Fixed "now" used by humanizeAge so the inbox ages read deterministically
// across loops/recordings. We compute ISO strings relative to this anchor.
// (humanizeAge calls Date.now() at render time; the offsets below are large
// enough that the human label is stable for the length of a recording.)
//
// MUST be a static literal — Date.now() differs between SSR and CSR by
// ~1s, causing React hydration mismatches on title attributes.
const HOUR = 3_600_000;
const MIN = 60_000;
const now = new Date("2026-05-25T10:00:00Z").getTime();
const ago = (ms: number) => new Date(now - ms).toISOString();

/**
 * The hero draft the demo "creates" — ByteDance Senior AI PM, routed to C Product Ops.
 * This is the run the agent attaches and the diagnosis view zooms into.
 */
export const DEMO_HERO_RUN_ID = "demo-bytedance-ai-pm";

/**
 * Dense left-list rows. Three groups visible from the start so observers read
 * the full arc without waiting for the hero to appear:
 *
 *   DEEP REWRITE NEEDED  — ByteDance v1 (38%, wrong lens, gate blocked)
 *   REVIEW BEFORE SUBMIT — Meituan (71%), SHEIN (64%)
 *   READY TO SUBMIT      — Tencent (86%), Kuaishou submitted
 *
 * After the agent streams, the hero (ByteDance v2, 84%) joins "READY TO
 * SUBMIT", giving observers a direct before/after in the same company.
 */
export const DEMO_RUNS: RunSummary[] = [
  // ── Gate-blocked first attempt ────────────────────────────────────────────
  // Same JD as the hero, routed to the wrong lens (B_data_analytics).
  // 38% → needs_deep_rewrite → R-18 blocks submission.
  {
    run_id: "demo-bytedance-v1-blocked",
    created_at: ago(90 * MIN),
    verdict: "complete",
    ui_status: "needs_rewrite",
    confidence_tier: "needs_deep_rewrite",
    primary_lens: "B_data_analytics",
    role_title_hint: "Senior AI PM",
    company_hint: "ByteDance",
    location_hint: "Beijing",
    resume_match_score: 38,
    lifecycle_state: "tailored",
    narration: "First rewrite scored 38%, R-18 threshold not met — wrong lens (B Data Analytics). Regenerating with a different lens.",
  },
  // ── Review group ──────────────────────────────────────────────────────────
  {
    run_id: "demo-meituan-growth",
    created_at: ago(26 * MIN),
    verdict: "partial_pending_user",
    ui_status: "pending_human_verify",
    confidence_tier: "review_recommended",
    primary_lens: "C_product_ops",
    role_title_hint: "Growth PM",
    company_hint: "Meituan",
    location_hint: "Beijing",
    resume_match_score: 71,
    lifecycle_state: "tailored",
  },
  {
    run_id: "demo-shein-ba",
    created_at: ago(3 * HOUR),
    verdict: "complete",
    ui_status: "verify",
    confidence_tier: "review_recommended",
    primary_lens: "B_data_analytics",
    role_title_hint: "Business Analytics",
    company_hint: "SHEIN",
    location_hint: "Guangzhou",
    resume_match_score: 64,
    lifecycle_state: "tailored",
  },
  // ── Ready group ───────────────────────────────────────────────────────────
  {
    run_id: "demo-tencent-pm",
    created_at: ago(5 * HOUR),
    verdict: "complete",
    ui_status: "ready",
    confidence_tier: "ready_to_go",
    primary_lens: "C_product_ops",
    role_title_hint: "Strategy PM",
    company_hint: "Tencent",
    location_hint: "Shenzhen",
    resume_match_score: 86,
    lifecycle_state: "tailored",
  },
  {
    run_id: "demo-kuaishou-ops",
    created_at: ago(28 * HOUR),
    verdict: "complete",
    ui_status: "submitted",
    confidence_tier: "ready_to_go",
    primary_lens: "C_product_ops",
    role_title_hint: "Content Ops",
    company_hint: "Kuaishou",
    location_hint: "Beijing",
    resume_match_score: 82,
    lifecycle_state: "applied",
  },
];

/**
 * The hero run as it appears in the dense list once the agent finishes.
 * confidence_tier: "ready_to_go" puts it in the green "Ready to submit" group,
 * giving observers a direct before/after contrast with demo-bytedance-v1-blocked
 * (38%, red "Deep rewrite needed") in the same company.
 */
export const DEMO_HERO_SUMMARY: RunSummary = {
  run_id: DEMO_HERO_RUN_ID,
  created_at: ago(1 * MIN),
  verdict: "complete",
  ui_status: "ready",
  confidence_tier: "ready_to_go",
  primary_lens: "C_product_ops",
  role_title_hint: "Senior AI PM",
  company_hint: "ByteDance",
  location_hint: "Beijing",
  resume_match_score: 84,
  lifecycle_state: "tailored",
  narration: "Switched to C Product Ops lens and regenerated. Match score improved from 38% to 84%, R-18 threshold passed.",
};

/**
 * Full RunDetail for the hero run — drives the diagnosis view (Match Matrix /
 * Dual-Perspective / Radar / Improvement Suggestions / Changes). Structure
 * mirrors the production mock-anker-aigc run so every FitDiagnosis* panel
 * renders fully.
 */
export const DEMO_HERO_DETAIL: RunDetail = {
  run_id: DEMO_HERO_RUN_ID,
  verdict: "complete",
  matched_resume_version: "C_product_ops",
  lens_routing: {
    primary_lens: "C_product_ops",
    scenario_loaded: "internet_pm_aigc",
    blend_ratio: { C: 70, A: 30 },
  },
  change_cards: [
    {
      title: "Summary rewritten for LLM product track",
      before: "Senior PM with expertise in data analytics and user growth.",
      after:
        "AI PM who shipped LLM applications from 0-to-1: RAG retrieval augmentation, Agent workflow orchestration, Prompt evaluation framework. Background in growth and data analytics.",
      note: "Front-loads LLM / Agent / RAG keywords to match JD opening",
    },
    {
      title: "Skills section reordered",
      before: "Data Analytics · Python · A/B Testing · SQL",
      after: "LLM Applications · Prompt Engineering · Python · Data Analytics · A/B Testing",
      note: "AI toolchain moved to top",
    },
    {
      title: "Project — RAG pilot made explicit",
      before: "Built internal knowledge retrieval tool, improving query efficiency.",
      after:
        "Built RAG retrieval-augmented QA system from scratch covering 3 business lines; accuracy +38% vs keyword search.",
      note: "Quantified result + explicit RAG keyword",
    },
    {
      title: "Agent workflow experience added",
      before: "(none)",
      after:
        "Designed multi-step Agent orchestration pipeline, integrated Claude / tool-calling, automated 60% of manual ops steps.",
      note: "New bullet — directly covers JD Tier 1 capability",
    },
  ],
  jd_context: {
    raw_text:
      "Senior AI PM — ByteDance / Own LLM product from 0-to-1, define RAG, Agent, and Prompt evaluation direction, drive cross-team delivery.",
    company_hint: "ByteDance",
    role_title_hint: "Senior AI PM",
    location_hint: "Beijing",
    target_market: "mainland-china",
    created_at: ago(1 * MIN),
  },
  metrics: { total_tokens: 2140, total_claude_calls: 3, elapsed_seconds: 5.1 },
  degradation_events: [],
  competency_model: {
    _method: "llm",
    section_d_keyword_architecture: {
      tier_1_core_role: ["LLM Applications", "RAG", "Agent", "Prompt Engineering"],
      tier_2_capability: ["0-to-1 product", "cross-functional collaboration", "data analytics", "user growth", "A/B testing"],
      tier_3_tools_methods: ["Claude", "LangChain", "Python", "SQL"],
      tier_4_action_verbs: ["define", "drive", "ship", "iterate"],
      tier_5_semantic_equivalents: ["Generative AI", "large language model apps"],
    },
    flat_summary: { confidence: "high" },
  },
  rewrite_engine_output: {
    section_a_fit_diagnosis:
      "Candidate has solid foundations in data analytics and growth. LLM/Agent hands-on experience from RAG pilot and Agent orchestration projects can directly back 0-to-1 product definition capability. Recommend front-loading LLM keywords in Summary and first project bullet; de-emphasize traditional growth details unrelated to AI.",
    section_j_decision_log: [
      {
        experience_id: "01-rag-pilot",
        decision: "rewrote_for_tier_1",
        rationale: "RAG pilot directly maps to Tier 1 keywords",
      },
      {
        experience_id: "02-agent-flow",
        decision: "added_bullet",
        rationale: "Agent orchestration fills 0-to-1 product definition signal",
      },
    ],
    _method: "llm",
  },
  fit_diagnosis_pre_rewrite: {
    sub_skill: "fit-diagnosis-engine",
    mode: "pre_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "planning",
    invoked_at: ago(1 * MIN),
    inputs_signature: {
      jd_analysis_id: "jd-bytedance-ai-pm-001",
      competency_profile_id: "comp-bytedance-ai-pm-001",
      current_resume_hash: "sha256:demo-bytedance-pre",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    matching_matrix: [
      {
        text: "LLM product definition and 0-to-1 delivery capability",
        evidence: "RAG pilot + Agent orchestration project directly maps to Tier 1 keywords with end-to-end ownership.",
        verdict: "strong_match",
        source: "section_b_priority",
        bridging_or_closure: "",
      },
      {
        text: "RAG / retrieval-augmented system design",
        evidence: "Internal knowledge retrieval project has RAG foundations; needs explicit architecture and metrics in bullet.",
        verdict: "transferable",
        source: "section_c_tier_1",
        bridging_or_closure:
          "preferred; reframe internal retrieval project as RAG system, add quantified accuracy improvement",
      },
      {
        text: "Data-driven product decisions and A/B experimentation",
        evidence: "Growth-side experience provides quantified metrics, directly aligned with product decision-making capability.",
        verdict: "strong_match",
        source: "section_c_tier_2",
        bridging_or_closure: "",
      },
      {
        text: "Large-scale consumer LLM product launch experience",
        evidence: "Current experience is internal-tool focused; lacks direct consumer LLM product at hundreds-of-millions scale.",
        verdict: "missing",
        source: "section_c_tier_3",
        bridging_or_closure: "preferred; long_term — build scale experience through consumer AI product projects",
      },
    ],
    integrated_assessment:
      "LLM/Agent hands-on experience and 0-to-1 product capability align strongly with JD Tier 1. RAG experience is packageable — existing internal retrieval project needs to be explicitly mapped as a retrieval-augmented system in bullet points. The main gap is large-scale consumer LLM product experience, but the JD lists it as a plus rather than a hard requirement, coverable in interviews through a transfer narrative.",
    optimization_boundary: {
      rewriting_can_solve: [
        "Reframe internal retrieval project as RAG retrieval-augmented system and add quantified results",
        "Front-load LLM / Agent / RAG keywords in Summary",
        "Add Agent workflow orchestration bullet to cover Tier 1 capability",
      ],
      rewriting_cannot_solve: ["Direct experience shipping consumer-facing LLM products at hundreds-of-millions scale"],
    },
    multi_jd_coverage: null,
    spread_flag: null,
  },
  fit_diagnosis_post_rewrite: {
    sub_skill: "fit-diagnosis-engine",
    mode: "post_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "late_feedback",
    invoked_at: ago(1 * MIN),
    inputs_signature: {
      jd_analysis_id: "jd-bytedance-ai-pm-001",
      competency_profile_id: "comp-bytedance-ai-pm-001",
      current_resume_hash: "sha256:demo-bytedance-post",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    hm: {
      highlights: [
        "RAG pilot + Agent orchestration are genuine 0-to-1 cases, not keyword stuffing",
        "Growth and data analytics background credibly backs product decision-making narrative",
        "Claude / LangChain hands-on experience is rare and especially valuable for AI PM roles",
      ],
      concerns: [
        "No consumer LLM product at scale; needs a transfer narrative in interviews",
        "Agent orchestration project is internal-tool scope; cross-business-unit drive needs more evidence",
      ],
      comparison_risk:
        "Compared to other ByteDance AI PM candidates, slightly weaker on direct consumer LLM product experience; but clearly stronger on LLM/Agent hands-on depth and data-driven structured capability.",
    },
    hrbp: {
      keyword_hit_rate: 0.81,
      hard_filter_match: {
        Education: "match",
        Language: "match",
        Location: "match",
        "Years exp.": "match",
      },
      advance_decision: "push_with_note",
      decision_rationale:
        "Tier 1 keyword hit rate is high, all hard filters pass. Recommend forwarding with a note to hiring manager: focus interview on transfer capability for consumer-scale LLM products and cross-team drive.",
    },
    radar: {
      dimensions: [
        {
          name: "LLM Apps",
          resume_score: 84,
          jd_required: 88,
          citation: "RAG pilot bullet 1 — retrieval-augmented QA system end-to-end",
        },
        {
          name: "Agent Orchestration",
          resume_score: 72,
          jd_required: 82,
          citation: "Section G bullet 04 — multi-step Agent workflow automation",
        },
        {
          name: "0-to-1 Product",
          resume_score: 80,
          jd_required: 80,
          citation: "RAG / Agent projects — full 0-to-1 definition-to-delivery cycle",
        },
        {
          name: "Data Analytics",
          resume_score: 86,
          jd_required: 70,
          citation: "Growth-side A/B experiments + quantified metrics",
        },
        {
          name: "Scale Experience",
          resume_score: 58,
          jd_required: 78,
          citation: "Gap: no consumer-scale LLM product — current cases are internal tools",
        },
        {
          name: "Cross-team Drive",
          resume_score: 78,
          jd_required: 72,
          citation: "Section D bullet 02 — cross-functional ownership",
        },
      ],
    },
    improvement_suggestions: [
      {
        text: "Explicitly label internal retrieval project bullet as 'RAG retrieval-augmented system', front-load Tier 1 keyword",
        effort: "wording",
      },
      {
        text: "Add 'LLM Applications + Agent workflow' dual keywords to first Summary sentence to match JD opening",
        effort: "wording",
      },
      {
        text: "Move Claude / LangChain / Prompt Engineering to top of skills section",
        effort: "wording",
      },
      {
        text: "Add a consumer-facing AI product side project to cover the scale experience gap",
        effort: "supplement_project",
      },
      {
        text: "Consumer-scale LLM product experience is a structural gap; plan to build it through relevant projects over the next 1–2 quarters",
        effort: "long_term",
      },
    ],
  },
};

/** The JD text the composer auto-types in beat 3. */
export const DEMO_JD_TEXT =
  "Senior AI PM — ByteDance / Own LLM product from 0-to-1, define RAG, Agent, and Prompt evaluation direction, drive cross-team delivery.";

/** The agent summary message that streams in token-by-token in beat 5. */
export const DEMO_AGENT_REPLY =
  "First rewrite used B Data Analytics lens — match score 38%, R-18 threshold not met. Switched to C Product Ops lens and regenerated. 7 changes, match score up to 84%, competitiveness above mid, submission threshold passed.";

// ─── Chinese (ZH) dataset ────────────────────────────────────────────────────

export const DEMO_JD_TEXT_ZH =
  "高级 AI 产品经理 — 字节跳动 / 负责 LLM 应用产品从 0 到 1,定义 RAG、Agent、Prompt 评测方向,推动跨团队落地。";

export const DEMO_AGENT_REPLY_ZH =
  "首次改写用 B 数据分析 lens，匹配度 38%，R-18 门槛未达——已切换至 C 产品运营 lens 重新生成。7 处改动，匹配度提升至 84%，竞争力中偏高，投递门槛通过。";

export const DEMO_RUNS_ZH: RunSummary[] = [
  {
    run_id: "demo-bytedance-v1-blocked",
    created_at: ago(90 * MIN),
    verdict: "complete",
    ui_status: "needs_rewrite",
    confidence_tier: "needs_deep_rewrite",
    primary_lens: "B_data_analytics",
    role_title_hint: "高级 AI 产品经理",
    company_hint: "字节跳动",
    location_hint: "北京",
    resume_match_score: 38,
    lifecycle_state: "tailored",
    narration: "首次改写匹配度 38%，R-18 门槛未达，建议重选 lens 后重新生成。",
  },
  {
    run_id: "demo-meituan-growth",
    created_at: ago(26 * MIN),
    verdict: "partial_pending_user",
    ui_status: "pending_human_verify",
    confidence_tier: "review_recommended",
    primary_lens: "C_product_ops",
    role_title_hint: "增长产品经理",
    company_hint: "美团",
    location_hint: "北京",
    resume_match_score: 71,
    lifecycle_state: "tailored",
  },
  {
    run_id: "demo-shein-ba",
    created_at: ago(3 * HOUR),
    verdict: "complete",
    ui_status: "verify",
    confidence_tier: "review_recommended",
    primary_lens: "B_data_analytics",
    role_title_hint: "商业分析",
    company_hint: "SHEIN",
    location_hint: "广州",
    resume_match_score: 64,
    lifecycle_state: "tailored",
  },
  {
    run_id: "demo-tencent-pm",
    created_at: ago(5 * HOUR),
    verdict: "complete",
    ui_status: "ready",
    confidence_tier: "ready_to_go",
    primary_lens: "C_product_ops",
    role_title_hint: "策略产品经理",
    company_hint: "腾讯",
    location_hint: "深圳",
    resume_match_score: 86,
    lifecycle_state: "tailored",
  },
  {
    run_id: "demo-kuaishou-ops",
    created_at: ago(28 * HOUR),
    verdict: "complete",
    ui_status: "submitted",
    confidence_tier: "ready_to_go",
    primary_lens: "C_product_ops",
    role_title_hint: "内容运营",
    company_hint: "快手",
    location_hint: "北京",
    resume_match_score: 82,
    lifecycle_state: "applied",
  },
];

export const DEMO_HERO_SUMMARY_ZH: RunSummary = {
  run_id: DEMO_HERO_RUN_ID,
  created_at: ago(1 * MIN),
  verdict: "complete",
  ui_status: "ready",
  confidence_tier: "ready_to_go",
  primary_lens: "C_product_ops",
  role_title_hint: "高级 AI 产品经理",
  company_hint: "字节跳动",
  location_hint: "北京",
  resume_match_score: 84,
  lifecycle_state: "tailored",
  narration: "重选 C 产品运营 lens 后重新生成，匹配度从 38% 提升至 84%，投递门槛通过。",
};

export const DEMO_HERO_DETAIL_ZH: RunDetail = {
  run_id: DEMO_HERO_RUN_ID,
  verdict: "complete",
  matched_resume_version: "C_product_ops",
  lens_routing: {
    primary_lens: "C_product_ops",
    scenario_loaded: "internet_pm_aigc",
    blend_ratio: { C: 70, A: 30 },
  },
  change_cards: [
    {
      title: "Summary 重写为 LLM 产品方向",
      before: "资深产品经理,擅长数据分析与用户增长。",
      after: "AI 产品经理,主导 LLM 应用从 0 到 1:RAG 检索增强、Agent 工作流编排、Prompt 评测体系。兼具增长与数据分析背景。",
      note: "前置 LLM / Agent / RAG 关键词,匹配 JD 顶部表述",
    },
    {
      title: "技能行重排序",
      before: "数据分析 · Python · A/B 测试 · SQL",
      after: "LLM 应用 · Prompt Engineering · Python · 数据分析 · A/B 测试",
      note: "AI 工具栈提到首位",
    },
    {
      title: "项目经历 — RAG 试点显化",
      before: "搭建内部知识检索工具,提升查询效率。",
      after: "从 0 搭建 RAG 检索增强问答系统,覆盖 3 个业务线,准确率较关键词检索提升 38%。",
      note: "量化结果 + 显式 RAG 关键词",
    },
    {
      title: "Agent 工作流经验补充",
      before: "(无)",
      after: "设计多步 Agent 编排流程,接入 Claude / 工具调用,将人工运营环节自动化 60%。",
      note: "新增 bullet — 直接覆盖 JD Tier 1 capability",
    },
  ],
  jd_context: {
    raw_text: "高级 AI 产品经理 — 字节跳动 / 负责 LLM 应用产品从 0 到 1,定义 RAG、Agent、Prompt 评测方向,推动跨团队落地。",
    company_hint: "字节跳动",
    role_title_hint: "高级 AI 产品经理",
    location_hint: "北京",
    target_market: "mainland-china",
    created_at: ago(1 * MIN),
  },
  metrics: { total_tokens: 2140, total_claude_calls: 3, elapsed_seconds: 5.1 },
  degradation_events: [],
  competency_model: {
    _method: "llm",
    section_d_keyword_architecture: {
      tier_1_core_role: ["LLM 应用", "RAG", "Agent", "Prompt Engineering"],
      tier_2_capability: ["产品从 0 到 1", "跨团队协作", "数据分析", "用户增长", "A/B 测试"],
      tier_3_tools_methods: ["Claude", "LangChain", "Python", "SQL"],
      tier_4_action_verbs: ["定义", "推动", "落地", "迭代"],
      tier_5_semantic_equivalents: ["生成式 AI", "大模型应用"],
    },
    flat_summary: { confidence: "high" },
  },
  rewrite_engine_output: {
    section_a_fit_diagnosis:
      "候选人在数据分析与增长侧基础扎实,LLM / Agent 实操经验来自 RAG 试点与 Agent 编排项目,可作为 0→1 产品定义能力的直接背书。建议在 Summary 与首段项目中前置 LLM 关键词,弱化与 AI 无关的传统增长细节。",
    section_j_decision_log: [
      { experience_id: "01-rag-pilot", decision: "rewrote_for_tier_1", rationale: "RAG 试点直接对应 Tier 1 关键词" },
      { experience_id: "02-agent-flow", decision: "added_bullet", rationale: "Agent 编排经验补全 0→1 产品定义信号" },
    ],
    _method: "llm",
  },
  fit_diagnosis_pre_rewrite: {
    sub_skill: "fit-diagnosis-engine",
    mode: "pre_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "planning",
    invoked_at: ago(1 * MIN),
    inputs_signature: {
      jd_analysis_id: "jd-bytedance-ai-pm-001",
      competency_profile_id: "comp-bytedance-ai-pm-001",
      current_resume_hash: "sha256:demo-bytedance-pre",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    matching_matrix: [
      {
        text: "LLM 应用产品从 0 到 1 的定义与落地能力",
        evidence: "RAG 试点 + Agent 编排项目直接对应 Tier 1 关键词,具备端到端 ownership。",
        verdict: "strong_match",
        source: "section_b_priority",
        bridging_or_closure: "",
      },
      {
        text: "RAG / 检索增强系统设计经验",
        evidence: "内部知识检索项目已具备 RAG 雏形,需在 bullet 中显式标注架构与指标。",
        verdict: "transferable",
        source: "section_c_tier_1",
        bridging_or_closure: "preferred; 把内部检索项目重新框架为 RAG 系统,补充准确率提升等量化结果",
      },
      {
        text: "数据驱动的产品决策与 A/B 实验",
        evidence: "增长侧经验给出量化指标背书,与产品决策能力直接对齐。",
        verdict: "strong_match",
        source: "section_c_tier_2",
        bridging_or_closure: "",
      },
      {
        text: "大规模 C 端 LLM 产品上线经验",
        evidence: "现有经验偏内部工具,缺直接面向亿级用户的 C 端 LLM 产品落地。",
        verdict: "missing",
        source: "section_c_tier_3",
        bridging_or_closure: "preferred; long_term — 通过 C 端 AI 产品项目积累规模化经验",
      },
    ],
    integrated_assessment:
      "LLM / Agent 实操与产品 0→1 能力与 JD 的 Tier 1 高度匹配,RAG 经验是可包装项 — 现有内部检索项目需在 bullet 中显式映射为检索增强系统。最大缺口是大规模 C 端 LLM 产品经验,但 JD 将其列为加分项而非硬卡,可在面试中以迁移叙事覆盖。",
    optimization_boundary: {
      rewriting_can_solve: [
        "把内部检索项目重新框架为 RAG 检索增强系统并补充量化结果",
        "Summary 中前置 LLM / Agent / RAG 关键词",
        "新增 Agent 工作流编排 bullet 覆盖 Tier 1 capability",
      ],
      rewriting_cannot_solve: ["亿级 C 端 LLM 产品的真实规模化落地经验缺失"],
    },
    multi_jd_coverage: null,
    spread_flag: null,
  },
  fit_diagnosis_post_rewrite: {
    sub_skill: "fit-diagnosis-engine",
    mode: "post_rewrite",
    target_market: "mainland-china",
    ppaf_stage: "late_feedback",
    invoked_at: ago(1 * MIN),
    inputs_signature: {
      jd_analysis_id: "jd-bytedance-ai-pm-001",
      competency_profile_id: "comp-bytedance-ai-pm-001",
      current_resume_hash: "sha256:demo-bytedance-post",
    },
    multi_jd: false,
    confidence: "high",
    competitiveness_rating: "above_mid",
    _method: "llm",
    hm: {
      highlights: [
        "RAG 试点 + Agent 编排是真实 0→1 case,而非堆砌关键词",
        "增长与数据分析背景为产品决策能力背书,叙事可信",
        "Claude / LangChain hands-on 经验稀缺,在 AI 产品方向尤为加分",
      ],
      concerns: [
        "缺亿级 C 端 LLM 产品上线 case,需在面试中补足规模化叙事",
        "Agent 编排项目偏内部场景,跨业务线推动力需进一步佐证",
      ],
      comparison_risk:
        "对比同样投递字节 AI PM 的候选人,在大规模 C 端产品的直接经验上略弱;但在 LLM / Agent 实操深度与数据驱动的结构化能力上明显胜出。",
    },
    hrbp: {
      keyword_hit_rate: 0.81,
      hard_filter_match: { 学历: "match", 语言: "match", 地点: "match", 年限: "match" },
      advance_decision: "push_with_note",
      decision_rationale:
        "Tier 1 关键词命中率高,硬性条件全部通过。建议附备注转招聘经理:面试聚焦 C 端规模化 LLM 产品的迁移能力与跨团队推动经验。",
    },
    radar: {
      dimensions: [
        { name: "LLM 应用", resume_score: 84, jd_required: 88, citation: "RAG 试点 bullet 1 — 检索增强问答系统端到端落地" },
        { name: "Agent 编排", resume_score: 72, jd_required: 82, citation: "Section G bullet 04 — 多步 Agent 工作流自动化" },
        { name: "产品 0→1", resume_score: 80, jd_required: 80, citation: "RAG / Agent 项目从定义到落地全链路" },
        { name: "数据分析", resume_score: 86, jd_required: 70, citation: "增长侧 A/B 实验 + 量化指标背书" },
        { name: "规模化经验", resume_score: 58, jd_required: 78, citation: "缺亿级 C 端产品 — 现有 case 偏内部工具" },
        { name: "跨团队协作", resume_score: 78, jd_required: 72, citation: "Section D bullet 02 — cross-functional ownership" },
      ],
    },
    improvement_suggestions: [
      { text: "把内部检索项目的 bullet 显式标注为 'RAG 检索增强系统',Tier 1 关键词前置", effort: "wording" },
      { text: "Summary 首句加入 'LLM 应用 + Agent 工作流' 双关键词,匹配 JD 顶部表述", effort: "wording" },
      { text: "技能行把 Claude / LangChain / Prompt Engineering 提到首位", effort: "wording" },
      { text: "补充一段面向 C 端的 AI 产品 side project,覆盖规模化经验缺口", effort: "supplement_project" },
      { text: "亿级 C 端 LLM 产品经验属结构性缺口,建议未来 1-2 个季度通过相关项目积累", effort: "long_term" },
    ],
  },
};
