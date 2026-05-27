/**
 * API client for the harness backend.
 *
 * Types mirror contracts/schemas/run-summary, run-list, harness-tailor-output,
 * harness-tailor-input, user-profile. Toggle real backend vs inline mocks via VITE_USE_MOCK.
 *
 * All fetches send the `X-User-Id` header (Wave 2.7 multi-user foundation).
 */
import { getUserId } from "./user";
// Wave 5 F4 — fit_diagnosis_pre_rewrite + fit_diagnosis_post_rewrite types
// are auto-generated from contracts/schemas/harness-tailor-output.schema.json
// (replacing the deprecated MatchMatrix + DualReview hand-typed stubs that
// lived inline here through the F2-F3 backend transition).
import type {
  FitDiagnosisPostRewrite,
  FitDiagnosisPreRewrite,
} from "@/types/generated";

// ============ Types ============

export type Verdict =
  | "complete"
  | "partial_pending_user"
  | "failed"
  | "degraded_to_manual"
  | "degraded_no_substance"
  | "user_aborted";

export type UiStatus =
  | "ready"
  | "verify"
  | "needs_rewrite"
  | "blocked"
  | "submitted"
  | "pending_human_verify"
  | "degraded_no_substance";

export type ConfidenceTier = "ready_to_go" | "review_recommended" | "needs_deep_rewrite";

// Wave 4 Step C — manual job lifecycle tracking per ARCHITECTURE.md §6.
export type LifecycleState =
  | "tailored"
  | "applied"
  | "oa"
  | "interview"
  | "rejected"
  | "offer"
  | "archived"
  | "dismissed";

export interface LifecycleEvent {
  state: LifecycleState;
  timestamp: string;
  note?: string;
  channel?: string;
}

export interface RunLifecycle {
  current_state: LifecycleState;
  events: LifecycleEvent[];
}

export type Lens =
  | "A_strategy_research"
  | "B_data_analytics"
  | "C_product_ops"
  | "D_finance_markets"
  | "HC_human_capital";

export type TargetMarket = "north-america" | "mainland-china" | "hong-kong";

// per harness-tailor-input.schema.json — mode is "auto" | "manual", NOT "tier1"
export type TailorMode = "auto" | "manual";

export interface RunSummary {
  run_id: string;
  created_at: string;
  verdict: Verdict;
  ui_status: UiStatus;
  primary_lens?: Lens;
  role_title_hint?: string;
  company_hint?: string;
  location_hint?: string;
  narration?: string;
  degradation_count?: number;
  confidence_tier?: ConfidenceTier;
  resume_match_score?: number;
  lifecycle_state?: LifecycleState;
  tier_assigned?: 1 | 2 | 3;
  matched_resume_version?: string;
}

export interface MatchScores {
  resume_match_score: number;
  confidence_tier: ConfidenceTier;
  method: string;
  degradation_count: number;
  lens_routing_confidence: number | null;
}

export interface RunList {
  runs: RunSummary[];
  total?: number;
}

export interface ChangeCard {
  title: string;
  before: string;
  after: string;
  note?: string;
  source_event?: string;
}

export interface DegradationEvent {
  stage: string;
  reason: string;
  fallback_taken: string;
}

export interface JdContext {
  raw_text?: string;
  company_hint?: string;
  role_title_hint?: string;
  location_hint?: string;
  target_market?: TargetMarket;
  created_at?: string;
}

export interface LensRouting {
  primary_lens?: Lens;
  secondary_lens?: Lens;
  blend_ratio?: Record<string, number>;
  scenario_loaded?: string;
}

// Wave 4 Step B — role-competency-extractor structured output.
// Spec: packages/strategy-modules/role-competency-extractor/output-schema.md
// UI renders only sections D, H, I (other sections are noise for end users).
export type CompetencyConfidence = "high" | "moderate" | "low";

export interface CompetencyModel {
  section_d_keyword_architecture?: {
    tier_1_core_role?: string[];
    tier_2_capability?: string[];
    tier_3_tools_methods?: string[];
    tier_4_action_verbs?: string[];
    tier_5_semantic_equivalents?: string[];
  };
  section_h_strategy_implications?: {
    emphasize_most?: string | string[];
    de_emphasize?: string | string[];
    top_half_content?: string | string[];
    natural_keyword_placement?: string | string[];
    common_mistakes?: string | string[];
  };
  section_i_limitations_confidence?:
    | string
    | { confidence?: CompetencyConfidence; body?: string };
  flat_summary?: { confidence?: CompetencyConfidence; [k: string]: unknown };
  _method?: "llm" | "llm_partial" | "fallback_no_llm";
}

// Wave 4 D.2b — resume-rewrite-engine structured output (Tier 2/3 runs).
// Spec: packages/strategy-modules/resume-rewrite-engine/output-schema.md
// UI renders only Section A (fit diagnosis) + Section J (decision log);
// other sections feed the .tex render path or remain advanced/debug.
export interface RewriteDecisionLogEntry {
  experience_id: string;
  decision: string;
  rationale: string;
}

export interface RewriteBullet {
  id: string;
  text: string;
  claimed_facts?: string[];
  experience_id: string;
  final_category: number;
  disambiguator_parenthetical?: string | null;
}

export interface RewriteEngineOutput {
  section_a_fit_diagnosis?: string;
  section_b_priority_signals?: unknown[];
  section_c_experience_prioritization?: Record<string, unknown>;
  section_d_resume_narrative?: string;
  section_e_cross_company_variations?: string;
  section_f_section_by_section_guidance?: Record<string, unknown>;
  section_g_bullets?: RewriteBullet[];
  section_h_resume_structure?: Record<string, unknown>;
  section_i_final_resume_draft?: string;
  section_j_decision_log?: RewriteDecisionLogEntry[];
  _method?: "llm" | "llm_partial" | "fallback_no_llm" | "skipped_tier_1";
}

