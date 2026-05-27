"""Schema sanity tests for pass3-verifier-io.schema.json (Wave 4 D.4a).

D.4a does not enforce schema validation at the loop boundary — that's D.4c.
These tests just confirm the schema loads and that a hand-crafted Pass 3
output dict matches the output branch's required structure.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "contracts" / "schemas" / "pass3-verifier-io.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_pass3_schema_loads_and_is_valid():
    """The schema file exists and is itself a well-formed JSON Schema."""
    assert SCHEMA_PATH.is_file(), f"schema file missing at {SCHEMA_PATH}"
    schema = _load_schema()
    # Meta-schema check; raises on malformed schema.
    Draft202012Validator.check_schema(schema)
    assert schema.get("title") == "Pass 3 Verifier I/O"
    # The schema uses oneOf with input + output branches.
    assert isinstance(schema.get("oneOf"), list) and len(schema["oneOf"]) == 2


def test_pass3_output_branch_validates_handcrafted_dict():
    """A hand-crafted per-bullet output dict validates against the output branch."""
    schema = _load_schema()
    # Pull the output sub-schema (oneOf[1]) and validate against it directly.
    # This bypasses the input branch's required-keys (bullets/source_files/...)
    # which would otherwise trip the top-level oneOf.
    output_branch = schema["oneOf"][1]
    assert output_branch.get("title") == "Pass 3 Output (per bullet)"

    sample = {
        "bullet_id": "b1",
        "verdict": "complete",
        "verified_facts": [
            {"claim": "led the team", "source": "raw § led the team", "confidence": 0.9}
        ],
        "unsourced_claims": [],
        "ask_user": [],
    }

    validator = Draft202012Validator(output_branch)
    errors = sorted(validator.iter_errors(sample), key=lambda e: e.path)
    assert errors == [], f"unexpected validation errors: {[e.message for e in errors]}"


def test_pass3_output_partial_with_ask_user_validates():
    """Partial verdict with ask_user entries validates."""
    schema = _load_schema()
    output_branch = schema["oneOf"][1]
    sample = {
        "bullet_id": "b2",
        "verdict": "partial",
        "verified_facts": [],
        "unsourced_claims": [
            {
                "claim": "increased revenue 42%",
                "action": "ask_user",
                "rationale": "numeric",
            }
        ],
        "ask_user": [
            {
                "question": "Can you confirm 42%?",
                "context": "numeric claim flagged",
            }
        ],
    }
    validator = Draft202012Validator(output_branch)
    errors = sorted(validator.iter_errors(sample), key=lambda e: e.path)
    assert errors == [], f"unexpected validation errors: {[e.message for e in errors]}"
