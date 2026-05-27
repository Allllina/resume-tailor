---
name: gap-bridging-planner
description: |
  Convert pre-rewrite fit-diagnosis matrix gaps into actionable bridging
  plans. Three branches: 5a Reframe (bridge each experience to JD language
  before rewrite), 5b Add (supplemental work suggestions in 1-2 weeks /
  1-3 months horizons), 5c Skill Gap (3-tier skill bar adjustment). Also
  absorbs Step 7-1 (structural ordering) and Step 7-2 (skills bar) from the
  original SKILL.md because their content overlaps.
---

# Gap Bridging Planner

Sub-skill that consumes the pre-rewrite fit diagnosis (Section 4-A matrix
+ Section 4-C optimization boundary) and produces a bridging plan that
the orchestrator hands to `resume-rewrite-engine` as input.

This sub-skill is **forward-looking**: it operates between Step 4
(diagnosis) and Step 6 (rewrite) in the PPAF cycle, telling the rewrite
engine which experiences to bridge, which gaps to flag for supplement,
and which skill-bar items to adjust.

It does NOT rewrite bullets directly — that is `resume-rewrite-engine`'s
job. This sub-skill outputs a plan, not text.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| `fit_diagnosis_pre_rewrite` | object | yes | Section 4-A matrix + 4-C boundary from `fit-diagnosis-engine` mode `pre_rewrite` |
| `competency_profile` | object | yes | 9-section output from `role-competency-extractor` |
| `candidate_assets` | object | yes | profile + experience-bank index |
| `target_market` | enum | yes | `north-america` / `mainland-china` / `hong-kong` |
| `application_timeline` | enum | optional | `immediate` (≤ 1 week to apply) / `near` (1-4 weeks) / `mid` (1-3 months); defaults to `immediate` |

## 10-step workflow

### Step 1: Validate inputs

Confirm `fit_diagnosis_pre_rewrite` contains both `matching_matrix` and
`optimization_boundary`. Confirm at least one ⚠️ partial or ❌ missing
verdict exists in the matrix (otherwise this sub-skill has nothing to
plan; orchestrator should skip).

### Step 2: Load reference rubrics

Load:
- `assets/knowledge-base/references/workflow/gap-bridging.md` — 桥接 strategy
  reference.
- `assets/knowledge-base/references/role-lenses/<lens>.md` — referenced by
  `competency_profile.flat.primary_lens`.
- `assets/knowledge-base/references/general-rules.md` — for skill bar
  conventions.

### Step 3: Triage matrix verdicts

Classify every Section 4-A row:

- **`strong` rows** → no action; skip in this planner.
- **`partial` rows** → candidates for 5a Reframe (the experience exists
  but needs JD-language framing).
- **`missing` rows** → candidates for 5b Add (the experience does not
  exist; needs supplement) or 5c Skill Gap (if the missing item is a
  declarative skill rather than experiential).

Also pull from Section 4-C `rewriting_cannot_solve`: any items there
that are `supplement` closure path become 5b candidates.

### Step 4: 5a Reframe planning

For each `partial` matrix row:

1. Identify which experience-bank entry the candidate evidence cites.
2. Diagnose what JD language is currently NOT in that entry's bullets.
3. Write a one-sentence reframe directive: which keyword to inject /
   which angle to surface, citing source-grounded evidence to justify.

The output is a plan that `resume-rewrite-engine` consumes — the actual
bullet rewriting happens there. This planner does NOT produce bullet
text; it produces directives like:
"Reframe Kearney 1.1 to surface 'industry research' keyword by adding
'下游应用行业研究' phrasing in the title; evidence: experience-bank
01-kearney.md project 1 explicitly covers 下游应用研究."

### Step 5: 5b Add planning

For each gap that is `missing` or marked `supplement` in Section 4-C:

1. Classify supplement horizon:
   - **`short_term` (≤ 1 week)** — self-study, certification, side project,
     case writeup. Achievable before applying.
   - **`mid_term` (1-3 months)** — short internship, formal coursework,
     volunteer engagement. Affects timeline.
   - **`not_closeable`** — accept as known gap; see 5c or face in
     interview.

2. Cross-reference `application_timeline` input:
   - If `application_timeline == "immediate"` and supplement is
     `mid_term`, mark as **defer** (not actionable for current cycle).
   - If `application_timeline == "mid"` and supplement is `mid_term`,
     mark as **plan-now** (achievable within the apply window).

