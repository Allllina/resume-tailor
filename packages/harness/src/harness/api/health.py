"""GET /api/health — LLM reachability + harness version.

Gate 2 (v0.6.2). The frontend polls this to show the LLM status pill in
the Sidebar and to gate the composer send button (if status=down, block
submission with an inline error instead of waiting for a 503 from tailor).

Response shape matches contracts/schemas/llm-health.schema.json.
"""
import time

from fastapi import APIRouter

from harness.llm.health import get_monitor

router = APIRouter()

_HARNESS_VERSION = "0.6.2"
_SCHEMA_VERSION = "llm-health-v1"


@router.get("/api/health")
async def api_health():
    monitor = get_monitor()
    snap = monitor.snapshot()

    now = time.monotonic()

    def _elapsed(ts: float | None) -> float | None:
        if ts is None:
            return None
        return round(now - ts, 1)

    return {
        "harness_version": _HARNESS_VERSION,
        "schema_version": _SCHEMA_VERSION,
        "llm": {
            "status": snap.status,
            "provider": snap.provider_name,
            "consecutive_failures": snap.consecutive_failures,
            "circuit_open": snap.circuit_open,
            "seconds_since_last_success": _elapsed(snap.last_success_at),
            "seconds_since_last_failure": _elapsed(snap.last_failure_at),
        },
    }
