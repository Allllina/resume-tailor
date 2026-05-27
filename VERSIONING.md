# Versioning Policy

This repository uses product-version management, not only code-version management.

## Version families

- `v0.0.x`: original resume-optimizer skill era.
- `v0.1.x`: structured strategy-asset repository era.
- `v0.2.x`: JobOps integration foundation.
- `v0.3.x`: scoring and resume-version routing MVP.
- `v0.4.x`: tailoring workflow and artifact generation MVP.
- `v1.0.0`: stable resume operations system with repeatable discover -> score -> tailor -> track loop.

## Required documentation for every meaningful version

Each meaningful version should update `VERSION_LOG.md` with:

1. Product context: why this version exists.
2. Architecture decision: what changed in system design.
3. Resume strategy decision: what changed in positioning, versions, or tailoring rules.
4. Data/model contract changes: schemas, indexes, metadata, prompt interfaces.
5. Safety/privacy notes: what should not be automated or published.
6. Next-step implications.

## Git tag convention

Use semantic tags for stable milestones:

```text
v0.0.0-skill-initial
v0.1.0-foundation
v0.2.0-jobops-integration
v0.3.0-scoring-mvp
v0.4.0-tailoring-mvp
v1.0.0
```

For experimental work, use branches instead of tags:

```text
feature/jobops-indexer
feature/scoring-rubric
feature/langgraph-workflow
feature/gmail-tracking
```

## Commit convention

Use short conventional commits:

- `docs:` documentation and design rationale
- `chore:` repo structure, config, maintenance
- `feat:` new capability
- `fix:` bug fix
- `schema:` data contracts or index changes
- `resume:` base resume or tailoring asset changes
- `strategy:` positioning, scoring, or product-logic changes

Examples:

```text
strategy: add human capital analytics resume version
schema: define job score output contract
resume: add base data analytics Chinese resume
feat: add Resume_Optimizer indexer for JobOps
```

## Privacy rule

The repository contains personal and career materials. Keep the GitHub repo private unless a redacted public version is intentionally produced.
