# fit-diagnosis-engine

Two-mode sub-skill that produces user-facing fit diagnosis at two PPAF
stages of the resume-optimization pipeline.

## Why this exists

The original `SKILL.md` Step 4 (匹配矩阵 + 整体评估 + 优化边界) and Step 8
(HM/HRBP 双视角 review + 雷达图) are the two biggest user-facing gaps in
the production agent (per `docs/STATUS.md`). Both are diagnostic in nature
and share rubric infrastructure, so they consolidate into a single sub-skill
with two invocation modes.

## Modes

| Mode | PPAF stage | Inputs | Outputs |
|---|---|---|---|
| `pre_rewrite` | PLANNING | JD analysis + competency profile + experience bank | Section 4: matching matrix + integrated assessment + optimization boundary (+ multi-JD coverage if applicable) |
| `post_rewrite` | late-FEEDBACK | Above + rewritten resume | Section 8: HM simulation + HRBP simulation + 6-axis radar + targeted recommendations |

## Inputs and outputs

See [`SKILL.md`](./SKILL.md) for the full 10-step workflow and
[`output-schema.md`](./output-schema.md) for the structured output contract.

## When to invoke

- **Always before rewrite** — orchestrator invokes `pre_rewrite` after
  `role-competency-extractor` and before `gap-bridging-planner`. Section 4
  output is surfaced to the user as honest forecast.
- **In Mode F after rewrite** — orchestrator invokes `post_rewrite` after
  `quality-pass-runner` to produce the review-queue artifact.
- **Skipped in Mode L for `post_rewrite`** — the lightweight orchestrator
  does not run the post-rewrite review pass by default. Users who want it
  can opt in explicitly.

## Hard rules

Inherits R-1 through R-6 from root SKILL.md. Adds:

1. No fabrication of evidence in matrix verdicts.
2. No score inflation in radar axes.
3. No optimism washing in integrated assessment.
4. Mode is immutable mid-flow.

See `SKILL.md` § "Hard rules" for full enumeration.

## Consumers

- Orchestrator (`SKILL.md` root): dispatches the sub-skill at PLANNING and
  late-FEEDBACK stages.
- `gap-bridging-planner`: consumes Section 4 matrix's ⚠️ partial rows as
  primary input.
- `resume-rewrite-engine`: consumes Section 4 matrix + boundary as
  contextual prioritization input.
- Inbox UI (in-repo, same project): renders matrix as colored table,
  radar as SVG chart, recommendations as actionable cards.
- Harness `repl/stages/early_feedback.py` (Wave 5+ planned): wires
  `pre_rewrite` invocation; current handler emits placeholders.
- Harness `repl/stages/late_feedback.py` (Wave 5+ planned): wires
  `post_rewrite` invocation; current handler omits this output.

## Status

- Spec: ✅ This package (v1.0.0).
- Implementation: ❌ Pending Wave 5 harness wiring.
- Tests: ❌ Pending implementation.

## Related

- ADR 0006 — `docs/decisions/0006-skill-superpowers-refactor.md`
- ADR 0005 — `docs/decisions/0005-five-stage-ppaf-variant.md`
- Sibling sub-skills:
  - `role-competency-extractor/` — produces the competency profile this
    sub-skill consumes.
  - `gap-bridging-planner/` — consumes this sub-skill's pre_rewrite
    Section 4 matrix.
  - `resume-rewrite-engine/` — consumes this sub-skill's pre_rewrite
    output as context.
  - `quality-pass-runner/` — runs between rewrite and post_rewrite
    invocation.
