"""Shared validation helpers for FastAPI endpoints that mutate state.json.

The harness backend persists `state.json` files that must conform to
`contracts/schemas/harness-tailor-output.schema.json`. Endpoints that
mutate these files (PATCH /lifecycle today; D.5 verify-claim tomorrow)
must re-validate before write so a backend bug cannot poison the on-disk
shape — once corrupted, downstream readers (UI, summaries, lens routing)
silently misbehave.

Why HTTP 500 on violation: a schema failure here means the *backend* built
an invalid dict. The client sent valid input (verified separately at
endpoint entry) and has no way to repair this. Surfacing as 500 makes the
bug visible in monitoring rather than masquerading as a 422 the client
might retry.

Future endpoints (D.5 verify-claim) should call `validate_state_for_persist`
right before the temp-file write in their atomic-rename block.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from loguru import logger

from harness.schemas.loader import SchemaRegistry, SchemaValidationError


# Schemas are shipped with the codebase under <repo>/contracts/schemas/, so
# we resolve them via this file's location rather than config.repo_root.
# Why: tests routinely monkeypatch config.repo_root to a tmp dir to isolate
# data/users/ — that tmp dir has no schemas. The contracts dir is fixed at
# the actual repo root, 5 parents up: api → harness → src → harness → packages → repo.
_REPO_ROOT_FROM_PACKAGE = Path(__file__).resolve().parents[5]


# Cached singleton: SchemaRegistry eagerly loads + meta-validates every
# *.schema.json file at __init__ (~6 small schemas, cheap). We construct
# lazily on first call so import-time errors don't break unrelated modules.
_registry: SchemaRegistry | None = None


def _get_registry() -> SchemaRegistry:
    global _registry
    if _registry is None:
        _registry = SchemaRegistry(_REPO_ROOT_FROM_PACKAGE)
    return _registry


def validate_state_for_persist(state: dict, run_id: str) -> None:
    """Validate a state dict against `harness-tailor-output` before write.

    Raises HTTPException(500) on schema violation — this indicates a
    backend bug, not a client error. The violation is logged with run_id
    + offending field path for debuggability.

    Callers should invoke this immediately before the atomic temp-file
    write so a non-conformant dict never reaches disk.
    """
    try:
        _get_registry().validate("harness-tailor-output", state)
    except SchemaValidationError as e:
        logger.error(f"state.json schema violation for run {run_id}: {e}")
        raise HTTPException(
            500,
            f"backend produced an invalid state for run {run_id}; "
            f"refusing to persist (see server logs for details)",
        )


def validate_verification_log_for_persist(log: dict, run_id: str) -> None:
    """Validate a verification_log dict against `verification-log` before write.

    Wave 4 D.5: paired with `validate_state_for_persist` so the verify-claim
    endpoint's append-only log can't drift from its schema (same rationale —
    catches dev errors before they reach disk).
    """
    try:
        _get_registry().validate("verification-log", log)
    except SchemaValidationError as e:
        logger.error(f"verification_log.json schema violation for run {run_id}: {e}")
        raise HTTPException(
            500,
            f"backend produced an invalid verification log for run {run_id}; "
            f"refusing to persist (see server logs for details)",
        )
