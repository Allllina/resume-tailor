"""harness.master_gen — Wave 4 C.1.2 per-lens master generation pipeline.

LLM-driven generation of a master.tex variant tailored for a specific
direction (lens). Mirrors the spirit of `harness.rewrite.engine` (which
rewrites bullets per JD) but operates without a specific JD: the lens
definition file (`assets/knowledge-base/references/role-lenses/<lens>.md`)
is the implicit demand signal.

Public API:
    - `generate_master_for_lens(...)` — async orchestrator (single LLM call).
    - `MasterGenOutput`               — pydantic model. Use
                                         `model_dump_jsonable()` so the
                                         private `_method` survives.
"""
from .engine import MasterGenOutput, generate_master_for_lens

__all__ = ["MasterGenOutput", "generate_master_for_lens"]