// Wave 4 D — three-pass experience selection trace. Advanced debug data;
// surfaced as a type so future debug panels can read it. Not rendered today.
export interface ExperienceTrace {
  experience_id: string;
  pass_a_tier: string;
  pass_b_tier: string;
  pass_b_lift: "mis_classification" | "pure_recognition" | "none";
  pass_c_tier: string;
  pass_c_ai_pressure: "none" | "weak_minus_1" | "none_minus_2";
  final_category: 1 | 2 | 3 | 4;
}

export interface RunDetail {
  run_id: string;
  verdict: Verdict;
  matched_resume_version?: string;
  lens_routing?: LensRouting;
  change_cards?: ChangeCard[];
  jd_context?: JdContext;
  metrics?: {
    total_tokens?: number;
    total_claude_calls?: number;
    elapsed_seconds?: number;
  };
  degradation_events?: DegradationEvent[];
  trace?: unknown;
  tex_artifact_path?: string;
  pdf_artifact_path?: string;
  match_scores?: MatchScores;
  lifecycle?: RunLifecycle;
  competency_model?: CompetencyModel;
  rewrite_engine_output?: RewriteEngineOutput;
  experience_selection_trace?: ExperienceTrace[];
  // Wave 5 F1 — fit_diagnosis_pre_rewrite (PLANNING-stage Section 4:
  // matching matrix + integrated assessment + optimization boundary +
  // optional multi-JD coverage). Generated type lives in @/types/generated
  // (source of truth: contracts/schemas/harness-tailor-output.schema.json).
  fit_diagnosis_pre_rewrite?: FitDiagnosisPreRewrite;
  // Wave 5 F3 — fit_diagnosis_post_rewrite (late-FEEDBACK Section 8:
  // HM + HRBP simulation + 6-axis radar with citations + improvement
  // suggestions). Consumes fit_diagnosis_pre_rewrite + the rewrite output.
  fit_diagnosis_post_rewrite?: FitDiagnosisPostRewrite;
  // Gate 1 (v0.6.1, R-18) — quality floor evaluation. Absent on pre-Gate-1
  // runs (treat as legacy / unverified). See SubstanceCheck below.
  substance_check?: SubstanceCheck;
}

// Gate 1 (v0.6.1, R-18) — quality floor for verdict=complete.
// Source of truth: contracts/schemas/harness-tailor-output.schema.json
// `substance_check`. passes=false demotes verdict to "degraded_no_substance"
// (see backend harness/verdict/substance_check.py).
export interface SubstanceCheck {
  passes: boolean;
  competitiveness_rating:
    | "high"
    | "above_mid"
    | "mid"
    | "below_mid"
    | "low"
    | "unknown";
  post_rewrite_method: "llm" | "llm_partial" | "fallback_no_llm" | "absent";
  pass3_verdict: "complete" | "partial" | "failed" | "absent";
  method_version: string;
  // Diagnostic fields — UI banner uses these to pick copy variant; not part
  // of the gate logic itself.
  diagnostic_failed_sub_skills?: string[];
  diagnostic_llm_unreachable?: boolean;
  diagnostic_change_card_count?: number;
}

// Re-export the schema-derived fit-diagnosis types so consumers (e.g. the
// FitDiagnosisPre/PostRewritePanel components) can import them from
// @/lib/api alongside RunDetail when convenient. Canonical definitions
// still live in @/types/generated.
export type { FitDiagnosisPostRewrite, FitDiagnosisPreRewrite };

export interface TailorRequest {
  mode: TailorMode;
  jd: {
    source: "paste" | "url" | "scraper";
    raw_text: string;
    company_hint?: string;
    role_title_hint?: string;
    location_hint?: string;
  };
  candidate_profile_ref: string;
  target_market: TargetMarket;
  lens_hint?: Lens;
}

export interface TailorResponse {
  run_id: string;
  verdict: Verdict;
}

// ============ User profile / upload types (Wave 2.7) ============

export type ResumeFormat = "md" | "tex" | "docx" | "pdf";

export type ScoringStatus = "queued" | "scoring" | "done" | "failed";

export type RecognitionLevel = "high" | "medium" | "low" | "none";
export type FitLevel = "core" | "adjacent" | "weak" | "missing";
export type AiFluencyLevel = "high" | "moderate" | "low" | "none";

export type MasterKind = "full" | "tailored_for_lens" | "mixed";

export interface UserProfile {
  user_id: string;
  created_at: string;
  last_updated?: string;
  candidate_names: string[];
  master_format?: ResumeFormat;
  master_uploaded_at?: string;
  master_parse_confidence?: number;
  master_parse_meta?: {
    format?: string;
    file_bytes?: number;
    warnings?: string[];
    section_count?: number;
    section_names?: string[];
    raw_tex_bytes?: number;
  };
  experience_count?: number;
  experiences_scored_count?: number;
  target_market_default?: TargetMarket;
  // C.1 onboarding redesign — per-lens master targeting
  target_lens_default?: Lens;
  target_lens_secondary?: Lens[];
  master_kind?: MasterKind;
}

export interface ExperienceSummary {
  id: string;
  file_name: string;
  scoring_status: ScoringStatus;
  uploaded_at?: string;
  scored_at?: string;
  recognition_per_industry?: Record<string, RecognitionLevel>;
  vertical_fit_per_lens?: Record<string, FitLevel>;
  ai_digital_fluency?: AiFluencyLevel;
  scoring_fallback?: boolean;
}

export interface UserStatus {
  user_id: string;
  profile: UserProfile | null;
  has_resume: boolean;
  experience_count: number;
  experiences_scored_count: number;
  experiences: ExperienceSummary[];
}

export interface UploadResumeResponse {
  ok: boolean;
  format: ResumeFormat;
  confidence: number;
  warnings: string[];
  section_count: number;
}

export interface UploadExperiencesResponse {
  ok: boolean;
  experiences: Array<{
    id: string;
    file_name: string;
    scoring_status: ScoringStatus;
  }>;
}

