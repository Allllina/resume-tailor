---
name: fit-diagnosis-engine
description: |
  Produce honest, user-facing fit diagnosis at two PPAF stages — pre-rewrite
  (matching matrix + integrated assessment + optimization boundary) and
  post-rewrite (HM/HRBP dual-perspective review + radar chart + targeted
  recommendations). Replaces the missing user-facing surface for SKILL.md
  Step 4 and Step 8.
---

# Fit Diagnosis Engine

Two-mode sub-skill that runs the same rubric-driven fit assessment at two
different points in the PPAF cycle:

- **`pre_rewrite`** (PLANNING stage): before the user starts rewriting,
  give a candid forecast — what the JD demands, what the candidate brings,
  where the gaps are, what optimization can / cannot solve.
- **`post_rewrite`** (late-FEEDBACK stage): after the rewrite is produced,
  simulate Hiring-Manager and HRBP readers and report what each sees /
  worries about / would recommend.

The sub-skill is invoked twice per run in Mode F (full); Mode L (lightweight)
typically only invokes the `pre_rewrite` mode and skips the `post_rewrite`
review pass.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| `mode` | `"pre_rewrite" \| "post_rewrite"` | yes | Selects branch |
| `jd_analysis` | object | yes | Output of jd-analyzer (5-layer JD breakdown) |
| `competency_profile` | object | yes | Output of role-competency-extractor (9-section) |
| `candidate_assets` | object | yes | profile + experience-bank index + resume base |
| `current_resume` | string \| null | only `post_rewrite` | LaTeX or markdown of rewritten resume |
| `target_market` | enum | yes | `north-america` / `mainland-china` / `hong-kong` |
| `multi_jd` | boolean | optional | Triggers Section 4-4 / 8-4 multi-JD coverage matrix |

## 10-step workflow

### Step 1: Validate inputs

Check `mode` is one of the two allowed values. Confirm `current_resume` is
provided iff `mode == "post_rewrite"`. Confirm `competency_profile` has all
9 sections (A through I + flat-field summary).

### Step 2: Load reference rubrics

Always load:
- `assets/knowledge-base/references/general-rules.md` — bullet-writing
  standards, six-element rubric.
- `assets/knowledge-base/references/market-contexts/<target_market>.md` —
  market-specific evaluation norms.

Conditionally load:
- The role-lens file referenced by `competency_profile.flat.primary_lens`
  (and `secondary_lens` if blended).
- The scenario file referenced by `competency_profile.flat.scenario_loaded`.

These references provide the rubric structure for matching-matrix evaluation
and the cultural / market norms for HM/HRBP simulation.

### Step 3: Branch on mode

If `mode == "pre_rewrite"` → continue to Steps 4-A through 4-D below.

If `mode == "post_rewrite"` → skip to Steps 8-A through 8-D below.

### Step 4-A: Build matching matrix (pre_rewrite)

For every JD requirement listed in `jd_analysis` (hard requirements,
preferred requirements, hidden criteria from `competency_profile.section_F`):

| JD requirement | Candidate evidence | Verdict |
|---|---|---|
| (literal JD line or competency item) | (specific experience or asset that proves it) | ✅ strong / ⚠️ partial / ❌ missing |

Verdict criteria:
- ✅ **strong** — direct, recent (≤3 years), at comparable scope. Cite the
  experience-bank entry that supports it.
- ⚠️ **partial** — adjacent or older or smaller scope. Bridgeable in
  Step 5 (gap-bridging-planner). Note the bridging hypothesis briefly.
- ❌ **missing** — no evidence in candidate assets. Note whether
  short-term (1-2 weeks of self-study) or long-term (3+ months of
  experience) closure is possible.

Matrix must be exhaustive over JD requirements; do NOT cherry-pick.

### Step 4-B: Integrated assessment (pre_rewrite)

3-5 sentences. Must cover:
- Overall fit verdict (one of: strong fit, mixed fit, stretch).
- Single biggest strength.
- Single biggest gap.
- Estimated competitiveness in the candidate pool (relative position, not
  guaranteed outcome).

Honest tone. No marketing language. If the candidate is a stretch, say so.

### Step 4-C: Optimization boundary (pre_rewrite)

Two columns:

**What rewriting can solve** — keyword surfacing, framing, structural
emphasis, market localization, narrative thread.

**What rewriting cannot solve** — missing core experiences, mismatched
seniority, missing technical certifications, hard credential gaps. These
require either supplementing (Step 5b: Add) or accepting as known gap.

Be explicit about which gaps are in which bucket; prevents overpromising.

### Step 4-D: Multi-JD coverage matrix (only if `multi_jd == true`)

For each JD in the multi-JD set, show coverage breakdown:

| JD | Strong matches | Partial | Missing | Net coverage |
|---|---|---|---|---|
| (jd_id) | (count) | (count) | (count) | (percentage) |

If coverage spread is high (e.g., 30% gap between top and bottom JD), flag
this as a structural concern that may require multiple resume versions.

### Step 8-A: Hiring Manager simulation (post_rewrite)

