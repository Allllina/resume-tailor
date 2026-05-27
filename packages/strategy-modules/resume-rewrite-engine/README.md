# Resume Rewrite Engine

Status: integrated as a strategy-module specification in v0.2.0 foundation.

Role in the system:

- Consumes role competency extraction and job score results.
- Selects the best canonical resume version.
- Produces a controlled tailoring plan grounded in the experience bank.

Canonical inputs:

- Role competency profile from `packages/strategy-modules/role-competency-extractor/`.
- Job score conforming to `contracts/schemas/job-score.schema.json`.
- Candidate assets:
  - `assets/experience-bank/index.json`
  - `assets/experience-bank/raw/*.md`
  - `assets/resume-bank/versions/*/metadata.json`
  - canonical resume source files under `assets/resume-bank/versions/`
  - `assets/knowledge-base/references/workflow/quality-pass.md`
  - `assets/knowledge-base/references/workflow/latex-output.md`

Canonical outputs:

- `matched_resume_version`
- `selected_experience_ids`
- `protected_sections`
- `rewrite_plan`
- `quality_checklist`
- optional generated artifact paths under ignored `outputs/` or JobOps local data

Strategic positioning rules:

- Internet/product/ops roles: emphasize business sense, product intuition, growth/ops metrics, and user/business impact.
- Consulting/strategy roles: emphasize industry insight, structured problem solving, and client-facing impact.
- Human Capital / People Analytics / Org roles: hard-sell Mercer, Desay SV org performance, and Desay SV overseas subsidiary governance.
- Avoid minor wording-only tailoring; optimize for differentiated positioning and measurable proof.

Implementation boundary:

This module should not fabricate evidence. Every tailored bullet must map back to a source experience or approved speedlearn item.