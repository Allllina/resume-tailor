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
  (or the seeded sample at `assets/profile/user-profile.sample.md`), and the Send button will
  become active. This is by design — the system needs at least a resume to tailor against.

## Functional gaps (non-blocking)

- `jd_total_score` (the 7-dimension composite JD score) is not yet computed
  end-to-end; the individual dimension scores are available.
- The "optimization history" table in your profile is not written back
  automatically on run completion.
- No data-migration story yet: if the data schema changes between versions,
  existing local user data may need manual adjustment.
- No `make doctor` health-check command yet — if setup fails, check the
  README troubleshooting section and backend logs.

## Reporting

Found something else? Open an issue on the GitHub repo.
