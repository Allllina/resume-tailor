# Strategy Modules

This directory turns the original SKILL.md monolith into 5 reusable
sub-skill packages. The root `SKILL.md` (now ~120-line orchestrator)
dispatches to these packages following Mode L (lightweight) or Mode F
(full) execution profile.

**Refactor reference:** see ADR 0006
(`docs/decisions/0006-skill-superpowers-refactor.md`) for the full
decision rationale, sub-skill boundaries, and Mode L/F dispatch table.

## Module catalog

| # | Module | Steps covered | Status |
|---|---|---|---|
| 1 | `role-competency-extractor/` | Step 3.5 (9-section competency profile) | ✅ Wave 4 D.4 wired in harness |
| 2 | `fit-diagnosis-engine/` | Step 4 (`pre_rewrite`) + Step 8 (`post_rewrite`) | 🟡 spec ready (this refactor); harness wiring pending Wave 5 |
| 3 | `gap-bridging-planner/` | Step 5 + Step 7-1/7-2 | 🟡 spec ready; harness wiring pending Wave 5 |
| 4 | `resume-rewrite-engine/` | Step 6 + Step 8.5 (10-section A-J rewrite) | ✅ Wave 4 D.2 wired in harness |
| 5 | `quality-pass-runner/` | Step 6.5 (Pass 1 + 1.5 + 2 + 3) | 🟡 partial (Pass 3 wired in D.4; Pass 1 partial; Pass 1.5 + Pass 2 pending Wave 5) |

## Module summaries

### 1. `role-competency-extractor/`

- **Purpose:** convert a JD (or set of JDs for the same role) into a
  9-section structured competency profile.
- **Inputs:** JD text, job metadata, target market, candidate assets.
- **Output:** 9 sections + flat-field summary aligned with
  `contracts/schemas/job-score.schema.json`.
- **Hard rule:** methodology only, no resume rewrite.

### 2. `fit-diagnosis-engine/` ← **NEW (this refactor)**

- **Purpose:** produce honest, user-facing fit diagnosis at two PPAF
  stages — `pre_rewrite` (Section 4 matching matrix + integrated
  assessment + optimization boundary) and `post_rewrite` (Section 8
  HM/HRBP review + 6-axis radar + targeted recommendations).
- **Inputs:** JD analysis + competency profile + candidate assets +
  (post_rewrite only) rewritten resume.
- **Output:** mode-bifurcated schema per `output-schema.md`.
- **Hard rule:** no fabrication, no score inflation, no optimism
  washing, mode immutable mid-flow.

### 3. `gap-bridging-planner/` ← **NEW (this refactor)**

- **Purpose:** convert pre-rewrite diagnosis matrix gaps into actionable
  bridging plans (5a Reframe directives + 5b Add suggestions + 5c Skill
  Gap classifications + structural recommendations).
- **Inputs:** fit-diagnosis-engine `pre_rewrite` output + competency
  profile + candidate assets + application timeline.
- **Output:** plan (not prose) per `output-schema.md`.
- **Hard rule:** no directive without source evidence, no skill
  inflation, no bullet text (rewriting is rewrite-engine's job).

### 4. `resume-rewrite-engine/`

- **Purpose:** consume competency profile + bridging plan + candidate
  assets, audit, prioritize, and emit a 10-section rewrite plan
  (Sections A-J).
- **Inputs:** competency profile + bridging plan + experience bank +
  lens / scenario / market context.
- **Output:** 10 sections per `output-schema.md`. Section I is the
  text-form final draft.
- **Hard rule:** truthfulness 护栏 from root SKILL.md; Tier 1 light
  tailoring restricts edits to headline / summary / skills (per
  ARCHITECTURE.md §9).

### 5. `quality-pass-runner/` ← **NEW (this refactor)**

- **Purpose:** run 4-pass quality pipeline in strict order (Pass 1
  keyword injection → Pass 1.5 Chinese readability → Pass 2 AI taste
  removal → Pass 3 truthfulness verification).
- **Inputs:** rewritten resume + competency profile + experience bank
  + JD text.
- **Output:** 4 pass-level result sections + aggregate verdict +
  `final_resume_text` per `output-schema.md`.
- **Hard rule:** pass order is immutable; Pass 3 cannot be skipped;
  JD-native terms protected from Pass 2; identity fields locked in
  Pass 3.

## Coupling graph

```text
fit-diagnosis-engine (pre_rewrite)
   ↓ Section 4-A matrix
   ↓ Section 4-C boundary
gap-bridging-planner
   ↓ Section 5a directives
   ↓ Section 5c skill plan
resume-rewrite-engine
   ↓ rewritten_resume
quality-pass-runner
   ↓ final_resume_text
   ├→ latex-renderer (Mode L 终点)
   └→ fit-diagnosis-engine (post_rewrite, Mode F only)
       ↓ Section 8 review + radar
       review queue / Inbox UI
```

## Implementation status

These 5 modules are **specification + workflow** for the refactor wave.
Modules 1 and 4 already have harness implementations (Wave 4 D.4 / D.2
respectively). Modules 2, 3, 5 are spec-ready; harness wiring is Wave 5
work scheduled per `docs/STATUS.md`.

The structured outputs (schema files in each module) are deliberately
schema-stable so harness implementation can persist them without
refactoring contracts.

## Future implementation (Wave 5+)

- Harness `repl/stages/planning.py` wires modules 2 (`pre_rewrite`) and 3.
- Harness `repl/stages/late_feedback.py` wires module 5 fully (Pass 1 +
  Pass 1.5 + Pass 2 round out the existing Pass 3 LangGraph verifier),
  and module 2 (`post_rewrite`) in Mode F.
- Harness `repl/stages/early_feedback.py` (existing) continues to host
  the tier router; no module change here.

These spec files in `packages/strategy-modules/` remain the source of
truth and the canonical contract regardless of harness implementation
language.
