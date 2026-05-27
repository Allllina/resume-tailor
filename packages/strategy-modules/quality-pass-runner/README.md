# quality-pass-runner

Sub-skill that wraps the SKILL.md Step 6.5 four-pass quality pipeline as
a single callable unit.

## Why this exists

The original `SKILL.md` Step 6.5 specifies a strict-order four-pass
quality gate:

1. **Pass 1** — keyword injection (raises ATS hit rate).
2. **Pass 1.5** — Chinese readability (only for Chinese resumes).
3. **Pass 2** — AI taste removal (kills "赋能 / 助力 / 千篇一律" weasel
   words).
4. **Pass 3** — truthfulness verification (canonical R-1 to R-6 gate).

In the prior monolith form, these passes ran inline as part of root
SKILL.md and were executed iteratively across multiple V1-V15 cycles
during a typical session. Compliance audit (per `STATUS.md` 2026-05-08
and ADR 0006) showed Pass 1.5 and Pass 2 were not implemented; Pass 1
ran ad-hoc; only Pass 3 had a structural commitment (D.4 LangGraph
verifier, Wave 4).

Packaging the 4-pass pipeline into a single sub-skill solves the
compliance problem: once the orchestrator invokes
`quality-pass-runner`, all 4 passes run in strict order before control
returns. The user cannot skip Pass 2 or Pass 1.5 by saying "just give
me the LaTeX" — the pass order is enforced inside the sub-skill.

## Inputs and outputs

See [`SKILL.md`](./SKILL.md) for the full 10-step workflow and
[`output-schema.md`](./output-schema.md) for the structured output
contract.

## When to invoke

- **Always after `resume-rewrite-engine`** — orchestrator invokes this
  sub-skill once the rewrite engine produces its output.
- **Before `latex-renderer` (Mode L) or before `fit-diagnosis-engine`
  `post_rewrite` (Mode F)** — downstream consumers consume
  `final_resume_text` from this sub-skill, not the upstream rewrite
  output.
- **Idempotency check** — orchestrator should detect if the resume has
  already been quality-passed (e.g., `inputs_signature.rewritten_resume_hash`
  matches a recent invocation) and skip re-running.

## Hard rules

Inherits R-1 through R-6 (truthfulness 护栏) from root SKILL.md. Adds:

1. Pass order is immutable (1 → 1.5 → 2 → 3).
2. Pass 3 cannot be skipped.
3. Each pass operates on the previous pass's output, not the original
   input.
4. No fabrication via injection — Pass 1 cannot invent experience.
5. JD-native terms are protected from Pass 2 replacement.
6. Identity fields (company, position, school, degree, date) are
   locked at Pass 3.

See `SKILL.md` § "Hard rules" for full enumeration.

## Consumers

- Orchestrator (`SKILL.md` root): runs this sub-skill in late-FEEDBACK
  PPAF stage.
- `fit-diagnosis-engine` `post_rewrite` mode: consumes
  `final_resume_text` as its input.
- `latex-renderer` (inline / harness utility): renders
  `final_resume_text` to LaTeX.
- Inbox UI (in-repo, same project): renders pass-level findings as
  individual quality cards; surfaces `pending_user_review_flag` as an
  approval checklist (D.5 wiring planned).
- Harness `repl/stages/late_feedback.py` (Wave 4 D.4 partial): wires
  Pass 3 LangGraph verifier; Pass 1, 1.5, 2 implementation pending
  (Wave 5).

## Status

- Spec: ✅ This package (v1.0.0).
- Implementation:
  - Pass 1 (keyword injection): 🟡 partial — harness Tier 1 path has
    skill_injector; sub-skill-style invocation pending.
  - Pass 1.5 (Chinese readability): ❌ not implemented.
  - Pass 2 (AI taste removal): ❌ not implemented.
  - Pass 3 (truthfulness verification): ✅ implemented (Wave 4 D.4
    LangGraph).
- Tests: 🟡 partial — Pass 3 has tests; Pass 1/1.5/2 pending.

## Related

- ADR 0006 — `docs/decisions/0006-skill-superpowers-refactor.md`
- ADR 0005 — `docs/decisions/0005-five-stage-ppaf-variant.md`
  (Pass 3 lives in late-FEEDBACK stage)
- Reference doc — `assets/knowledge-base/references/workflow/quality-pass.md`
  (pass methodology + AI-taste replacement table)
- Sibling sub-skills:
  - `resume-rewrite-engine/` — produces input that this sub-skill
    operates on.
  - `fit-diagnosis-engine/` — consumes `final_resume_text` in
    `post_rewrite` mode.
  - `gap-bridging-planner/` — runs upstream; its 5a directives are
    consumed by `resume-rewrite-engine`.
