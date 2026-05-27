#!/usr/bin/env python3
"""Validate the repository foundation structure.

Checks that essential tracked files exist. Private/gitignored asset paths
(user-profile.md, index.json, metadata.json, resume.zh.tex) are seeded by
`make seed-sample` and are checked via their .sample siblings here.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "KNOWN_ISSUES.md",
    "LICENSE",
    "docs/architecture/ARCHITECTURE.md",
    "assets/profile/user-profile.sample.md",
    "assets/experience-bank/index.sample.json",
    "assets/experience-bank/raw.sample/01-strategy-consulting.md",
    "assets/experience-bank/raw.sample/02-data-analytics.md",
    "assets/experience-bank/raw.sample/03-product-ops.md",
    "assets/knowledge-base/references/search-keywords.json",
    "assets/knowledge-base/references/speedlearn-whitelist.json",
    "assets/knowledge-base/references/blacklist.txt",
    "contracts/schemas/experience.schema.json",
    "contracts/schemas/resume-version.schema.json",
    "contracts/schemas/job-score.schema.json",
    "config/integration-map.yaml",
    "packages/strategy-modules/MODULES.md",
    "packages/strategy-modules/role-competency-extractor/README.md",
    "packages/strategy-modules/resume-rewrite-engine/README.md",
    "ops/jobops/package.json",
    "ops/jobops/orchestrator/package.json",
    "ops/jobops/shared/package.json",
]
RESUME_DIRS = [
    "A_strategy_research",
    "B_data_analytics",
    "C_product_ops",
    "D_finance_markets",
    "HC_human_capital_analytics",
]

errors = []
for rel in REQUIRED:
    if not (ROOT / rel).exists():
        errors.append(f"missing required file: {rel}")

# Check .sample metadata files (the real metadata.json files are gitignored)
for d in RESUME_DIRS:
    meta = ROOT / "assets" / "resume-bank" / "versions" / d / "metadata.sample.json"
    if not meta.exists():
        errors.append(f"missing sample metadata: assets/resume-bank/versions/{d}/metadata.sample.json")
    else:
        try:
            json.loads(meta.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON in {meta.relative_to(ROOT)}: {exc}")

# Check sample index (real index.json is gitignored, seeded by make seed-sample)
idx = ROOT / "assets" / "experience-bank" / "index.sample.json"
if idx.exists():
    try:
        json.loads(idx.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON in assets/experience-bank/index.sample.json: {exc}")

if errors:
    print("Validation failed:")
    for e in errors:
        print(f"- {e}")
    sys.exit(1)

print("Validation passed: repository foundation is structurally ready.")