3. For each suggested supplement, output a one-sentence action item:
   what to do, expected time investment, where it surfaces on resume.

### Step 6: 5c Skill Gap + structural triage

For declarative skill items (programming languages, tools, certifications,
methodologies named in the JD):

Apply 3-tier classification:

- **Tier A (会但没写)** — candidate has the skill, just absent from the
  current resume's skill bar. Action: add to skill bar; bullet-level
  embed if a relevant experience demonstrates it.
- **Tier B (会一点)** — candidate has shallow exposure. Action: add to
  skill bar with care, do not over-emphasize; do not embed at bullet
  level unless the JD specifically requires.
- **Tier C (完全不会)** — candidate does not have the skill. Action: do
  NOT add to skill bar. If the JD lists it as preferred, accept the gap
  and note in 5b for future supplement.

Also handle structural items absorbed from Step 7-1:

- Experience section ordering (which experience leads, which goes last)
- Section length allocation (which experience gets more bullets)
- Missing sections (e.g., self-introduction, language proficiency, etc.)

### Step 7: Cross-coverage check (multi-JD mode)

If `competency_profile.flat.scoring_notes` indicates multi-JD scope,
verify the bridging plan does not over-fit a single JD at the expense of
others. If it does, flag the conflict and propose a master-version vs
JD-specific-version branching strategy.

### Step 8: Confidence and limitations

Rate plan confidence:
- `high` — every partial row has a concrete reframe directive grounded
  in source experience; every missing row has a clear supplement plan or
  accept-as-gap rationale.
- `moderate` — most rows handled; a few rows have ambiguous bridging
  hypotheses that the rewrite engine will need to resolve.
- `low` — multiple rows have weak bridging hypotheses; recommend
  re-running Step 4 (fit-diagnosis-engine) with better inputs first.

### Step 9: Format-specific localization

Apply `target_market` rules to the plan output:
- `mainland-china` — favor "全栈 / 端到端 / deliverable-noun-suffixed"
  phrasing in reframe directives.
- `hong-kong` — bilingual sensitivity; conservative claims.
- `north-america` — STAR-explicit reframe directives, action-verb
  starters.

### Step 10: Emit structured output

Return the structured payload per `output-schema.md`. Include:
- 5a Reframe directives array
- 5b Add suggestions array (with action-or-defer flag)
- 5c Skill Gap classifications + structural recommendations
- Confidence rating
- Multi-JD conflict flag (if applicable)

## Hard rules

1. **No directive without source.** Every 5a reframe directive must cite
   the specific experience-bank entry that justifies the keyword
   injection. Inherits R-1 (no fabrication) from root SKILL.md.
2. **No skill inflation.** 5c Tier A/B/C classification must be honest;
   placing a Tier C skill in the bar violates R-2.
3. **No silent over-claim.** If the bridging hypothesis stretches beyond
   what experience-bank supports, mark the directive `confidence: low`
   and surface to user.
4. **Plan, not prose.** This sub-skill outputs directives + classifications,
   not rewritten bullet text. Bullet rewriting is `resume-rewrite-engine`'s
   exclusive responsibility.
5. **Timeline awareness.** Honor `application_timeline` input; do not
   propose mid-term supplements when timeline is immediate (mark them
   `defer` instead).

## When NOT to invoke

- Section 4-A matrix has zero `partial` or `missing` rows → orchestrator
  should skip; nothing to bridge.
- The candidate is rejecting `pre_rewrite` diagnosis output (e.g.,
  disagrees with verdicts) → re-run `fit-diagnosis-engine` with adjusted
  inputs before invoking this planner.
- Mode L orchestrator may invoke this sub-skill in lightweight form (skip
  Step 7 cross-coverage check); the full Step 7 only fires in Mode F.

## Consumed by

- `resume-rewrite-engine`: consumes 5a directives as primary input for
  bullet rewriting; consumes 5c skill-bar plan to update the technical /
  AI / language skill rows.
- Orchestrator (`SKILL.md` root): surfaces 5b Add suggestions to user as
  out-of-band action items (not part of resume itself, but coaching
  surface).
- Inbox UI (in-repo, same project): renders 5a directives as a
  before/after preview, 5b suggestions as a checklist, 5c skill-bar plan
  as add/remove diffs.
