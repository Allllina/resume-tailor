# Changelog

All notable changes to the public `resume-tailor` self-hosted MVP.

## [v1.0.0-public] — 2026-05-27

First public release of the BYOD resume tailoring stack.

- **Self-hosted core flow:** Setup wizard → paste JD → fit diagnosis → tailored resume → Pass 3 truthfulness review.
- **Bring your own data:** Sample assets via `make seed-sample`; real profile, experience bank, and per-direction resumes stay gitignored on your machine.
- **LLM:** Anthropic direct or OpenAI-compatible proxy via `packages/harness/.env` (see README quickstart).
- **UI:** Inbox + tailoring agent composer, run-detail review (diagnosis, rewrite, verify), mobile-friendly empty/error/loading states.
- **Known limits:** PDF preview requires Docker or TeX Live; see [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
