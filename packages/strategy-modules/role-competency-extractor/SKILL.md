---
name: role-competency-extractor
description: |
  Convert a JD (or set of JDs for the same role) into a structured competency model
  consumed by JobOps scoring and the resume-rewrite-engine. Produces 9-section output
  per `output-schema.md`. Called by the root `SKILL.md` Step 3.5 and by JobOps
  pipeline before the scoring layer. Strategy module — methodology only, no resume
  rewrite. Truthfulness rules from root `SKILL.md` apply.
---

# Role Competency Extractor

Strategy module for the v0.3.x scoring and resume-version routing MVP. Reads the
asset layer, normalizes the JD demand signal, and emits a structured competency
profile that downstream modules and the JobOps scoring layer consume.

This module **does not** rewrite the resume. It only normalizes demand. Tailoring
is handled by `packages/strategy-modules/resume-rewrite-engine/`.

## Inputs (canonical)

- Raw JD text from JobOps (or pasted by the user via root `SKILL.md`)
- Job metadata: title, company, location, source, seniority, visa language
- `target_market` (default `north-america`)
- Candidate strategy assets (read-only):
  - `assets/profile/user-profile.md`
  - `assets/knowledge-base/references/workflow/jd-analysis.md`
  - `assets/knowledge-base/references/workflow/competency-framework.md`
  - `assets/knowledge-base/references/workflow/keyword-extraction.md`
  - `assets/knowledge-base/references/role-lenses/{A,B,C,D,HC}.md`
  - `assets/knowledge-base/references/market-contexts/{north-america,mainland-china,hong-kong}.md`
  - `assets/knowledge-base/references/scenarios/*.md`
  - `assets/knowledge-base/references/company-contexts/*.md`
  - `assets/knowledge-base/references/search-keywords.json`
  - `assets/knowledge-base/references/blacklist.txt`

## Output

Structured 9-section product per `output-schema.md`. Persisted by JobOps to the
review queue and consumed by:
- JobOps scoring layer (uses `role_family` / `competency_tags` / `evidence_requirements` / `visa_risk` / `scoring_notes`)
- `resume-rewrite-engine` (uses competency model as primary targeting input)

Validates against `contracts/schemas/job-score.schema.json` for the fields it shares.

## Workflow

### Step 1 — Validate inputs and load context

1. Confirm at least 1 JD. For multi-JD analysis (≥2), confirm they belong to the
   same role family per `competency-framework.md §1`. If unstable → flag in
   Section I (Limitations).
2. Resolve `target_market` (default `north-america`); load corresponding
   `market-contexts/<market>.md`.
3. Load `general-rules.md` and `competency-framework.md` always.

### Step 2 — JD structural decomposition

Apply `workflow/jd-analysis.md` 5-layer decomposition:
core positioning → hard requirements → core capabilities → bonus → keywords.

### Step 3 — Role family validation + Lens assignment

1. Apply `competency-framework.md §1` Role Family Validation.
2. Determine `role_family` from `{A_strategy_research, B_data_analytics,
   C_product_ops, D_finance_markets, HC_human_capital, other}` per
   `competency-framework.md §2` Lens 判定 table.
3. Load the matching lens file (`role-lenses/<X>-*.md`).
4. Identify the single-owner scenario per `competency-framework.md §2.1`. Load it.
5. If blended (≥60% primary, secondary ≥20%): apply `competency-framework.md §2.2`,
   record `secondary_lens` and `blend_ratio` in `scoring_notes`. The scenario
   stays single-owner; routing variance lives in `scoring_notes`, not in lens or
   scenario files.
6. If company-context applies (internet / automotive), load corresponding
   `company-contexts/*.md`.

### Step 4 — Capability & priority extraction

Apply `competency-framework.md §3-§5`:
- §3 Responsibility Clustering
- §4 Capability Extraction (5 dimensions)
- §5 Priority Ranking (Tier 1 / 2 / 3)

### Step 5 — Hidden screening logic

Apply `competency-framework.md §6`. Each inferred criterion must be grounded in
specific JD signal — no speculation.

### Step 6 — Keyword architecture

Apply `workflow/keyword-extraction.md` 5-tier extraction (Tier 1 core role / 2
capability / 3 tools / 4 verbs / 5 semantic equivalents) with frequency × placement
scoring.

### Step 7 — Visa risk

Apply `competency-framework.md §7`. Output 5-value enum:
`clear | generic_authorized_neutral | sponsor_positive | blocked | unknown`.
`blocked` → hard skip downstream.

### Step 8 — Market localization

Apply `market-contexts/<market>.md` JD 解读 layer to adjust Tier boundaries,
hidden screening signals, and keyword form. Do not adjust resume-side
conventions here — that's the rewrite engine's job.

### Step 9 — Resume version routing hint

Output `resume_version_hints` as a subset of `{A, B, C, D, HC}` ordered by fit.
Primary lens determines first hint. Blended cases include both primary and
secondary lens versions.

### Step 10 — Emit structured output

Format per `output-schema.md`. All 9 sections required (Section I confidence
must be present even if low).

## Hard rules

Truthfulness 护栏 inherited from root `SKILL.md` §细则 (do not restate). Module-specific:

- **Methodology only, no resume rewrite.** Caller handles tailoring.
- **No fabrication of JD content.** Only normalize what's there.
- **`scoring_notes` is the only place where lens / scenario routing variance is allowed.** Lens files and scenario files stay single-owner.
- **Visa risk uses the 5-value schema enum**; `role_family` uses the prefixed form. Both per `contracts/schemas/job-score.schema.json` and `workflow/competency-framework.md §9`.
- **All inferred screening criteria must cite the JD signal** that supports them.
- **Limitations section (Section I) is mandatory**, even at high confidence.
- **No invented metrics or seniority claims** about the role.
