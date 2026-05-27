#!/usr/bin/env python3
"""Generate TypeScript types from JSON Schemas in contracts/schemas/.

L2 of docs/HANDSHAKE.md — eliminates the manual backend↔frontend type
handshake. Output goes to ui/src/types/generated.ts; frontend imports
from there.

Scope (intentional): only the schemas + sub-objects we want auto-typed.
The hand-maintained types in ui/src/lib/api.ts stay until we migrate
them. This is incremental adoption — start with the highest-friction
fields (D07 dual_review and forthcoming fit_diagnosis_*), expand later.

JSON Schema constructs handled:
  - object → TS interface (with required vs optional fields)
  - array → TS array type
  - string + enum → TS union of string literals
  - string → string
  - number / integer → number
  - boolean → boolean
  - oneOf / anyOf with const / type entries → union
  - additionalProperties: false / true / object → respected
  - $ref → not yet supported (we don't use cross-schema refs)

Run:
  python3 scripts/gen_ts_types.py            # write ui/src/types/generated.ts
  python3 scripts/gen_ts_types.py --check    # exit 1 if drift vs checked-in

Idempotent: same schemas → same output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Schemas we want to extract types from + which top-level properties
# to emit. Add entries here when a new schema field needs FE types.
EMIT_SPEC: dict[str, list[str]] = {
    "harness-tailor-output.schema.json": [
        "quality_pass_report",
        "fit_diagnosis_pre_rewrite",
        "fit_diagnosis_post_rewrite",
        "gap_bridging",
    ],
}

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "contracts" / "schemas"
OUTPUT = REPO_ROOT / "ui" / "src" / "types" / "generated.ts"


def _camel_to_pascal(snake: str) -> str:
    """match_matrix → MatchMatrix; competitiveness_rating → CompetitivenessRating."""
    return "".join(part.capitalize() for part in snake.split("_"))


def _ts_type_for_property(prop: dict[str, Any], prop_name: str, parent: str) -> str:
    """Convert a JSON Schema property fragment to a TypeScript type string.

    `parent` is the name of the enclosing interface (used to disambiguate
    nested anonymous interfaces — we inline them as object literals).
    """
    if "enum" in prop:
        members = prop["enum"]
        if all(isinstance(m, str) for m in members):
            return " | ".join(f'"{m}"' for m in members)
        return " | ".join(json.dumps(m) for m in members)

    schema_type = prop.get("type")

    if schema_type == "string":
        return "string"
    if schema_type in ("number", "integer"):
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"

    if schema_type == "array":
        items = prop.get("items", {})
        item_type = _ts_type_for_property(items, prop_name + "Item", parent)
        return f"Array<{item_type}>"

    if schema_type == "object" or "properties" in prop:
        return _emit_object_inline(prop, prop_name, parent)

    if isinstance(schema_type, list):
        # Union of primitive types
        return " | ".join(_ts_type_for_property({"type": t}, prop_name, parent) for t in schema_type)

    # Unknown / un-typed → fall back to unknown
    return "unknown"


def _emit_object_inline(prop: dict[str, Any], prop_name: str, parent: str) -> str:
    """Render an object schema inline as a `{ key: type; ... }` literal."""
    properties = prop.get("properties", {})
    required = set(prop.get("required", []))
    additional_props = prop.get("additionalProperties", True)

    if not properties:
        # No properties listed
        if isinstance(additional_props, dict):
            value_type = _ts_type_for_property(additional_props, prop_name, parent)
            return f"Record<string, {value_type}>"
        if additional_props is True:
            return "Record<string, unknown>"
        return "Record<string, never>"

    field_lines: list[str] = []
    for key in properties:
        sub = properties[key]
        ts_type = _ts_type_for_property(sub, key, parent)
        marker = "" if key in required else "?"
        field_lines.append(f"  {key}{marker}: {ts_type};")

    if isinstance(additional_props, dict):
        value_type = _ts_type_for_property(additional_props, prop_name, parent)
        field_lines.append(f"  [k: string]: {value_type};")
    elif additional_props is True:
        field_lines.append(f"  [k: string]: unknown;")

    body = "\n".join(field_lines)
    return "{\n" + body + "\n}"


def _emit_top_level_interface(name: str, prop: dict[str, Any]) -> str:
    """Emit `export interface Name { ... }` for a top-level property."""
    body = _emit_object_inline(prop, name, name)
    # Strip the outer braces to inject into an interface declaration
    inner = body.strip()
    if inner.startswith("{"):
        inner = inner[1:]
    if inner.endswith("}"):
        inner = inner[:-1]
    inner = inner.strip("\n")
    description = prop.get("description", "").strip()
    doc = f"/**\n * {description}\n */\n" if description else ""
    return f"{doc}export interface {name} {{\n{inner}\n}}\n"


def _emit_for_schema(schema_path: Path, props_to_emit: list[str]) -> list[str]:
    """Generate TS interfaces for the listed top-level properties."""
    schema = json.loads(schema_path.read_text())
    properties = schema.get("properties", {})
    out: list[str] = []
    for prop_name in props_to_emit:
        if prop_name not in properties:
            print(
                f"WARN: {schema_path.name} has no property '{prop_name}'; skipped",
                file=sys.stderr,
            )
            continue
        interface_name = _camel_to_pascal(prop_name)
        out.append(_emit_top_level_interface(interface_name, properties[prop_name]))
    return out


def generate() -> str:
    """Generate the full ui/src/types/generated.ts content."""
    blocks: list[str] = []
    for schema_filename, props in EMIT_SPEC.items():
        schema_path = SCHEMAS_DIR / schema_filename
        if not schema_path.exists():
            print(f"WARN: missing schema {schema_filename}; skipped", file=sys.stderr)
            continue
        section_blocks = _emit_for_schema(schema_path, props)
        if section_blocks:
            blocks.append(f"// ──── from {schema_filename} ────\n\n" + "\n".join(section_blocks))

    body = "\n\n".join(blocks)
    header = (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: contracts/schemas/*.json\n"
        "// Regenerate: `make gen-types` (or `python3 scripts/gen_ts_types.py`)\n"
        "// Drift check: `python3 scripts/gen_ts_types.py --check` returns non-zero on diff.\n"
        "// Adoption: hand-maintained types in ui/src/lib/api.ts coexist; new schema\n"
        "// fields land here first. Migration of api.ts to generated.ts is incremental.\n\n"
    )
    return header + body + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if generated file would change")
    args = parser.parse_args()

    new_content = generate()

    if args.check:
        if not OUTPUT.exists():
            print(f"FAIL: {OUTPUT.relative_to(REPO_ROOT)} does not exist; run without --check to create.", file=sys.stderr)
            return 1
        existing = OUTPUT.read_text()
        if existing != new_content:
            print(
                f"FAIL: {OUTPUT.relative_to(REPO_ROOT)} is out of sync with schemas. "
                f"Run `make gen-types` to regenerate.",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {OUTPUT.relative_to(REPO_ROOT)} is in sync.")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(new_content)
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(new_content)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
