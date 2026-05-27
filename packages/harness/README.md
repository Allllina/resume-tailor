# packages/harness — Wave 1 Tier 1 PoC (v0.4.0)

Python backend implementing Harness Engineering REPL container + Tier 1 light-tailoring service for the `jobsearch-ops-agent` project.

**Status:** Wave 1 ships `POST /api/tier1-tailor` — a working Tier 1 light-tailoring pipeline (lens routing → master selection → Skills row reorder → Summary regenerate → .tex artifact). 150 unit + integration tests passing.

## See also

- [`docs/architecture/HARNESS_DESIGN.md`](../../docs/architecture/HARNESS_DESIGN.md) — canonical Harness reference (PPAF cycle, REPL container, 6 design principles, 3-plane architecture). Sections 3.1–3.4 map directly to this package's `repl/{read,eval,print,loop}.py`.
- [`docs/architecture/HARNESS_COMPLIANCE_AUDIT.md`](../../docs/architecture/HARNESS_COMPLIANCE_AUDIT.md) — Wave 0 baseline gaps. Wave 1 closes Gap 1 (PII filter), Gap 2 (R-1..R-8 JSON), Gap 4 (schema validation), Gap 6 (retry/timeout/circuit breaker).
- [`docs/decisions/0003-harness-as-architectural-foundation.md`](../../docs/decisions/0003-harness-as-architectural-foundation.md) — ADR + sunset criteria.
- [`docs/plans/archive/2026-05-04-wave1-tier1-poc.md`](../../docs/plans/archive/2026-05-04-wave1-tier1-poc.md) — this wave's plan (23 tasks).
- [`contracts/schemas/`](../../contracts/schemas/) — 6 Wave 0 contract schemas validated by `harness/schemas/loader.py`.

## Quick start

```bash
cd packages/harness
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # then edit HARNESS_ANTHROPIC_API_KEY
uvicorn harness.api.main:app --reload --port 8001
```

Server listens on `http://127.0.0.1:8001`.

## Run tests

```bash
pytest                    # all 150 tests
pytest tests/unit         # unit tests only
pytest tests/integration  # integration + E2E
pytest -v -k anker        # the Anker AIGC retro-test
```

## Local backend launch (anaconda venv quirk)

If `.venv/bin/python` on this machine is a symlink straight to anaconda's
interpreter (e.g. `/opt/anaconda3/bin/python3`), `uvicorn` will fail to
import `harness` because the editable install's `.pth` file (at
`.venv/lib/python<ver>/site-packages/__editable__.harness-0.4.0.pth`) is
not consumed by the anaconda interpreter. Workaround — pass `PYTHONPATH=src`
explicitly:

```bash
cd packages/harness
PYTHONPATH=src .venv/bin/python -m uvicorn harness.api.main:app \
  --host 127.0.0.1 --port 8001 --log-level warning
```

**Why pytest works without this:** `pyproject.toml` sets
`[tool.pytest.ini_options].pythonpath = ["src"]`, which pytest honors
regardless of how the venv resolves the `.pth` file. uvicorn boots a plain
Python interpreter and has no equivalent — hence the manual override.

**Symptom if you forget:** `ModuleNotFoundError: No module named 'harness'`
right when uvicorn boots, before any request is served.

This is preemptive documentation for D.4 (LangGraph claim-verifier) — the
implementer will hit this on first launch and we want the answer here.

## API

### `GET /health`

```bash
curl http://127.0.0.1:8001/health
# {"status":"ok"}
```

### `POST /api/tier1-tailor`

Request body validates against `contracts/schemas/harness-tailor-input.schema.json`:

```bash
curl -X POST http://127.0.0.1:8001/api/tier1-tailor \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "manual",
    "jd": {
      "source": "paste",
      "raw_text": "AIGC 内容实习生招聘. 生成式 AI Prompt Engineering Agent 工作流 LLM RAG 标签体系."
    },
    "candidate_profile_ref": "assets/profile/user-profile.md",
    "target_market": "cn"
  }'
```

Response (validates against `harness-tailor-output.schema.json`):

```json
{
  "run_id": "550e8400-...",
  "verdict": "complete",
  "tier_assigned": 1,
  "matched_resume_version": "C_product_ops",
  "lens_routing": {
    "primary_lens": "C_product_ops",
    "scenario": "ai-innovation",
    "used_llm_fallback": false
  },
  "tex_artifact_path": "/path/to/packages/harness/data/runs/<run_id>/resume.tex",
  "trace": { "perception_events": [...], "planning_events": [...], ... },
  "metrics": { "elapsed_seconds": 1.23, ... }
}
```

The `.tex` artifact is written to `packages/harness/data/runs/<run_id>/resume.tex`. Compile via Overleaf or local XeLaTeX.

## Architecture (this package)

```
src/harness/
├── api/                  # FastAPI HTTP layer
│   ├── main.py             # /health + router
│   └── tier1_tailor.py     # POST /api/tier1-tailor
├── repl/                 # REPL container (HARNESS_DESIGN §3)
│   ├── state.py            # RunState pydantic model
│   ├── read.py             # Token pipeline (Wave 1 minimal)
│   ├── eval.py             # Tier1Tools facade
│   ├── print.py            # Output assembler
│   └── loop.py             # PPAF orchestrator
├── tier1/                # 6 Tier 1 transforms
│   ├── lens_router.py      # Step 3: keyword + LLM fallback
│   ├── master_selector.py  # Step 5: pick base resume + fallback
│   ├── skill_injector.py   # Step 6: Skills row reorder (deterministic)
│   ├── label_rewriter.py   # Step 6: bullet 标签 (LLM)
│   ├── summary_writer.py   # Step 6: Summary (LLM)
│   └── disambiguator.py    # R-7 enforcement
├── policy/               # Policy gateway
│   ├── pii_filter.py       # PII redact + restore (Gap 1)
│   ├── rules_loader.py     # R-1..R-8 from JSON (Gap 2)
│   ├── injection_defense.py
│   └── gateway.py          # Verdict + decision record
├── claude/               # Anthropic SDK wrapper
│   ├── client.py           # Retry on transient errors
│   └── retry.py            # CircuitBreaker (Gap 6)
├── schemas/              # JSON Schema validator
│   └── loader.py           # SchemaRegistry (Gap 4)
├── metrics/              # SQLite event store
│   └── emitter.py          # MetricsEmitter
└── scrapers/             # JD source extractors
    └── tencent_doc.py      # 腾讯文档内推汇总 (PoC)

tests/
├── unit/                 # ~110 unit tests
└── integration/          # ~40 integration + E2E tests
```

## Wave 2 next

Per `docs/plans/archive/2026-04-27-agentify-with-harness.md` (now scoped to Pass 3 only): build LangGraph-based Pass 3 verifier agent. The current Wave 1 leaves three Tier 1 lacunae for Wave 2:

- `target_industry` derived from `target_market` heuristic (`cn → internet_operational`); should accept explicit hint via `harness-tailor-input.lens_hint` or new `target_industry` field.
- `candidate_tags` for `SummaryWriter` is hardcoded `[]`; should derive from `index.json[exp].capability_tags`.
- Token pipeline `read.py` is minimal; full 5-stage pipeline (relevance ranking + compression + template assembly) needed for Tier 2/3 with raw experience files.

See `docs/architecture/HARNESS_COMPLIANCE_AUDIT.md` §6 for the full retrofit gap list.
