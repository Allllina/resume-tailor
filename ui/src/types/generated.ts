// AUTO-GENERATED — do not edit by hand.
// Source: contracts/schemas/*.json
// Regenerate: `make gen-types` (or `python3 scripts/gen_ts_types.py`)
// Drift check: `python3 scripts/gen_ts_types.py --check` returns non-zero on diff.
// Adoption: hand-maintained types in ui/src/lib/api.ts coexist; new schema
// fields land here first. Migration of api.ts to generated.ts is incremental.

// ──── from harness-tailor-output.schema.json ────

/**
 * Wave 5 P2 — quality-pass-runner output for Step 6.5 Pass 1.5 Chinese readability and Pass 2 R-11 AI-tone cleanup, run before Pass 3. See packages/strategy-modules/quality-pass-runner/output-schema.md.
 */
export interface QualityPassReport {
  schema_version: "1.0.0";
  sub_skill: "quality-pass-runner";
  target_market: "north-america" | "mainland-china" | "hong-kong";
  ppaf_stage: "late_feedback";
  invoked_at: string;
  inputs_signature: {
  rewritten_resume_hash: string;
  competency_profile_id: string;
  experience_bank_version: string;
};
  final_resume_text: string;
  aggregate_verdict: "pass" | "partial_pending_user" | "fail";
  pending_user_review_flag: boolean;
  confidence: "high" | "moderate" | "low";
  _method: "llm" | "llm_partial" | "fallback_no_llm";
  pass_1_keyword_injection: {
  injected_keywords: Array<{
  keyword: string;
  target_location: string;
  injection_method: "title_keyword" | "inline_phrase" | "skill_bar" | "summary_addition";
}>;
  hit_rate_before: string;
  hit_rate_after: string;
  unable_to_inject: Array<{
  keyword: string;
  reason: string;
}>;
  verdict: "pass" | "partial" | "fail";
};
  pass_1_5_chinese_readability: {
  enabled: boolean;
  flagged_phrases: Array<{
  original: string;
  replacement: string;
  reason: "english_direct_translation" | "non_universal_abbreviation";
}>;
  preserved_english_terms: Array<{
  term: string;
  reason: string;
}>;
  verdict: "pass" | "partial" | "fail";
  _method: "llm" | "llm_partial" | "fallback_no_llm";
};
  pass_2_ai_taste_removal: {
  replacements_applied: Array<{
  original: string;
  replacement: string;
  location: string;
}>;
  protected_skipped: Array<{
  term: string;
  reason: "in_jd" | "candidate_idiom_authentic";
}>;
  verdict: "pass" | "partial" | "fail";
  _method: "llm" | "llm_partial" | "fallback_no_llm";
};
  pass_3_truthfulness: {
  verified_claims_count: number;
  unsourced_claims: Array<{
  claim: string;
  location: string;
  severity: "high" | "medium";
  type: "quantification" | "scope" | "role_description" | "other";
}>;
  identity_lock_check: "pass" | "fail";
  identity_lock_violations: Array<{
  field: string;
  resume_value: string;
  source_value: string;
}>;
  verdict: "pass" | "partial_pending_user" | "fail";
};
}

/**
 * Wave 5 F1 — fit-diagnosis-engine sub-skill output, pre_rewrite mode (PLANNING-stage Section 4: matching matrix with bridging/closure + integrated assessment + optimization boundary with closure path + optional multi-JD coverage). Populated by harness.fit_diagnosis. See packages/strategy-modules/fit-diagnosis-engine/output-schema.md for the canonical spec.
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
  confidence: "high" | "moderate" | "low";
  competitiveness_rating: "high" | "above_mid" | "mid" | "below_mid" | "low";
  _method: "llm" | "llm_partial" | "fallback_no_llm";
  matching_matrix: Array<{
  text: string;
  evidence: string;
  verdict: "strong_match" | "transferable" | "missing";
  source: "section_b_priority" | "section_c_tier_1" | "section_c_tier_2" | "section_c_tier_3";
  bridging_or_closure: string;
}>;
  integrated_assessment: string;
  optimization_boundary: {
  rewriting_can_solve: Array<string>;
  rewriting_cannot_solve: Array<string>;
};
  multi_jd_coverage?: Array<unknown> | null;
  spread_flag?: boolean | null;
}

/**
 * Wave 5 F3 — fit-diagnosis-engine sub-skill output, post_rewrite mode (late-FEEDBACK Section 8: HM + HRBP simulation + 6-axis radar with citations + improvement suggestions). Populated by harness.fit_diagnosis after rewrite. See packages/strategy-modules/fit-diagnosis-engine/output-schema.md.
 */
export interface FitDiagnosisPostRewrite {
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
  confidence: "high" | "moderate" | "low";
  competitiveness_rating: "high" | "above_mid" | "mid" | "below_mid" | "low";
  _method: "llm" | "llm_partial" | "fallback_no_llm";
  hm: {
  highlights: Array<string>;
  concerns: Array<string>;
  comparison_risk: string;
};
  hrbp: {
  keyword_hit_rate: number;
  hard_filter_match: Record<string, "match" | "mismatch" | "uncertain">;
  advance_decision: "push_direct" | "push_with_note" | "screen_out";
  decision_rationale: string;
};
  radar: {
  dimensions: Array<{
  name: string;
  resume_score: number;
  jd_required: number;
  citation: string;
}>;
};
  improvement_suggestions: Array<{
  text: string;
  effort: "wording" | "supplement_project" | "long_term";
}>;
}

/**
 * Wave 5 F6 — gap-bridging-planner output (Step 5a reframe, 5b add, 5c skill-gap and structural plan) produced after fit_diagnosis_pre_rewrite and before rewrite.
 */
export interface GapBridging {
  sub_skill: "gap-bridging-planner";
  target_market: "north-america" | "mainland-china" | "hong-kong";
  ppaf_stage: "planning";
  invoked_at: string;
  inputs_signature: {
  fit_diagnosis_id: string;
  competency_profile_id: string;
};
  application_timeline: "immediate" | "near" | "mid";
  confidence: "high" | "moderate" | "low";
  multi_jd_conflict_flag: boolean;
  _method: "llm" | "llm_partial" | "fallback_no_llm";
  reframe_directives: Array<{
  matrix_row_id: string;
  target_experience: string;
  target_bullet_id: string;
  keyword_to_inject: string;
  framing_directive: string;
  source_evidence: string;
}>;
  add_suggestions: Array<{
  gap_label: string;
  horizon: "short_term" | "mid_term" | "not_closeable";
  action: "plan_now" | "defer" | "accept";
  suggestion: string;
}>;
  skill_bar_adjustments: {
  add_to_bar: Array<{
  skill: string;
  tier: "A" | "B";
  placement_row: "technical" | "ai" | "language" | "other";
  rationale: string;
}>;
  remove_from_bar: Array<{
  skill: string;
  reason: string;
}>;
  do_not_add: Array<{
  skill: string;
  reason: string;
}>;
};
  section_ordering: {
  experience_section_order: Array<string>;
  experience_section_emphasis: Array<{
  exp_id: string;
  bullet_count_recommendation: number;
  rationale: string;
}>;
  missing_sections: Array<{
  section_name: string;
  action: "add" | "acknowledge_absence";
  rationale: string;
}>;
};
  multi_jd_conflict: {
  conflicting_directives: Array<{
  jd_a: string;
  jd_b: string;
  conflict_summary: string;
}>;
  proposed_resolution: "master_with_jd_specific" | "branch_versions" | "accept_compromise";
  rationale: string;
};
}

