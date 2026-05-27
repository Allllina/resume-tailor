"""Common helpers shared by fit_diagnosis pre_rewrite + post_rewrite modes.

These are stage-agnostic. Both `engine.build_diagnosis(mode="pre_rewrite", ...)`
(this phase) and the future `mode="post_rewrite"` (F3) build the same
common header described in `packages/strategy-modules/fit-diagnosis-engine/
output-schema.md` ("Common header").

Common header fields (per spec):
  - sub_skill, mode, target_market, ppaf_stage, invoked_at
  - inputs_signature: jd_analysis_id, competency_profile_id,
    current_resume_hash (null when pre_rewrite)
  - multi_jd, confidence, _method

`competitiveness_rating` is not derived here — the LLM-normalizer
(per-mode) emits it; callers attach the value into the header dict
returned by build_diagnosis.

Confidence is computed up-front from the input shape (jd count +
competency completeness + market loaded) plus the post-LLM `_method`
marker. _method == "fallback_no_llm" forces low confidence regardless
of inputs.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal


_VALID_MARKETS: frozenset[str] = frozenset(
    {"north-america", "mainland-china", "hong-kong"}
)
_VALID_MODES: frozenset[str] = frozenset({"pre_rewrite", "post_rewrite"})
_VALID_METHODS: frozenset[str] = frozenset(
    {"llm", "llm_partial", "fallback_no_llm"}
)

Confidence = Literal["high", "moderate", "low"]


def _stable_hash(payload: Any) -> str:
    """Deterministic SHA-256 short hash for an arbitrary JSON-serializable payload.

    Used to generate `inputs_signature.jd_analysis_id` /
    `competency_profile_id` when the caller doesn't pass an explicit
    upstream id. Returns first 16 hex chars (64-bit collision space —
    plenty for in-run signature traceability).
    """
    if payload is None:
        return "unknown"
    try:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        serialized = repr(payload)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return digest[:16]


def compute_confidence(
    *,
    jd_count: int,
    competency_complete: bool,
    market_loaded: bool,
    method: str,
) -> Confidence:
    """Map input-quality + LLM-degradation signals to a 3-level confidence enum.

    Per `output-schema.md` "Confidence rating":
      - high: ≥4 JDs analyzed AND complete competency model AND
        market_context loaded.
      - moderate: 1-3 JDs OR partial competency model (still LLM-driven).
      - low: single JD with default-market fallback OR _method ==
        fallback_no_llm.

    `method` value of "fallback_no_llm" always collapses confidence to
    "low" — the placeholder output cannot be trusted regardless of how
    rich the inputs were.
    """
    if method == "fallback_no_llm":
        return "low"
    if jd_count <= 1 and not market_loaded:
        return "low"
    if jd_count >= 4 and competency_complete and market_loaded:
        return "high"
    return "moderate"


def build_common_header(
    *,
    mode: str,
    target_market: str,
    jd_analysis: Any,
    competency_profile: Any,
    current_resume_hash: str | None,
    multi_jd: bool,
    method: str,
    competitiveness_rating: str,
    confidence: Confidence,
    invoked_at: datetime | None = None,
) -> dict:
    """Assemble the per-spec common header attached to every diagnosis output.

    `mode` selects ppaf_stage:
      - pre_rewrite  → "planning"
      - post_rewrite → "late_feedback"

    `current_resume_hash` MUST be None when mode == "pre_rewrite" per
    the inputs_signature contract; the field is always present (null
    in JSON) so downstream consumers can rely on the key existing.

    `invoked_at` is dependency-injected for deterministic tests; when
    None the current UTC time is captured.
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(_VALID_MODES)}, got {mode!r}")
    if target_market not in _VALID_MARKETS:
        raise ValueError(
            f"target_market must be one of {sorted(_VALID_MARKETS)}, got {target_market!r}"
        )
    if method not in _VALID_METHODS:
        raise ValueError(
            f"method must be one of {sorted(_VALID_METHODS)}, got {method!r}"
        )

    ppaf_stage = "planning" if mode == "pre_rewrite" else "late_feedback"

    if invoked_at is None:
        invoked_at = datetime.now(timezone.utc)
    timestamp = invoked_at.isoformat()

    return {
        "sub_skill": "fit-diagnosis-engine",
        "mode": mode,
        "target_market": target_market,
        "ppaf_stage": ppaf_stage,
        "invoked_at": timestamp,
        "inputs_signature": {
            "jd_analysis_id": _stable_hash(jd_analysis),
            "competency_profile_id": _stable_hash(competency_profile),
            "current_resume_hash": current_resume_hash,
        },
        "multi_jd": bool(multi_jd),
        "confidence": confidence,
        "competitiveness_rating": competitiveness_rating,
        "_method": method,
    }


__all__ = [
    "build_common_header",
    "compute_confidence",
    "Confidence",
]
