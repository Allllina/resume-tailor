"""Pass 3 truthfulness verifier (Wave 4 D.4).

Public surface (D.4a):
  - `verify_bullets(bullets, source_files, rubric_path, llm)` — orchestrator
  - `Pass3VerifyError` — raised on hard errors (graph build failure)
  - `build_graph(llm)` — compile the LangGraph state graph (used by
    orchestrator and by tests)
  - `VerifyState` — TypedDict schema for the LangGraph state

D.4b will replace the deterministic `classify_unsourced` heuristics with an
LLM-driven action chooser. D.4c will integrate the verifier into the REPL
loop and add the `pass3_trace` field to harness output. None of those touch
the public surface listed here.
"""
from .graph import VerifyState, build_graph
from .pass3 import Pass3VerifyError, verify_bullets


__all__ = [
    "Pass3VerifyError",
    "VerifyState",
    "build_graph",
    "verify_bullets",
]
