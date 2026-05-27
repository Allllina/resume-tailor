# resume-tailor

A self-hosted, bring-your-own-data AI resume tailoring tool. You bring your resume and experiences; the tool analyses job descriptions, diagnoses fit, generates a tailored resume with quality passes, and flags any AI-fabricated claims for your review before you submit.

**Runs entirely on your own machine.** No SaaS, no subscriptions — only your Anthropic API key.

---

## What it does

| Step | What you get |
|---|---|
| Paste a JD | Fit diagnosis with a per-requirement match matrix and competitive assessment |
| Generate tailored resume | Tiered rewrite engine with 4 quality passes (keyword alignment, readability, AI-tone cleaning, truthfulness) |
| Onboarding | Upload your own resume + experiences via the Setup wizard; system builds per-direction master resumes via LLM |
| Pass 3 verify | Review each AI-sourced claim (approve / reject / edit) before the resume is unlocked for submission |

Output: a `.tex` artifact (PDF preview available with Docker/TeX Live — see [KNOWN_ISSUES.md](KNOWN_ISSUES.md)).

---

## Requirements

- Python 3.11+
- Node 18+
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- (Optional) Docker or TeX Live for PDF preview

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/Allllina/resume-tailor.git
cd resume-tailor

# 2. Seed sample data into place (idempotent — skips paths you have already
#    populated, so safe to re-run after you add your own data)
make seed-sample

# 3. Configure your LLM key
cp packages/harness/.env.example packages/harness/.env
# Edit packages/harness/.env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
#
# Want to use a local proxy (LiteLLM / OpenAI-compatible / DeepSeek / Kimi /
# 通义千问)? See the OpenAI block in .env.example.

# 4. Backend Python deps
cd packages/harness
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd ../..

# 5. Frontend deps
cd ui && npm install && cd ..

# 6. Run (two terminals)
make backend     # http://127.0.0.1:8001
make ui          # http://localhost:8080
```

Then open **http://localhost:8080** in your browser.

---

## First-time flow

1. **Setup** — upload your own resume and experiences, or edit the seeded sample files under `assets/profile/` and `assets/experience-bank/`. The system generates per-direction master resumes via LLM.
2. **Paste a JD** — the floating composer sends the JD through the full pipeline.
3. **Inbox** — the tailored draft appears with fit diagnosis, rewrite output, and a truthfulness badge.
4. **Run detail** — review the match matrix, dual HM/HRBP perspective, radar chart, and each AI-surfaced claim.
5. **Pass 3 verify** — approve or reject each claim before downloading the `.tex`.

---

## Bring your own data

`make seed-sample` copies the anonymized sample files into the real paths the app reads. You can then replace them with your actual data:

| Sample file | Real path (gitignored) | What to put there |
|---|---|---|
| `assets/profile/user-profile.sample.md` | `assets/profile/user-profile.md` | Your career profile, target directions, visa status |
| `assets/experience-bank/index.sample.json` | `assets/experience-bank/index.json` | Your experience index |
| `assets/experience-bank/raw.sample/*.md` | `assets/experience-bank/raw/*.md` | Detailed per-role experience files |
| `assets/resume-bank/versions/*/resume.sample.zh.tex` | `resume.zh.tex` per version | Your base resume per direction |

Your real data stays gitignored and never leaves your machine.

---

## Repository structure

```text
resume-tailor/
  Makefile                          # seed-sample, backend, ui, test targets
  SKILL.md                          # 10-step tailoring workflow methodology
  VERSIONING.md

  assets/
    profile/
      user-profile.sample.md        # template — copy → user-profile.md + edit
    experience-bank/
      index.sample.json             # template
      raw.sample/                   # 3 anonymized sample roles
    resume-bank/
      versions/{A,B,C,D,HC}/        # per-direction resume templates
    knowledge-base/
      references/
        workflow/                   # jd-analysis, rewrite, quality-pass, etc.
        role-lenses/                # 5 career-direction lens definitions
        scenarios/                  # 14 tailoring scenarios
        market-contexts/            # NA / CN / HK JD + resume rules
        company-contexts/           # industry overlays

  contracts/schemas/                # JSON schemas for module I/O
  packages/
    harness/                        # FastAPI backend (Python)
      src/harness/
        api/                        # REST endpoints
        repl/                       # PPAF pipeline orchestrator
        llm/                        # LLM provider abstraction
        forecast/                   # fit diagnosis engine
        review/                     # HM/HRBP dual-perspective review
        gap_bridging/               # gap bridging planner
      tests/
    strategy-modules/               # callable sub-skill specs + schemas

  ui/                               # React 19 / TanStack / Vite frontend
    src/
      routes/                       # page routes (index, run detail, setup…)
      components/                   # fit-diagnosis, draft-review, etc.

  docs/architecture/                # system architecture + project structure
  scripts/                          # validate_structure, seed_sample, etc.
  config/                           # integration-map.yaml
```

---

## Running tests

```bash
# Backend
cd packages/harness && source .venv/bin/activate
pytest tests/ -q

# Frontend
cd ui && npm run test -- --run
```

---

## Known issues

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

---

## License

MIT — see [LICENSE](LICENSE).
