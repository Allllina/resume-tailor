# gap-bridging-planner

Forward-looking sub-skill that converts pre-rewrite fit-diagnosis output
into actionable bridging plans for the rewrite engine.

## Why this exists

The original `SKILL.md` Step 5 (5a Reframe / 5b Add / 5c Skill Gap) and
Step 7-1 / 7-2 (structural / skill-bar advice) were inline in the root
file. They share two characteristics:

1. **Plan-not-prose.** Both produce directives and classifications, not
   rewritten text.
2. **Forward-looking.** Both run before `resume-rewrite-engine` and feed
   it directly.

Consolidating them into one sub-skill keeps the planning concern
separate from the rewriting concern (which is `resume-rewrite-engine`'s
exclusive job).

## Inputs and outputs

See [`SKILL.md`](./SKILL.md) for the full 10-step workflow and
[`output-schema.md`](./output-schema.md) for the structured output contract.

## When to invoke

- **Always after fit-diagnosis pre_rewrite** — orchestrator invokes this
  sub-skill after `fit-diagnosis-engine` mode `pre_rewrite` produces a
  Section 4-A matrix with at least one ⚠️ or ❌ row.
- **Always before resume-rewrite-engine** — the rewrite engine consumes
  the 5a directives as primary input.
- **Skipped if matrix is all green** — when every Section 4-A row is
  ✅ strong, the orchestrator skips this planner; nothing to bridge.

## Hard rules

Inherits R-1 through R-2 from root SKILL.md (no fabrication, no skill
inflation). Adds:

1. No directive without source evidence.
2. No silent over-claim — bridging hypotheses must be defensible.
3. No bullet text — output is plan, not prose.
4. Timeline awareness — honor `application_timeline` input.

See `SKILL.md` § "Hard rules" for full enumeration.

## Consumers

- `resume-rewrite-engine`: consumes 5a Reframe directives as primary
  input for bullet rewriting; consumes 5c skill-bar plan to update
  technical / AI / language skill rows.
- Orchestrator (`SKILL.md` root): surfaces 5b Add suggestions to user as
  out-of-band coaching action items.
- Inbox UI (in-repo, same project): renders 5a directives as
  before/after preview, 5b suggestions as a checklist, 5c skill-bar
  plan as add/remove diffs.
- Harness `repl/stages/planning.py` (Wave 5+ planned): wires this sub-skill
  between fit-diagnosis-engine and rewrite-engine.

## Status

- Spec: ✅ This package (v1.0.0).
- Implementation: ❌ Pending Wave 5 harness wiring.
- Tests: ❌ Pending implementation.

## Related

- ADR 0006 — `docs/decisions/0006-skill-superpowers-refactor.md`
- Sibling sub-skills:
  - `fit-diagnosis-engine/` — produces the matrix this sub-skill
    consumes.
  - `resume-rewrite-engine/` — consumes this sub-skill's output as
    primary rewrite input.
  - `role-competency-extractor/` — provides the competency profile this
    sub-skill loads for Tier 1 keyword reference.
