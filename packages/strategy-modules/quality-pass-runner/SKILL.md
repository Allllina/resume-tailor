---
name: quality-pass-runner
description: |
  Run 4-pass quality pipeline on a rewritten resume in strict order:
  Pass 1 (keyword injection) → Pass 1.5 (Chinese readability, conditional)
  → Pass 2 (AI taste removal) → Pass 3 (truthfulness verification).
  Each pass checks content introduced by the previous pass. Pass 3 is the
  source-grounding gate.
---

# Quality Pass Runner

Sub-skill that wraps SKILL.md Step 6.5 four-pass pipeline as a single
callable unit. The pipeline runs strictly in order; downstream passes
catch issues introduced by upstream passes.

This sub-skill is **invoked once after rewrite, not interleaved**. The
caller passes in the full rewritten resume; the runner produces the
final-quality version + structured findings.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| `rewritten_resume` | string | yes | Full resume text after `resume-rewrite-engine` produces it; LaTeX or markdown form |
| `competency_profile` | object | yes | 9-section output from `role-competency-extractor`; used for Pass 1 keyword reference |
| `experience_bank` | object | yes | Source-of-truth experience entries; used for Pass 3 grounding |
| `target_market` | enum | yes | `north-america` / `mainland-china` / `hong-kong`; controls Pass 1.5 trigger |
| `jd_text` | string | yes | Original JD body; used for Pass 2 protection rule (don't replace JD-native terms) |

## 10-step workflow

### Step 1: Validate inputs

Confirm `rewritten_resume` is non-empty and has not already been
quality-passed (idempotency check: orchestrator should not double-pass).
Confirm `experience_bank` is loaded (Pass 3 hard requires source files).
Confirm `competency_profile.section_D` (5-tier ATS keywords) is populated
(Pass 1 hard requires keyword reference).

### Step 2: Load reference files

Always load:
- `assets/knowledge-base/references/workflow/quality-pass.md` — pass methodology + AI-taste replacement table.
- `assets/knowledge-base/references/general-rules.md` — bullet-writing standards (used in Pass 1.5).
- `assets/knowledge-base/references/market-contexts/<target_market>.md` — market-specific phrasing norms.

Conditionally load:
- `assets/knowledge-base/references/role-lenses/<lens>.md` if Pass 1 needs additional keyword context.

### Step 3: Pass 1 — Keyword Injection

Goal: ensure all Tier 1 (and selected Tier 2) ATS keywords from
`competency_profile.section_D` appear in the resume with sufficient
frequency.

Process:
1. Extract Tier 1 + selected Tier 2 keywords from competency profile.
2. Use word-boundary precise matching (`\b<keyword>\b` for English /
   exact substring for CJK) to count current hits per keyword.
3. For each keyword with zero hits where the candidate genuinely has
   the underlying capability, identify the most relevant bullet or
   skill-bar slot to inject.
4. Inject by augmenting existing text — do NOT add fabricated content.
   If no natural injection point exists, mark keyword as
   `unable_to_inject` and surface to user.
5. Re-count hits after injection.

Output: list of injected keywords + before/after hit rate + list of
unable-to-inject (with reasons).

### Step 4: Pass 1.5 — Chinese Readability (conditional)

Trigger: only fires when `target_market == "mainland-china"` or
`hong-kong`. Skip otherwise.

Goal: ensure each bullet is intelligible to a Chinese-reading business
interviewer without translation gymnastics.

Process:
1. Scan for English direct-translation phrases (e.g., "技术采用曲线评估").
2. Scan for non-universal English abbreviations (e.g., random ML
   acronyms not standard in Chinese resume context).
3. Replace with idiomatic Chinese equivalents per `quality-pass.md`
   reference table.
4. Preserve technical English terms that ARE standard (e.g., "BERT",
   "LangGraph", "Excel", "PPT").

Output: list of flagged phrases + replacements made.

### Step 5: Pass 2 — AI Taste Removal

Goal: remove LLM-typical over-modifiers and weasel language.

Process:
1. Run `quality-pass.md` replacement table against the resume:
   - "Spearheaded" → "Led" / "主导"
   - "Leveraged" → "Used" / "用"
   - "赋能" → "支持"
   - "打通" → context-specific replacement
   - "全方位" / "深度赋能" / "助力" → flagged
   - Weasel adverbs ("显著" / "大幅" / "极大") → flagged
2. **Protection rule**: if a flagged term appears in `jd_text`, skip
   replacement and log as `protected_skipped`. Rationale: JD-native
   terms are not AI taste; they are job-specific vocabulary.
3. Track every replacement with location and original/replacement pair.

Output: list of replacements applied + list of protected skipped.

### Step 6: Pass 3 — Truthfulness Verification

Goal: every factual claim in the rewritten resume must trace back to
`experience_bank` source files.

Process:
1. Extract every factual claim (numbers, scopes, deliverables, role
   descriptions, dates, company affiliations).
2. For each claim, search `experience_bank` for source evidence.
3. Classify each claim:
   - **`verified`** — direct or paraphrased match in source.
   - **`unsourced`** — no source match found; severity is `high` if it
     is a quantified claim (number, percentage, scope) and `medium`
     if qualitative.
   - **`identity_locked`** — company / position / school / degree /
     dates fields; must match source exactly. Mismatch = `fail`.
4. Hard rules R-1 through R-6 enforced here: no fabricated experiences,
   no fabricated skills, no fabricated quantification, no identity-field
   modification, no role upgrades, all new content source-traceable.

Output: list of verified claims + list of unsourced claims (with
severity) + identity-lock check verdict.

This pass is canonical; in current harness implementation (Wave 4 D.4),
it runs as a LangGraph multi-agent verifier per ADR 0005.

### Step 7: Aggregate findings

Combine pass-level verdicts into aggregate verdict:

- All 4 passes `pass` → aggregate `pass`.
- Any pass `fail` → aggregate `fail`; resume cannot be released to user.
- Pass 3 has `unsourced` claims with severity `high` → aggregate
  `partial_pending_user`; resume goes to manual review queue (D.5 in
  harness) where user approves or rejects each unsourced claim.
- Other partial cases → aggregate `partial_pending_user`.

### Step 8: Pending-user review flag

Set `pending_user_review_flag = true` when aggregate is `partial_pending_user`.
This flag drives downstream UI behavior:
- Inbox UI surfaces unsourced claims as a checklist for user approval.
- Orchestrator does NOT auto-release the resume; user action required.

In Mode L (lightweight, single user), the user is themselves; the flag
short-circuits to a chat-based prompt asking the user to confirm or
amend each unsourced claim.

### Step 9: Format-specific localization carryover

Localization is already built into Pass 1.5 (Chinese-specific) and
Pass 2 (replacement table is market-aware). This step verifies no
localization regression was introduced; emit warning if found.

### Step 10: Emit structured output

Return per `output-schema.md`:
- 4 pass-level result sections (Pass 1, Pass 1.5, Pass 2, Pass 3).
- Aggregate verdict.
- Pending-user review flag.
- Confidence rating.

The final cleansed resume text is also returned as `final_resume_text`.

## Hard rules

1. **Pass order is immutable.** Pass 1 → 1.5 → 2 → 3. The runner does
   not interleave or reorder. Caller cannot request "skip Pass 2"; if
   skip is needed, caller must invoke this sub-skill with appropriate
   `pass_skip_flags` input (currently not exposed; reserved for future
   versions).
2. **Pass 3 cannot be skipped.** Truthfulness is the canonical hard
   rule (R-1 to R-6). Even Mode L runs Pass 3. The only mode in which
   Pass 3 can be deferred is `partial_pending_user` — and that defers
   user resolution, not the pass itself.
3. **Each pass checks the previous.** Pass 1 may inject text; Pass 1.5
   checks the injected text for Chinese readability; Pass 2 checks the
   1.5-modified text for AI taste; Pass 3 checks the 2-modified text
   for truthfulness. No pass operates on stale upstream content.
4. **No fabrication via injection.** Pass 1 cannot invent experience
   to inject keywords. If no natural injection point exists, the
   keyword is marked `unable_to_inject`; this is honest behavior, not
   failure.
5. **JD-native terms are protected.** Pass 2 must check `jd_text`
   before replacing any term that appears there. Replacing a JD-native
   term with an "alternative" actively hurts ATS keyword matching.
6. **Identity fields are locked.** Pass 3 hard-fails if company name,
   position, school, degree, or date fields differ from source.

## When NOT to invoke

- The resume has not yet been rewritten (`resume-rewrite-engine` has
  not run) → caller error.
- The resume has already had this sub-skill applied → idempotency
  violation; orchestrator should detect and skip.
- Source files (`experience_bank`) are stale relative to the rewritten
  resume → re-load and re-run.
- Mode L orchestrator running with explicit user opt-out for Pass 3
  → currently not supported; future versions may add an opt-out flag
  but Pass 3 default is mandatory.

## Consumed by

- Orchestrator (`SKILL.md` root): runs this sub-skill after
  `resume-rewrite-engine` and before `latex-renderer` (Mode L) or before
  `fit-diagnosis-engine` `post_rewrite` (Mode F).
- `fit-diagnosis-engine` `post_rewrite` mode: consumes
  `final_resume_text` as its input.
- `latex-renderer` (inline / harness utility): renders
  `final_resume_text` to LaTeX.
- Inbox UI (in-repo, same project): renders pass-level findings as
  individual quality cards; surfaces `pending_user_review_flag` as an
  approval checklist.
- Harness `repl/stages/late_feedback.py` (Wave 4+): wires Pass 3
  (D.4 LangGraph). Pass 1, 1.5, 2 implementation pending.
