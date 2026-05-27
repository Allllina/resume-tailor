"""Pass 3 LangGraph verifier — graph builder (Wave 4 D.4a).

Wires the 4 node factories from `nodes.py` into a compiled `StateGraph`.
The orchestrator in `pass3.verify_bullets` invokes the compiled graph once
per bullet.

Linear DAG (D.4a; D.4b/c may add conditional branching):

    START
      ↓
    extract_claims         ← LLM only when bullet has no pre-extracted facts
      ↓
    ground_claim           ← Layer 1 substring (deterministic) +
      ↓                      Layer 2 paraphrase (LLM, per unsourced claim)
    classify_unsourced     ← deterministic heuristics in D.4a
      ↓                      (D.4b will replace with LLM)
    aggregate_verdict
      ↓
    END
"""
from __future__ import annotations

from typing import Any

from harness.llm.protocol import LLMProvider

from .nodes import (
    _make_aggregate_verdict_node,
    _make_classify_unsourced_node,
    _make_extract_claims_node,
    _make_ground_claim_node,
)
from .state import VerifyState


def build_graph(llm: LLMProvider | None = None) -> Any:
    """Compile the Pass 3 LangGraph state graph with `llm` bound to nodes.

    `llm=None` is supported for tests and the deterministic fast path
    (claim extraction degrades to single-claim, Layer 2 grounding is
    skipped). Returns the compiled graph; reuse it across bullets.

    LangGraph is imported lazily so harness modules that don't need the
    verifier don't pay its import cost. (Optional dependency; installed
    via the `[verifier]` extra.)
    """
    from langgraph.graph import StateGraph, START, END

    builder = StateGraph(VerifyState)
    builder.add_node("extract_claims", _make_extract_claims_node(llm))
    builder.add_node("ground_claim", _make_ground_claim_node(llm))
    builder.add_node("classify_unsourced", _make_classify_unsourced_node(llm))
    builder.add_node("aggregate_verdict", _make_aggregate_verdict_node())

    builder.add_edge(START, "extract_claims")
    builder.add_edge("extract_claims", "ground_claim")
    builder.add_edge("ground_claim", "classify_unsourced")
    builder.add_edge("classify_unsourced", "aggregate_verdict")
    builder.add_edge("aggregate_verdict", END)
    return builder.compile()


__all__ = ["VerifyState", "build_graph"]
