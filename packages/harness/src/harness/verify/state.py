"""LangGraph state shape for Pass 3 verifier (Wave 4 D.4a)."""
from __future__ import annotations

from typing import TypedDict


class VerifyState(TypedDict, total=False):
    """LangGraph state for a single-bullet Pass 3 verification cycle.

    Inputs (set by orchestrator before invoke):
      - bullet:        {id, text, claimed_facts, experience_ref}
      - source_text:   concatenated raw markdown for grounding lookups
      - rubric:        parsed quality-pass rules (D.4a: empty dict OK)

    Per-node outputs accumulate as the graph runs. Must remain
    JSON-serializable so LangGraph can checkpoint it; an `LLMProvider`
    instance is NOT in state — nodes capture it via closure (Option A
    from the D.4a spec).
    """

    # Inputs
    bullet: dict
    source_text: str
    rubric: dict

    # Per-node outputs
    extracted_claims: list[str]
    extraction_degraded: bool
    grounded_results: list[dict]
    layer_2_failures: list[str]
    classified_unsourced: list[dict]
    classify_degraded: bool
    final_verdict: dict


__all__ = ["VerifyState"]
