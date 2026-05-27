"""PERCEPTION stage."""
from ..state import RunState


async def run_perception(state: RunState, jd_text: str, target_market: str) -> None:
    """Mutates state. PERCEPTION stage."""
    state.add_event("perception", "jd_received", {"length": len(jd_text), "target_market": target_market})
