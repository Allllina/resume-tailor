"""harness.competency — Wave 4 Step B role-competency-extractor module.

Lightweight LLM-driven port of the strategy module
`packages/strategy-modules/role-competency-extractor`. Produces the 9-section
structured competency model defined in that module's `output-schema.md` so
Tier 1 PLANNING has a richer JD understanding to feed into Skills row
reordering (Section D) and the Summary prompt (Section H).

This is intentionally NOT the full 10-step workflow port — only the LLM
extraction of the 9 sections + a graceful fallback model. The richer port
(market-contexts loading, scenario detection, blacklists, etc.) can come
in a future wave.

The returned dict carries a `_method` marker so callers can decide whether
to record a degradation event:
  - "llm": full LLM-driven extraction with all required sections present.
  - "llm_partial": LLM ran but JSON was missing required sections; gaps
    filled with fallback values + degradation event emitted.
  - "fallback_no_llm": LLM unavailable / raised / returned malformed JSON;
    whole model is the placeholder fallback.
"""
from .extractor import (
    SECTION_KEYS,
    extract_competencies,
    fallback_model,
    section_d_keywords,
    section_h_strategy_hints,
)

__all__ = [
    "SECTION_KEYS",
    "extract_competencies",
    "fallback_model",
    "section_d_keywords",
    "section_h_strategy_hints",
]
