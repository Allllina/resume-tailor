"""harness.rewrite — Wave 4 D.2a resume-rewrite-engine module.

LLM-driven port of `packages/strategy-modules/resume-rewrite-engine`.
Produces the 10-section structured rewrite product (sections A-J + a
`_method` marker) for Tier 2/3 tailoring runs. Tier 1 short-circuits
with `_method = "skipped_tier_1"` and no LLM work.

Public API:
    - `rewrite_bullets(...)` — async orchestrator.
    - `RewriteOutput`        — pydantic model mirroring the 10-section output.
    - `RewriteBullet`        — pydantic model for one Section G bullet.
    - `UnsourcedClaimError`  — raised when a claimed_fact cannot be located
                                in the experience's raw markdown. Caller
                                decides recovery.
    - `verify_claims_in_raw` — substring-gate truthfulness pre-check.

D.2b will wire `rewrite_bullets` into `repl/loop.py`'s ACTION stage. D.4
will replace the substring gate with a LangGraph-based semantic verifier.
"""
from .engine import (
    DecisionLogEntry,
    RewriteBullet,
    RewriteOutput,
    UnsourcedClaimError,
    rewrite_bullets,
)
from .truthfulness import verify_claims_in_raw

__all__ = [
    "DecisionLogEntry",
    "RewriteBullet",
    "RewriteOutput",
    "UnsourcedClaimError",
    "rewrite_bullets",
    "verify_claims_in_raw",
]
