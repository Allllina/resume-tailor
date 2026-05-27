# Role Competency Extractor

Status: integrated as a strategy-module specification in v0.2.0 foundation.

Role in the system:

- JobOps discovers or imports a job.
- This module extracts what the role is really asking for.
- The extracted profile feeds scoring, resume-version routing, and tailoring.

Canonical inputs:

- Raw JD text from JobOps.
- Job metadata: title, company, location, source, seniority, visa language.
- Candidate strategy assets:
  - `assets/profile/user-profile.md`
  - `assets/knowledge-base/references/workflow/jd-analysis.md`
  - `assets/knowledge-base/references/search-keywords.json`
  - `assets/knowledge-base/references/blacklist.txt`

Canonical outputs (aligned with `assets/knowledge-base/references/workflow/competency-framework.md §9` and `contracts/schemas/job-score.schema.json`):

- `role_family`: `A_strategy_research` | `B_data_analytics` | `C_product_ops` | `D_finance_markets` | `HC_human_capital` | `other`
- `competency_tags`: business / analytics / stakeholder / org / product / research / finance tags
- `evidence_requirements`: what proof must be shown in the resume
- `visa_risk`: `clear` | `generic_authorized_neutral` | `sponsor_positive` | `blocked` | `unknown`
- `resume_version_hints`: subset of `{A, B, C, D, HC}` (matches `assets/resume-bank/versions/*/metadata.json` ids)
- `scoring_notes`: reasoning used by the JobOps scoring layer; includes secondary lens annotation when blended

Visa rule reminder (5-value enum, see `competency-framework.md §7`):

- `generic_authorized_neutral` — generic "authorized to work" language (F-1 OPT satisfies)
- `sponsor_positive` — explicit sponsorship available
- `blocked` — explicit no-sponsorship / citizen-only / clearance-only language → hard skip
- `clear` — JD explicitly indicates no visa concern for the candidate
- `unknown` — JD does not mention work authorization

Implementation boundary:

This module should not rewrite the resume. It only normalizes the job demand signal.