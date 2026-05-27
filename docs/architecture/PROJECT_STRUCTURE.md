# Project Structure

`Resume_Optimizer` is organized as a strategy asset repository.

## Source-of-truth assets

- `assets/profile/user-profile.md`: candidate profile, experience table, skill stack, optimization history.
- `assets/experience-bank/raw/*.md`: detailed experience ground truth.
- `assets/experience-bank/index.json`: machine-readable routing/cache view. Regenerate from source files when experience content changes.
- `assets/knowledge-base/references/`: reusable methods, scenarios, templates, search keywords, blacklist, and speedlearn rules.

## Resume assets

- `assets/resume-bank/versions/A_strategy_research/`: strategy, consulting, research roles.
- `assets/resume-bank/versions/B_data_analytics/`: data and analytics roles.
- `assets/resume-bank/versions/C_product_ops/`: product and operations roles.
- `assets/resume-bank/versions/D_finance_markets/`: finance and market research roles.
- `assets/resume-bank/versions/HC_human_capital_analytics/`: human capital, org effectiveness, people analytics.
- `assets/resume-bank/versions/custom/`: application-specific outputs.

## Automation contracts

- `contracts/schemas/experience.schema.json`: contract for `assets/experience-bank/index.json`.
- `contracts/schemas/resume-version.schema.json`: contract for resume metadata.
- `contracts/schemas/job-score.schema.json`: target scoring output for future JobOps integration.

## Operations app and strategy modules

- `ops/jobops/`: imported source snapshot of the user's JobOps fork. It is the future operations hub for discovery, scoring, dashboard/review queue, artifact generation, and tracking.
- `docs/archive/`: legacy planning docs (Hermes/JobOps era + old architecture). Moved from `ops/hermes/` 2026-05-26.
- `packages/strategy-modules/`: integrated strategy-module specs that bridge Resume_Optimizer assets into JobOps behavior.
- `packages/strategy-modules/role-competency-extractor/`: JD-to-role-demand extraction boundary.
- `packages/strategy-modules/resume-rewrite-engine/`: resume version routing and controlled tailoring boundary.
- `config/integration-map.yaml`: current map of asset layer, JobOps source, and planned integration points.
- `scripts/`: repo validation and index generation scripts.