export interface PatchUserProfileBody {
  candidate_names?: string[];
  target_market_default?: TargetMarket;
  // Onboarding redesign: user can declare what kind of resume they uploaded.
  // Backend's user-profile.schema.json accepts this optional field.
  master_kind?: MasterKind;
}

// ============ Multi-lens master onboarding (C.1 / C.2) ============
//
// Per docs/plans/2026-05-07-onboarding-multi-lens-master.md: the user picks 1
// primary direction + N optional secondary directions, and the backend keeps a
// per-lens master.tex generated for each. Status flows
// `absent -> generating -> ready` (or stays `absent` if generation never ran).

export interface LensTargets {
  primary: Lens;
  secondary: Lens[];
}

export type MasterGenStatus = "ready" | "generating" | "absent";

export interface MasterStatus {
  has_master: boolean;
  generated_at: string | null;
  method: string | null;
  status: MasterGenStatus;
}

/**
 * Backend GET /api/users/masters returns one entry per lens the user has
 * declared as primary or secondary. Lenses the user hasn't picked are absent
 * from the map — callers should treat missing keys as "not a target".
 */
export type MastersResponse = Partial<Record<Lens, MasterStatus>>;

// Gate 2 (v0.6.2) — LLM health endpoint types.
// Source of truth: contracts/schemas/llm-health.schema.json
export type LLMHealthStatus = "healthy" | "degraded" | "down";

export interface LLMLive {
  status: LLMHealthStatus;
  provider: string;
  consecutive_failures: number;
  circuit_open: boolean;
  seconds_since_last_success: number | null;
  seconds_since_last_failure: number | null;
}

export interface LLMHealth {
  harness_version: string;
  schema_version: string;
  llm: LLMLive;
}

/** Thrown by jsonFetch when the backend returns a non-2xx response. */
export class ApiError extends Error {
  status: number;
  detail?: string;
  /** Structured detail object from FastAPI 503 bodies (code, sub_skill, etc.). */
  detailObj?: Record<string, unknown>;
  constructor(
    status: number,
    message: string,
    detail?: string,
    detailObj?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.detailObj = detailObj;
  }
}

// ============ Config ============

const env = (typeof import.meta !== "undefined" ? import.meta.env : {}) as Record<
  string,
  string | undefined
>;

export const API_BASE = env.VITE_API_BASE ?? "http://127.0.0.1:8001";
// Default to real backend. Set VITE_USE_MOCK=true only for UI-only dev
// when no harness backend is running.
export const USE_MOCK = (env.VITE_USE_MOCK ?? "false") === "true";

// ============ Real client ============

function withUserHeader(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers ?? {});
  // Don't override an explicitly-set X-User-Id (test hooks etc.)
  if (!headers.has("X-User-Id")) headers.set("X-User-Id", getUserId());
  return { ...init, headers };
}

/** Best-effort extract of FastAPI's `{detail: "..."}` body for cleaner errors.
 *  Also handles structured 503 bodies where detail is an object. */
function parseErrorDetail(text: string): {
  message: string;
  detailObj?: Record<string, unknown>;
} {
  try {
    const j = JSON.parse(text);
    if (j && typeof j.detail === "string") return { message: j.detail };
    if (j && j.detail && typeof j.detail === "object") {
      const d = j.detail as Record<string, unknown>;
      const msg =
        typeof d.message === "string"
          ? d.message
          : typeof d.reason === "string"
            ? d.reason
            : typeof d.code === "string"
              ? d.code
              : JSON.stringify(d).slice(0, 200);
      return { message: msg, detailObj: d };
    }
  } catch {
    /* not JSON */
  }
  return { message: text.slice(0, 300) };
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, withUserHeader(init));
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const { message: detail, detailObj } = parseErrorDetail(text);
    throw new ApiError(r.status, `${r.status} ${r.statusText}: ${detail}`, detail, detailObj);
  }
  // 204 No Content / empty body — return undefined as T (callers handle void)
  if (r.status === 204) return undefined as T;
  const ct = r.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) return undefined as T;
  return r.json() as Promise<T>;
}

async function multipartFetch<T>(path: string, body: FormData): Promise<T> {
  // NOTE: deliberately do NOT set Content-Type — fetch sets the multipart
  // boundary automatically. We only attach X-User-Id.
  const r = await fetch(`${API_BASE}${path}`, withUserHeader({ method: "POST", body }));
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const { message: detail, detailObj } = parseErrorDetail(text);
    throw new ApiError(r.status, `${r.status} ${r.statusText}: ${detail}`, detail, detailObj);
  }
  return r.json() as Promise<T>;
}

export async function listRuns(): Promise<RunList> {
  if (USE_MOCK) return mockListRuns();
  return jsonFetch<RunList>("/api/runs");
}

export async function getRun(id: string): Promise<RunDetail> {
  if (USE_MOCK) return mockGetRun(id);
  return jsonFetch<RunDetail>(`/api/runs/${encodeURIComponent(id)}`);
}

