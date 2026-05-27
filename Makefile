# Resume_Optimizer Makefile — common dev tasks.
# Run from repo root.

.PHONY: help status status-deep test test-harness test-quick lint backend ui clean seed-sample gen-types

help:
	@echo "First-time setup:"
	@echo "  make seed-sample   - Populate gitignored asset paths from anonymized samples"
	@echo "                       (idempotent — won't overwrite if you've uploaded your own)"
	@echo ""
	@echo "Project state:"
	@echo "  make status        - One-screen status (git / audit / debt / incidents) ~2s"
	@echo "  make status-deep   - status + full pytest run ~45s"
	@echo "  make gen-types     - Regenerate ui/src/types/generated.ts from contracts/schemas/"
	@echo ""
	@echo "Run:"
	@echo "  make backend       - (Re)start the harness backend on :8001 — kills any stale listener first"
	@echo "  make ui            - Start the UI dev server on :8080"
	@echo ""
	@echo "Test + lint:"
	@echo "  make test          - Run all backend tests"
	@echo "  make test-harness  - Same as test (alias)"
	@echo "  make test-quick    - Run unit tests only (skip integration)"
	@echo "  make lint          - Run ruff + mypy on harness"
	@echo "  make clean         - Remove __pycache__ + .pytest_cache"

status:
	@bash scripts/dev_status.sh

status-deep:
	@bash scripts/dev_status.sh
	@echo ""
	@echo "──────────────────────────────────────────────────────────────"
	@echo "Running full pytest..."
	@cd packages/harness && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --tb=line 2>&1 | tail -8

seed-sample:
	python3 scripts/seed_sample.py

gen-types:
	python3 scripts/gen_ts_types.py

test test-harness:
	cd packages/harness && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --tb=short

test-quick:
	cd packages/harness && PYTHONPATH=src .venv/bin/python -m pytest tests/unit/ -q --tb=short

backend:
	@echo "==> backend on :8001 (killing any stale listener first so you never run old code)"
	@PID=$$(lsof -nP -iTCP:8001 -sTCP:LISTEN -t 2>/dev/null | head -1); \
		if [ -n "$$PID" ]; then echo "    killing stale backend pid $$PID"; kill $$PID; sleep 1; fi
	cd packages/harness && PYTHONPATH=src .venv/bin/python -m uvicorn harness.api.main:app \
		--host 127.0.0.1 --port 8001 --log-level warning

ui:
	cd ui && npm run dev

lint:
	cd packages/harness && PYTHONPATH=src .venv/bin/python -m ruff check src tests
	cd packages/harness && PYTHONPATH=src .venv/bin/python -m mypy src --ignore-missing-imports

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
