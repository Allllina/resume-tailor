#!/usr/bin/env python3
"""Contract drift-gate — the machine guarantee that FE and BE can't silently drift.

Runs two checks and exits non-zero if either fails:

1. **TS type drift** — `scripts/gen_ts_types.py --check`. Fails when a schema
   changed but `ui/src/types/generated.ts` was not regenerated.
2. **Fixture validity** — every `contracts/fixtures/<name>.example.json` is
   validated against `contracts/schemas/<name>.schema.json` (JSON Schema,
   dialect auto-detected). Fixtures with no matching standalone schema (e.g.
   sub-object examples like `match-matrix`, `dual-review`) are reported and
   skipped, not failed. Non-`*.example.json` files (multi-scenario corpora
   such as `jd-scenarios.json`) are ignored.

Why this exists: see docs/handoff/2026-05-27-shared-contract-protocol.md and
docs/HANDSHAKE.md. The contract (contracts/schemas/*.json) is the single
source of truth; this gate makes any divergence a red build instead of a
silent bug.

Usage:
  python3 scripts/check_contracts.py          # run both checks
  python3 scripts/check_contracts.py --fixtures-only
  python3 scripts/check_contracts.py --types-only

Requires `jsonschema` (already a harness dependency: jsonschema>=4.23).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "contracts" / "schemas"
FIXTURES_DIR = REPO_ROOT / "contracts" / "fixtures"
GEN_TYPES = REPO_ROOT / "scripts" / "gen_ts_types.py"


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def check_types() -> list[str]:
    """Run the generated.ts drift check. Returns a list of failure messages."""
    if not GEN_TYPES.exists():
        return [f"missing {_rel(GEN_TYPES)} — cannot run TS drift check"]
    proc = subprocess.run(
        [sys.executable, str(GEN_TYPES), "--check"],
        capture_output=True,
        text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return [
            "ui/src/types/generated.ts is stale vs contracts/schemas/. "
            "Run `make gen-types` and commit the result.\n"
            + "    " + out.replace("\n", "\n    ")
        ]
    return []


def check_fixtures() -> list[str]:
    """Validate each *.example.json against its matching schema."""
    try:
        from jsonschema.validators import validator_for
    except ImportError:
        return [
            "jsonschema is not installed (need jsonschema>=4.23). "
            "Install it (it's a harness dependency) and retry."
        ]

    if not FIXTURES_DIR.exists():
        print(f"  (no {_rel(FIXTURES_DIR)} dir — nothing to validate)")
        return []

    failures: list[str] = []
    validated = 0
    skipped: list[str] = []

    main_schema_path = SCHEMAS_DIR / "harness-tailor-output.schema.json"
    main_schema_defs = {}
    if main_schema_path.exists():
        try:
            main_schema_data = json.loads(main_schema_path.read_text())
            main_schema_defs = main_schema_data.get("$defs", {})
        except Exception:
            pass

    for fixture in sorted(FIXTURES_DIR.glob("*.example.json")):
        base = fixture.name[: -len(".example.json")]
        schema_path = SCHEMAS_DIR / f"{base}.schema.json"
        
        schema = None
        schema_src_name = ""
        
        if schema_path.exists():
            try:
                schema = json.loads(schema_path.read_text())
                schema_src_name = schema_path.name
            except (json.JSONDecodeError, OSError) as e:
                failures.append(f"{_rel(schema_path)}: cannot read schema — {e}")
                continue
        elif base in main_schema_defs:
            schema = main_schema_defs[base]
            schema_src_name = f"harness-tailor-output.schema.json#$defs/{base}"
        else:
            skipped.append(base)
            continue

        try:
            instance = json.loads(fixture.read_text())
        except (json.JSONDecodeError, OSError) as e:
            failures.append(f"{_rel(fixture)}: cannot read fixture — {e}")
            continue

        ValidatorCls = validator_for(schema)
        try:
            ValidatorCls.check_schema(schema)
        except Exception as e:  # noqa: BLE001 — surface any schema-meta error
            failures.append(f"{schema_src_name}: invalid schema — {e}")
            continue

        validator = ValidatorCls(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            for err in errors:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                failures.append(f"{_rel(fixture)} @ {loc}: {err.message}")
        else:
            validated += 1
            print(f"  ✓ {fixture.name} ↔ {schema_src_name}")

    if skipped:
        print(
            f"  · skipped (no standalone <name>.schema.json): {', '.join(skipped)}"
        )
    print(f"  validated {validated} fixture(s) against their schemas")
    return failures


def main(argv: list[str]) -> int:
    types_only = "--types-only" in argv
    fixtures_only = "--fixtures-only" in argv

    all_failures: list[str] = []

    if not fixtures_only:
        print("• TS type drift check (generated.ts vs contracts/schemas/)")
        all_failures += check_types()

    if not types_only:
        print("• Fixture validity (contracts/fixtures/*.example.json)")
        all_failures += check_fixtures()

    print()
    if all_failures:
        print(f"❌ contract drift-gate FAILED ({len(all_failures)} issue(s)):")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print("✅ contracts in sync (types + fixtures).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