export async function postTailor(req: TailorRequest): Promise<TailorResponse> {
  if (USE_MOCK) return mockPostTailor(req);
  return jsonFetch<TailorResponse>("/api/tier1-tailor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function patchRunLifecycle(
  id: string,
  body: { state: LifecycleState; note?: string; channel?: string },
): Promise<{ ok: true; current_state: LifecycleState; event: LifecycleEvent }> {
  if (USE_MOCK) return mockPatchRunLifecycle(id, body);
  return jsonFetch<{ ok: true; current_state: LifecycleState; event: LifecycleEvent }>(
    `/api/runs/${encodeURIComponent(id)}/lifecycle`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

// ============ Wave 4 D.5 — Pass 3 user-trust ============

export interface Pass3UnsourcedClaim {
  claim: string;
  action: "remove" | "mark_TBD" | "ask_user";
  rationale?: string;
}

export interface Pass3VerifiedFact {
  claim: string;
  source: string;
  confidence?: number;
}

export interface Pass3Bullet {
  bullet_id: string;
  verdict: "complete" | "partial" | "failed";
  verified_facts: Pass3VerifiedFact[];
  unsourced_claims: Pass3UnsourcedClaim[];
  ask_user: { question: string; context: string }[];
}

export type VerifyClaimDecision = "approve" | "reject" | "edit";

export interface VerifyClaimRequest {
  bullet_id: string;
  claim_index: number;
  decision: VerifyClaimDecision;
  edited_text?: string;
  note?: string;
}

export interface VerifyClaimResponse {
  run_id: string;
  decided_count: number;
  total_unsourced: number;
  all_decided: boolean;
  verdict: Verdict;
  ui_status: UiStatus;
}

export interface VerificationLogEvent {
  decided_at: string;
  bullet_id: string;
  claim_index: number;
  claim_snapshot: string;
  decision: VerifyClaimDecision;
  edited_text?: string;
  note?: string;
}

export interface VerificationLog {
  run_id: string;
  events: VerificationLogEvent[];
}

export interface Pass3Response {
  bullets: Pass3Bullet[];
  verification_log: VerificationLog;
}

export async function getPass3(id: string): Promise<Pass3Response> {
  if (USE_MOCK) return mockGetPass3(id);
  return jsonFetch<Pass3Response>(`/api/runs/${encodeURIComponent(id)}/pass3`);
}

export async function postVerifyClaim(
  id: string,
  body: VerifyClaimRequest,
): Promise<VerifyClaimResponse> {
  if (USE_MOCK) return mockPostVerifyClaim(id, body);
  return jsonFetch<VerifyClaimResponse>(
    `/api/runs/${encodeURIComponent(id)}/verify-claim`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export function getTexUrl(id: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(id)}/tex`;
}

export function getPdfUrl(id: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(id)}/pdf`;
}

// ============ User profile / upload endpoints (Wave 2.7) ============

export async function getUserStatus(): Promise<UserStatus> {
  if (USE_MOCK) return mockUserStatus();
  return jsonFetch<UserStatus>("/api/users/me");
}

export async function getUserMasterTex(): Promise<string> {
  // Plain-text endpoint — 404 if no master uploaded.
  const r = await fetch(`${API_BASE}/api/users/me/master/tex`, withUserHeader());
  if (!r.ok) {
    const { message: detail, detailObj } = parseErrorDetail(await r.text().catch(() => ""));
    throw new ApiError(r.status, `${r.status} ${r.statusText}: ${detail}`, detail, detailObj);
  }
  return r.text();
}

export async function getLensMasterTex(lens: Lens): Promise<string> {
  const r = await fetch(`${API_BASE}/api/users/masters/${lens}/tex`, withUserHeader());
  if (!r.ok) {
    const { message: detail, detailObj } = parseErrorDetail(await r.text().catch(() => ""));
    throw new ApiError(r.status, `${r.status} ${r.statusText}: ${detail}`, detail, detailObj);
  }
  return r.text();
}

// Gate 2 (v0.6.2) — GET /api/health (LLM health snapshot).
// Always hits the real backend — no mock (monitoring, not content data).
export async function getHealth(): Promise<LLMHealth> {
  return jsonFetch<LLMHealth>("/api/health");
}

export async function uploadResume(file: File): Promise<UploadResumeResponse> {
  if (USE_MOCK) return mockUploadResume(file);
  const fd = new FormData();
  fd.append("file", file);
  return multipartFetch<UploadResumeResponse>("/api/users/profile/upload-resume", fd);
}

export async function uploadExperiences(files: File[]): Promise<UploadExperiencesResponse> {
  if (USE_MOCK) return mockUploadExperiences(files);
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  return multipartFetch<UploadExperiencesResponse>("/api/users/experiences/upload", fd);
}

export async function deleteExperience(
  expId: string,
): Promise<{ ok: boolean; experience_count: number }> {
  if (USE_MOCK) return mockDeleteExperience();
  return jsonFetch<{ ok: boolean; experience_count: number }>(
    `/api/users/experiences/${encodeURIComponent(expId)}`,
    { method: "DELETE" },
  );
}

export async function patchUserProfile(body: PatchUserProfileBody): Promise<UserStatus> {
  if (USE_MOCK) return mockPatchUserProfile(body);
  return jsonFetch<UserStatus>("/api/users/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteUser(): Promise<{ ok: boolean }> {
  if (USE_MOCK) return { ok: true };
  return jsonFetch<{ ok: boolean }>("/api/users/me", { method: "DELETE" });
}

// ============ Multi-lens master endpoints (C.1) ============

export async function setLensTargets(
  body: LensTargets,
): Promise<{ ok: boolean; primary: Lens; secondary: Lens[] }> {
  if (USE_MOCK) return mockSetLensTargets(body);
  return jsonFetch<{ ok: boolean; primary: Lens; secondary: Lens[] }>(
    "/api/users/lens-targets",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function getMasters(): Promise<MastersResponse> {
  if (USE_MOCK) return mockGetMasters();
  return jsonFetch<MastersResponse>("/api/users/masters");
}

export async function generateMaster(
  lens: Lens,
): Promise<{ ok: boolean; lens: Lens; status: string }> {
  if (USE_MOCK) return mockGenerateMaster(lens);
  return jsonFetch<{ ok: boolean; lens: Lens; status: string }>(
    "/api/users/masters/generate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lens }),
    },
  );
}

export async function deleteMaster(lens: Lens): Promise<{ ok: boolean }> {
  if (USE_MOCK) return mockDeleteMaster(lens);
  return jsonFetch<{ ok: boolean }>(
    `/api/users/masters/${encodeURIComponent(lens)}`,
    { method: "DELETE" },
  );
}

// ============ Mocks ============
// Used when VITE_USE_MOCK=true. Hand-built to mirror what backend produces.

const MOCK_RUNS: RunDetail[] = [
  {
    run_id: "mock-anker-aigc",
    verdict: "complete",
    matched_resume_version: "C_product_ops",
    lens_routing: {
      primary_lens: "C_product_ops",
      scenario_loaded: "internet_pm_aigc",
      blend_ratio: { C: 70, A: 30 },
    },
    change_cards: [
      {
        title: "Skills row reordered",
        before: "数据分析 · AI 工具 · Python",
        after: "AI 工具 · 数据分析 · Python",
        note: "AI 工具 → first (was second)",
      },
      {
        title: "Summary regenerated",
        before: "(no Summary section)",
        after:
          "兼具 BA 思维与 AI 工具实操,在 3 个项目中应用 AIGC 内容生产, 包括短视频脚本与图文模板. Hands-on with Claude / 数据分析 / Python.",
        note: "Tone shifted toward C_product_ops vocabulary",
      },
    ],
    jd_context: {
      raw_text: "Anker AIGC 内容实习生岗位描述:擅长 Claude/ChatGPT、Prompt Engineering...",
      company_hint: "Anker",
      role_title_hint: "AIGC 内容实习生",
      location_hint: "深圳",
      target_market: "mainland-china",
      created_at: new Date(Date.now() - 2 * 60_000).toISOString(),
    },
    metrics: { total_tokens: 1832, total_claude_calls: 2, elapsed_seconds: 4.2 },
    degradation_events: [],
    competency_model: {
      _method: "llm",
      section_d_keyword_architecture: {
        tier_1_core_role: ["AIGC", "AI Agent", "RAG", "Prompt Engineering"],
        tier_2_capability: [
          "内容生产流水线",
          "短视频脚本",
          "产品运营",
          "数据分析",
          "用户洞察",
          "A/B 测试",
        ],
        tier_3_tools_methods: ["Claude", "ChatGPT", "Midjourney", "Python", "SQL"],
        tier_4_action_verbs: ["搭建", "迭代", "驱动", "落地"],
        tier_5_semantic_equivalents: ["生成式 AI", "大模型应用"],
      },
      section_h_strategy_implications: {
        emphasize_most: [
          "AI 驱动的产品运营经验,尤其是 Prompt Engineering 流水线",
          "短视频/图文 AIGC 内容生产的端到端 case",
          "对 Claude/ChatGPT 的 hands-on 调优能力",
        ],
        de_emphasize: ["与内容/AI 无关的传统 BA 项目细节"],
        top_half_content: [
          "Summary 必须出现 AIGC + 产品运营双关键词",
          "首段技能行把 AI 工具置于最前",
        ],
        natural_keyword_placement:
          "Prompt Engineering 应嵌入项目描述而非堆叠在技能行;RAG 出现在最近一段 case 的方法层。",
        common_mistakes: [
          "把 AI 工具当作单纯 buzzword 罗列",
          "忽视内容生产链路上的运营指标",
        ],
      },
      section_i_limitations_confidence: {
        confidence: "moderate",
        body: "JD 较短且偏内容方向,核心岗位职责描述清晰但对量化指标(DAU/转化率)没有明确预期。Tier 1 关键词高置信,Tier 2 capability 部分基于行业经验推断,候选人可酌情对齐。",
      },
      flat_summary: { confidence: "moderate" },
    },
    rewrite_engine_output: {
      section_a_fit_diagnosis:
        "Candidate demonstrates strong analytical foundations from Kearney + Mercer; AI / LLM exposure is moderate (LangChain at SDIC + RAG pilot at Ipsos). Top-half should foreground prompt engineering pipeline experience. Weakness: limited live AIGC product ownership signal — recommend reframing the Ipsos RAG pilot as a proxy for shipped AIGC content workflows, and amplifying the Claude-driven analysis cadence at SDIC.",
      section_g_bullets: [
        {
          id: "01-kearney-1",
          experience_id: "01-kearney",
          text: "Built strategic frameworks for OSAT growth — proxy for analytical rigor in AIGC roadmap planning",
          claimed_facts: ["OSAT growth strategy", "5-year framework"],
          final_category: 1,
          disambiguator_parenthetical: null,
        },
      ],
      section_j_decision_log: [
        {
          experience_id: "01-kearney",
          decision: "rewrote_for_tier_2",
          rationale: "Strategy lens transfer to AIGC roadmap fit",
        },
        {
          experience_id: "02-ipsos",
          decision: "rewrote_for_tier_2",
          rationale: "RAG pilot aligns with prompt engineering Tier 2 keyword",
        },
        {
          experience_id: "03-sdic",
          decision: "rewrote_for_tier_2",
          rationale: "LangChain hands-on directly maps to AI 工具 capability",
        },
        {
          experience_id: "06-projects",
          decision: "skipped_cat_4",
          rationale: "Cat 4 — projects don't match the AIGC PM lens",
        },
      ],
      _method: "llm",
    },
    // Anker / AIGC themed pre-rewrite fit diagnosis. Mirrors the narrative
    // in fit_diagnosis_post_rewrite below so the run reads coherently
    // end-to-end. mock-jd-business below intentionally OMITS both
    // fit_diagnosis_* fields to demo graceful absence on historical /
    // fallback runs.
    fit_diagnosis_pre_rewrite: {
      sub_skill: "fit-diagnosis-engine",
      mode: "pre_rewrite",
      target_market: "mainland-china",
      ppaf_stage: "planning",
      invoked_at: "2026-05-08T10:00:00.000Z",
      inputs_signature: {
        jd_analysis_id: "jd-anker-aigc-001",
        competency_profile_id: "comp-anker-aigc-001",
        current_resume_hash: "sha256:mock-anker-aigc-pre",
      },
      multi_jd: false,
      confidence: "high",
      competitiveness_rating: "above_mid",
      _method: "llm",
      matching_matrix: [
        {
          text: "AIGC 内容生产经验,熟悉 Claude / ChatGPT 工作流",
          evidence: "Ipsos RAG pilot + SDIC LangChain pipeline 直接对应 Tier 1 关键词。",
          verdict: "strong_match",
          source: "section_b_priority",
          bridging_or_closure: "",
        },
        {
          text: "短视频脚本 / 图文模板等 AIGC 媒介产出",
          evidence: "现有 case 偏文本生成,需在 bullet 中显化短视频脚本的复用逻辑。",
          verdict: "transferable",
          source: "section_c_tier_1",
          bridging_or_closure:
            "preferred; 把 RAG pilot 重新框架为 AIGC 内容流水线案例,Tier 2 capability 显化",
        },
        {
          text: "产品运营 / 数据分析双背景",
          evidence: "Kearney + Mercer 给出量化指标背书,与 BA 思维直接对齐。",
          verdict: "strong_match",
          source: "section_c_tier_2",
          bridging_or_closure: "",
        },
        {
          text: "硬件+内容跨界视野",
          evidence: "Anker 偏硬件出海,候选人主要 case 在咨询 / 互联网,缺直接硬件经验。",
          verdict: "missing",
          source: "section_c_tier_3",
          bridging_or_closure:
            "preferred; long_term — 1-2 个季度通过跨境内容相关项目积累硬件出海背景",
        },
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
    },
    // Anker / AIGC themed post-rewrite fit diagnosis (Step 8 双视角评估
    // + 6-axis radar with citations + improvement suggestions). Mirrors
    // the narrative in fit_diagnosis_pre_rewrite above so the run reads
    // coherently end-to-end.
    fit_diagnosis_post_rewrite: {
      sub_skill: "fit-diagnosis-engine",
      mode: "post_rewrite",
      target_market: "mainland-china",
      ppaf_stage: "late_feedback",
      invoked_at: "2026-05-08T10:30:00.000Z",
      inputs_signature: {
        jd_analysis_id: "jd-anker-aigc-001",
        competency_profile_id: "comp-anker-aigc-001",
        current_resume_hash: "sha256:mock-anker-aigc-post",
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
        keyword_hit_rate: 0.78,
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
    },
  },
  {
    run_id: "mock-jd-business",
    verdict: "complete",
    matched_resume_version: "B_data_analytics",
    lens_routing: {
      primary_lens: "B_data_analytics",
      scenario_loaded: "internet_business_analyst",
      blend_ratio: { B: 80, A: 20 },
    },
    change_cards: [
      {
        title: "Skills row reordered",
        before: "Excel · SQL · Tableau",
        after: "SQL · Tableau · Excel",
        note: "SQL lifted on JD signal",
      },
    ],
    jd_context: {
      role_title_hint: "商业分析",
      company_hint: "京东",
      location_hint: "北京",
      target_market: "mainland-china",
      created_at: new Date(Date.now() - 90 * 60_000).toISOString(),
    },
    metrics: { total_tokens: 1100, total_claude_calls: 1, elapsed_seconds: 3.8 },
    degradation_events: [
      {
        stage: "action",
        reason: "summary writer rate-limited",
        fallback_taken: "skip summary regen",
      },
    ],
    rewrite_engine_output: {
      section_a_fit_diagnosis:
        "Candidate's BA / consulting background is a good structural match but quantitative depth (SQL, dashboarding) shows up only in fragments. Recommend foregrounding the JD-side Tableau + Excel modeling work and downplaying the strategy-research framing.",
      section_j_decision_log: [
        {
          experience_id: "01-kearney",
          decision: "rewrote_for_tier_2",
          rationale: "BA framing fits 商业分析 Tier 1",
        },
        {
          experience_id: "04-mercer",
          decision: "rewrote_for_tier_2",
          rationale: "Quant modeling as proxy for SQL / Tableau Tier 2",
        },
      ],
      _method: "fallback_no_llm",
    },
  },
];

function deriveUiStatus(run: RunDetail): UiStatus {
  if (run.verdict === "failed") return "blocked";
  if (run.verdict === "degraded_no_substance") return "degraded_no_substance";
  if (run.verdict === "complete") {
    return (run.degradation_events?.length ?? 0) > 0 ? "verify" : "ready";
  }
  return "blocked";
}

export function humanizeAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 120_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)} min ago`;
  if (ms < 7_200_000) return "1 hour ago";
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)} hours ago`;
  if (ms < 86_400_000 * 2) return "yesterday";
  if (ms < 86_400_000 * 7) return new Date(iso).toLocaleDateString(undefined, { weekday: "short" });
  return new Date(iso).toLocaleDateString();
}

// User-facing direction labels. Backend IDs (A_strategy_research, etc.) are
// internal — never surface the letter prefixes in the UI. Labels here are
// intentionally broad so a stranger can self-select without needing context
// on the original 5-bucket taxonomy. Custom user-defined directions are a
// v0.6 capability — see docs/plans/2026-05-11-lens-taxonomy-configurability.md.
export const LENS_LABELS_ZH: Record<Lens, string> = {
  A_strategy_research: "Strategy & Research",
  B_data_analytics: "Data & Analytics",
  C_product_ops: "Product & Operations",
  D_finance_markets: "Finance & Markets",
  HC_human_capital: "Talent & HR",
};

export const LENS_DESCRIPTIONS_EN: Record<Lens, string> = {
  A_strategy_research:
    "Strategy consulting · corporate strategy · industry research · policy / think-tank",
  B_data_analytics:
    "Business analyst · BI · data analyst · data science (applied) · analytics engineer",
  C_product_ops:
    "Product manager · product ops · growth · ops · internet / tech generalist",
  D_finance_markets:
    "Investment banking · markets / trading · buy-side / asset management · corporate finance",
  HC_human_capital:
    "HRBP · talent acquisition · comp & benefits · L&D · people analytics",
};

export const LENSES: Lens[] = [
  "A_strategy_research",
  "B_data_analytics",
  "C_product_ops",
  "D_finance_markets",
  "HC_human_capital",
];

// Coming-soon role families. These are NOT registered in the backend playbook
// taxonomy yet — the cards render disabled with a "Coming soon" tooltip so a
// stranger landing on /setup sees the product roadmap, not a closed 5-option
// world. Authoring the playbooks moves an entry from here into LENSES in v0.6
// (see docs/plans/2026-05-11-lens-taxonomy-configurability.md).
export interface PlaceholderLens {
  id: string;
  label_en: string;
  description_en: string;
}

export const LENS_PLACEHOLDERS: PlaceholderLens[] = [
  {
    id: "SW_software_eng",
    label_en: "Software Engineering",
    description_en: "Backend · frontend · full-stack · SRE · DevOps · platform / infra",
  },
  {
    id: "ML_machine_learning",
    label_en: "Machine Learning",
    description_en: "Applied ML · MLE · ML research · MLOps · data science (modeling)",
  },
  {
    id: "AI_agent_eng",
    label_en: "AI / Agent Engineering",
    description_en: "LLM apps · prompt eng · agent / RAG systems · AI product eng",
  },
  {
    id: "QA_quality_eng",
    label_en: "QA & Test Engineering",
    description_en: "Test automation · SDET · QA lead · release engineering",
  },
  {
    id: "LG_legal_compliance",
    label_en: "Legal & Compliance",
    description_en: "In-house counsel · compliance · privacy · regulatory affairs",
  },
  {
    id: "MK_marketing_brand",
    label_en: "Marketing & Brand",
    description_en: "Brand · growth marketing · content · PR · creative",
  },
];

// Industry/sector selector — v0.5 MVP renders the picker, stores choice
// locally so it persists across reloads, but the playbook layer doesn't
// branch on industry yet (only `target_market` does). v0.6 turns this into
// a profile field with industry-aware scoring + playbook overlays.
export interface IndustryOption {
  id: string;
  label_en: string;
  description_en: string;
  active: boolean; // false = visible-but-not-yet-wired (no industry-specific playbook)
}

export const INDUSTRIES: IndustryOption[] = [
  {
    id: "tech_internet",
    label_en: "Tech & Internet",
    description_en: "Software, internet platforms, AI, consumer apps",
    active: true,
  },
  {
    id: "finance",
    label_en: "Finance",
    description_en: "IB, asset management, private equity, fintech, markets",
    active: true,
  },
  {
    id: "consulting",
    label_en: "Consulting & Strategy",
    description_en: "MBB, Big-4 advisory, boutique, in-house strategy",
    active: true,
  },
  {
    id: "cross_industry",
    label_en: "Cross-industry",
    description_en: "Not locked to one sector — pick playbook by role family",
    active: true,
  },
  {
    id: "healthcare",
    label_en: "Healthcare & Life Sciences",
    description_en: "Hospitals, biotech, pharma, medical devices, health-tech",
    active: false,
  },
  {
    id: "education",
    label_en: "Education",
    description_en: "EdTech, K-12, higher-ed, training & talent dev",
    active: false,
  },
  {
    id: "retail_cpg",
    label_en: "Retail & CPG",
    description_en: "Consumer goods, e-commerce, retail ops, supply chain",
    active: false,
  },
  {
    id: "manufacturing",
    label_en: "Manufacturing & Industrial",
    description_en: "Hardware, automotive, semiconductors, industrial systems",
    active: false,
  },
  {
    id: "media_entertainment",
    label_en: "Media & Entertainment",
    description_en: "Content, gaming, publishing, streaming",
    active: false,
  },
  {
    id: "government_nonprofit",
    label_en: "Government & Nonprofit",
    description_en: "Public sector, NGO, policy, think tanks",
    active: false,
  },
];

function lensLabelZh(lens?: string): string {
  if (!lens) return "";
  return LENS_LABELS_ZH[lens as Lens] ?? "";
}

function toSummary(r: RunDetail): RunSummary {
  const created = r.jd_context?.created_at ?? new Date().toISOString();
  const lens = r.lens_routing?.primary_lens;
  const lensLabel = lensLabelZh(lens);
  const degCount = r.degradation_events?.length ?? 0;
  const tail =
    degCount === 0
      ? "no issues."
      : degCount === 1
        ? `${r.degradation_events![0].stage} stage degraded.`
        : `${degCount} stages degraded.`;
  return {
    run_id: r.run_id,
    created_at: created,
    verdict: r.verdict,
    ui_status: deriveUiStatus(r),
    primary_lens: lens,
    role_title_hint: r.jd_context?.role_title_hint,
    company_hint: r.jd_context?.company_hint,
    location_hint: r.jd_context?.location_hint,
    narration: lensLabel
      ? `I tailored this ${humanizeAge(created)}. ${lensLabel} lens, ${tail}`
      : `I tailored this ${humanizeAge(created)}. ${tail}`,
    degradation_count: degCount,
  };
}

async function mockListRuns(): Promise<RunList> {
  await new Promise((r) => setTimeout(r, 200));
  const runs = MOCK_RUNS.map(toSummary).sort((a, b) => b.created_at.localeCompare(a.created_at));
  return { runs, total: runs.length };
}

async function mockGetRun(id: string): Promise<RunDetail> {
  await new Promise((r) => setTimeout(r, 200));
  const r = MOCK_RUNS.find((x) => x.run_id === id);
  if (!r) throw new Error(`mock: run ${id} not found`);
  return r;
}

async function mockPostTailor(_req: TailorRequest): Promise<TailorResponse> {
  await new Promise((r) => setTimeout(r, 600));
  return { run_id: "mock-anker-aigc", verdict: "complete" };
}

async function mockPatchRunLifecycle(
  id: string,
  body: { state: LifecycleState; note?: string; channel?: string },
): Promise<{ ok: true; current_state: LifecycleState; event: LifecycleEvent }> {
  await new Promise((r) => setTimeout(r, 100));
  const run = MOCK_RUNS.find((x) => x.run_id === id);
  if (!run) throw new ApiError(404, `mock: run ${id} not found`);
  const event: LifecycleEvent = {
    state: body.state,
    timestamp: new Date().toISOString(),
    ...(body.note ? { note: body.note } : {}),
    ...(body.channel ? { channel: body.channel } : {}),
  };
  const prev = run.lifecycle ?? { current_state: "tailored" as LifecycleState, events: [] };
  run.lifecycle = {
    current_state: body.state,
    events: [...prev.events, event],
  };
  return { ok: true, current_state: body.state, event };
}

async function mockGetPass3(id: string): Promise<Pass3Response> {
  await new Promise((r) => setTimeout(r, 80));
  return { bullets: [], verification_log: { run_id: id, events: [] } };
}

async function mockPostVerifyClaim(
  id: string,
  _body: VerifyClaimRequest,
): Promise<VerifyClaimResponse> {
  await new Promise((r) => setTimeout(r, 80));
  return {
    run_id: id,
    decided_count: 1,
    total_unsourced: 1,
    all_decided: true,
    verdict: "complete",
    ui_status: "ready",
  };
}

// In-memory mock state for user upload flows
let _mockState: UserStatus = {
  user_id: "mock-user",
  profile: null,
  has_resume: false,
  experience_count: 0,
  experiences_scored_count: 0,
  experiences: [],
};

async function mockUserStatus(): Promise<UserStatus> {
  await new Promise((r) => setTimeout(r, 80));
  return _mockState;
}

async function mockUploadResume(file: File): Promise<UploadResumeResponse> {
  await new Promise((r) => setTimeout(r, 200));
  const fmt = (file.name.split(".").pop() || "md").toLowerCase() as ResumeFormat;
  _mockState = {
    ..._mockState,
    has_resume: true,
    profile: {
      user_id: _mockState.user_id,
      created_at: _mockState.profile?.created_at ?? new Date().toISOString(),
      candidate_names: _mockState.profile?.candidate_names ?? ["Alina"],
      master_format: fmt,
      master_uploaded_at: new Date().toISOString(),
      master_parse_confidence:
        fmt === "tex" ? 1.0 : fmt === "md" ? 0.95 : fmt === "docx" ? 0.85 : 0.6,
    },
  };
  return {
    ok: true,
    format: fmt,
    confidence: _mockState.profile!.master_parse_confidence!,
    warnings: [],
    section_count: 4,
  };
}

async function mockUploadExperiences(files: File[]): Promise<UploadExperiencesResponse> {
  await new Promise((r) => setTimeout(r, 200));
  const newExps = files.map((f) => ({
    id: Math.random().toString(16).slice(2, 18),
    file_name: f.name,
    scoring_status: "queued" as ScoringStatus,
  }));
  _mockState = {
    ..._mockState,
    experience_count: _mockState.experience_count + newExps.length,
    experiences: [..._mockState.experiences, ...newExps],
  };
  // Mock: simulate scoring completion after a short delay
  setTimeout(() => {
    _mockState = {
      ..._mockState,
      experiences_scored_count: _mockState.experience_count,
      experiences: _mockState.experiences.map((e) => ({
        ...e,
        scoring_status: "done" as ScoringStatus,
      })),
    };
  }, 1500);
  return { ok: true, experiences: newExps };
}

async function mockDeleteExperience(): Promise<{ ok: boolean; experience_count: number }> {
  await new Promise((r) => setTimeout(r, 80));
  return { ok: true, experience_count: _mockState.experience_count };
}

async function mockPatchUserProfile(body: PatchUserProfileBody): Promise<UserStatus> {
  await new Promise((r) => setTimeout(r, 80));
  _mockState = {
    ..._mockState,
    profile: {
      ..._mockState.profile!,
      ...(body.candidate_names !== undefined ? { candidate_names: body.candidate_names } : {}),
      ...(body.target_market_default !== undefined
        ? { target_market_default: body.target_market_default }
        : {}),
    },
  };
  return _mockState;
}

// In-memory mock state for multi-lens master flow.
let _mockLensTargets: LensTargets = { primary: "C_product_ops", secondary: [] };
let _mockMasters: MastersResponse = {
  C_product_ops: {
    has_master: true,
    generated_at: new Date(Date.now() - 86_400_000).toISOString(),
    method: "user_uploaded",
    status: "ready",
  },
};

async function mockSetLensTargets(
  body: LensTargets,
): Promise<{ ok: boolean; primary: Lens; secondary: Lens[] }> {
  await new Promise((r) => setTimeout(r, 80));
  _mockLensTargets = { primary: body.primary, secondary: body.secondary };
  // Ensure mock map has entries for all chosen lenses (absent if not generated).
  const next: MastersResponse = {};
  const all: Lens[] = [body.primary, ...body.secondary];
  for (const l of all) {
    next[l] = _mockMasters[l] ?? {
      has_master: false,
      generated_at: null,
      method: null,
      status: "absent",
    };
  }
  _mockMasters = next;
  return { ok: true, primary: body.primary, secondary: body.secondary };
}

async function mockGetMasters(): Promise<MastersResponse> {
  await new Promise((r) => setTimeout(r, 60));
  return { ..._mockMasters };
}

async function mockGenerateMaster(
  lens: Lens,
): Promise<{ ok: boolean; lens: Lens; status: string }> {
  await new Promise((r) => setTimeout(r, 80));
  _mockMasters[lens] = {
    has_master: false,
    generated_at: null,
    method: "rewrite_from_upload_and_bank",
    status: "generating",
  };
  // Simulate completion after a few seconds.
  setTimeout(() => {
    _mockMasters[lens] = {
      has_master: true,
      generated_at: new Date().toISOString(),
      method: "rewrite_from_upload_and_bank",
      status: "ready",
    };
  }, 4000);
  return { ok: true, lens, status: "scheduled" };
}

async function mockDeleteMaster(lens: Lens): Promise<{ ok: boolean }> {
  await new Promise((r) => setTimeout(r, 60));
  delete _mockMasters[lens];
  if (_mockLensTargets.primary === lens) {
    // Don't auto-promote — backend rejects this in real life
  }
  _mockLensTargets = {
    ..._mockLensTargets,
    secondary: _mockLensTargets.secondary.filter((l) => l !== lens),
  };
  return { ok: true };
}
