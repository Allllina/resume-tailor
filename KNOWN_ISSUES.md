# Known Issues

This is an early self-hosted MVP. The core pipeline (JD analysis → rewrite →
onboarding → truthfulness verify) works; the items below are known gaps that
do not block the core flow.

## Environmental

- **PDF preview needs Docker or a TeX Live toolchain.** Without it, the
  `.tex` artifact is still produced and PDF rendering returns an explicit
  `503 unavailable` state (not a crash). Install Docker or TeX Live to enable
  in-app PDF preview.

## First-run gotcha

- **The JD composer Send button is disabled until you complete Setup.** `make seed-sample` copies
  the sample asset files into place, but the backend's user data directory is only initialised when
  you actually upload a resume through the Setup wizard (Step 1). Open `/setup`, upload your resume
  (or re-upload the seeded sample PDF / `.tex` / `.md`), and the Send button will become active.
  This is by design — the system needs at least a resume to tailor against. The README quickstart
  calls this out explicitly.

## Functional gaps (non-blocking)

- `jd_total_score` (the 7-dimension composite JD score) is not yet computed
  end-to-end; the individual dimension scores are available.
- The "optimization history" table in your profile is not written back
  automatically on run completion.
- No data-migration story yet: if the data schema changes between versions,
  existing local user data may need manual adjustment.
- No `make doctor` health-check command yet — if setup fails, check the
  README troubleshooting section and backend logs.

## Release smoke (`v1.0.0-public`, 2026-05-27)

Fresh-clone quickstart was verified: `make seed-sample` → Python 3.11 venv → `pip install -e ".[dev]"` →
`ui` `npm install` → `make backend` + resume upload via Setup/API → **one live JD** through
`POST /api/tier1-tailor` (~60s). Run produced a reviewable `.tex` artifact (PDF preview returned **503**
without Docker/TeX, as expected).

If you skip master generation in Setup, the pipeline may finish with `degraded_to_manual` — still usable
for reviewing diagnosis output, but complete Setup for best tailoring quality.

## Reporting

Found something else? Open an issue on the GitHub repo.
