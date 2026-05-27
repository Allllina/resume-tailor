# Known Issues

This is an early self-hosted MVP. The core pipeline (JD analysis → rewrite →
onboarding → truthfulness verify) works; the items below are known gaps that
do not block the core flow.

## Environmental

- **PDF preview needs Docker or a TeX Live toolchain.** Without it, the
  `.tex` artifact is still produced and PDF rendering returns an explicit
  `503 unavailable` state (not a crash). Install Docker or TeX Live to enable
  in-app PDF preview.

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
