"""harness.fit_diagnosis — Wave 5 F1 backend for the fit-diagnosis-engine sub-skill.

Two-mode (pre_rewrite + post_rewrite) consolidation of harness/forecast/
(Step 4 match matrix) and harness/review/ (Step 8 dual perspective)
into a single sub-skill module per the canonical spec at
`packages/strategy-modules/fit-diagnosis-engine/`.

F1 ships pre_rewrite ONLY. F3 will add post_rewrite. Both stages share
the common header + confidence helpers in `_shared.py`. Old
harness/forecast/ + harness/review/ remain intact this phase; F2 wires
the new path into PLANNING and late_feedback, then F2 deletes the old
modules.

The returned dict carries a `_method` marker so callers can decide
whether to record a degradation event:
  - "llm": full LLM-driven extraction with all required keys present.
  - "llm_partial": LLM ran but JSON was missing required keys / had
    invalid enum values; gaps filled with fallback values.
  - "fallback_no_llm": LLM unavailable / raised / returned malformed
    JSON; whole structure is the placeholder fallback.
"""
from .engine import build_diagnosis, fallback_diagnosis

__all__ = ["build_diagnosis", "fallback_diagnosis"]