Simulate the direct hiring manager (the business leader who would be the
candidate's boss) reading the rewritten resume. Output three subsections:

- **亮点 / Highlights** — 1-2 bullets the HM would react to positively
  ("if I see this, I want to interview deeper").
- **顾虑 / Concerns** — 1-2 areas the HM would probe in the interview
  because the resume doesn't fully address them.
- **对比风险 / Comparative risk** — if the candidate pool likely contains
  candidates with directly relevant experience (e.g., ex-competitor BU
  alums), where does this resume lose? One sentence.

### Step 8-B: HRBP simulation (post_rewrite)

Simulate the HR business partner / talent screener applying first-pass
filters. Output three subsections:

- **关键词命中率 / Keyword hit rate** — count of `competency_profile`
  Tier 1 keywords surfaced in the resume, expressed as a fraction.
- **硬性条件匹配 / Hard requirement match** — pass/fail on each hard
  requirement (degree, language, location, time-window, etc.).
- **推进决策 / Advance decision** — one of: direct-pass to business,
  pass-with-flags, hold for cohort review, reject. Justify in one
  sentence.

### Step 8-C: Six-axis radar chart data (post_rewrite)

Produce numeric scores (0-100) on the six axes derived from the JD:

1. **Industry experience** — relevance of industry exposure.
2. **Core skills** — depth of the core technical / methodological skills.
3. **Data ability** — data fluency where the role demands it.
4. **Communication / collaboration** — evidence of stakeholder management.
5. **Cultural fit** — language, market norms, ownership signals.
6. **JD-specific extras** — any additional axis the JD emphasizes
  (substitute the most JD-relevant dimension here).

Each score must be justified by a one-line citation to either the resume or
the experience-bank. The renderer downstream uses these scores to draw the
radar.

### Step 8-D: Targeted recommendations (post_rewrite)

Bullet list of actionable changes, grouped by investment level:

- **Wording-level** (1 hour) — specific phrase replacements, keyword
  surfacing, action-verb upgrades.
- **Structure-level** (half day) — bullet reordering, section
  re-emphasis, summary rewrites.
- **Project / experience-level** (multi-week) — supplemental work the
  candidate should consider before re-applying or in interview prep.

Each recommendation cites the specific bullet or section it addresses.

### Step 9: Format-specific localization

Apply `target_market` rules:
- `mainland-china`: bullet-tag conventions, deliverable-noun closers,
  no decimal places past one in percentages.
- `hong-kong`: bilingual considerations, conservative claims.
- `north-america`: STAR-explicit, action-verb starters, achievement
  metric prominence.

This stage runs over both modes' outputs to ensure presentation matches the
target market's expectations.

### Step 10: Emit structured output

Return the structured payload per `output-schema.md`:
- `mode == "pre_rewrite"` → Section 4 schema (matrix + assessment +
  boundary + multi-JD coverage when applicable).
- `mode == "post_rewrite"` → Section 8 schema (HM + HRBP + radar +
  targeted recommendations).

Include `confidence` rating (high / moderate / low) based on:
- Number of JDs analyzed (1 → moderate at best; 4+ → high).
- Coverage of `competency_profile` sections used.
- Whether market-context file was loaded vs default-fallback.

## Hard rules

1. **No fabrication.** Every matrix verdict must cite a real experience or
   resume content. If no evidence exists, it's ❌, not ⚠️.
2. **No score inflation.** Radar axis scores must be defensible. A 90+
   requires multiple pieces of converging evidence; a 70 with one piece
   is honest.
3. **No optimism washing.** If the candidate is a stretch, say so in
   Step 4-B integrated assessment. Do not soften the language.
4. **Mode immutability.** Once a mode is invoked and the workflow has
   started, the mode does not switch mid-flow. Caller must invoke the
   sub-skill twice for two modes.
5. **Truthfulness inheritance.** Inherits R-1 through R-6 from root
   SKILL.md (no fabrication of experiences, skills, numbers, identity
   fields, role descriptions; new content must be source-traceable).

## When NOT to invoke

- The competency profile is missing or stale → invoke
  `role-competency-extractor` first.
- The resume is not yet rewritten and `mode == "post_rewrite"` is requested
  → caller error; return validation failure.
- Single-JD self-screening where the user already knows their fit → caller
  may skip this sub-skill in Mode L if they explicitly opt out (audit-log
  the skip).

## Consumed by

- Mode L orchestrator → calls only `pre_rewrite`, surfaces Section 4 to
  user before rewrite begins.
- Mode F orchestrator → calls both modes, persists Section 4 to early
  feedback channel and Section 8 to late feedback / review queue.
- Inbox UI (in-repo, same project): renders matrix as colored table,
  radar as SVG chart, recommendations as actionable cards.
- Subsequent sub-skills consume:
  - `gap-bridging-planner` consumes Section 4 matrix (specifically the
    ⚠️ partial rows) as its primary input.
  - `resume-rewrite-engine` consumes Section 4 matrix + boundary as
    contextual input for prioritizing which experiences to surface.
