"""LLM health monitor — Gate 2 (v0.6.2).

Singleton that tracks LLM reachability across all requests in the process.
The circuit breaker calls back here on success/failure/circuit-open so the
`GET /api/health` endpoint can serve a lightweight snapshot without making
any network call.

Usage:
    from harness.llm.health import get_monitor
    monitor = get_monitor()
    monitor.record_success()
    snap = monitor.snapshot()  # {"status": "healthy", ...}
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal


LLMStatus = Literal["healthy", "degraded", "down"]


@dataclass
class LLMHealthSnapshot:
    status: LLMStatus
    consecutive_failures: int
    circuit_open: bool
    last_success_at: float | None  # monotonic seconds; None if never succeeded
    last_failure_at: float | None  # monotonic seconds; None if never failed
    provider_name: str


class LLMHealthMonitor:
    """Thread-safe (GIL) LLM reachability tracker.

    Status rules:
    - consecutive_failures == 0 → healthy
    - 1 ≤ consecutive_failures < circuit_open_threshold → degraded
    - circuit_open (and cooldown not yet elapsed) → down

    `circuit_cooldown_seconds` must match the CircuitBreaker's `cooldown_seconds`
    (default 300) so that after cooldown the precheck gate unblocks and lets
    the next request through — which will either succeed (clearing the monitor)
    or fail again (re-recording the circuit-open event).
    """

    def __init__(
        self,
        provider_name: str = "unknown",
        circuit_open_threshold: int = 3,
        circuit_cooldown_seconds: int = 300,
    ) -> None:
        self._provider_name = provider_name
        self._circuit_open_threshold = circuit_open_threshold
        self._circuit_cooldown_seconds = circuit_cooldown_seconds
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_opened_at: float | None = None
        self._last_success_at: float | None = None
        self._last_failure_at: float | None = None

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_opened_at = None
        self._last_success_at = time.monotonic()

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        self._last_failure_at = time.monotonic()

    def record_circuit_open(self) -> None:
        self._circuit_open = True
        self._circuit_opened_at = time.monotonic()
        self._last_failure_at = time.monotonic()

    def _resolve_circuit_open(self) -> bool:
        """Return whether the circuit is still open, auto-clearing after cooldown.

        Once `circuit_cooldown_seconds` have elapsed the CircuitBreaker will
        allow calls through again (its `check_or_raise` uses the same window).
        Clearing here lets the precheck gate unblock so those calls can actually
        reach the breaker and record success/failure.
        """
        if not self._circuit_open:
            return False
        if self._circuit_opened_at is not None:
            if time.monotonic() - self._circuit_opened_at >= self._circuit_cooldown_seconds:
                self._circuit_open = False
                self._circuit_opened_at = None
                return False
        return True

    def snapshot(self) -> LLMHealthSnapshot:
        circuit_open = self._resolve_circuit_open()
        if circuit_open:
            status: LLMStatus = "down"
        elif self._consecutive_failures >= self._circuit_open_threshold:
            status = "down"
        elif self._consecutive_failures > 0:
            status = "degraded"
        else:
            status = "healthy"

        return LLMHealthSnapshot(
            status=status,
            consecutive_failures=self._consecutive_failures,
            circuit_open=circuit_open,
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
            provider_name=self._provider_name,
        )

    def is_down(self) -> bool:
        snap = self.snapshot()
        return snap.status == "down"


_monitor: LLMHealthMonitor | None = None


def get_monitor() -> LLMHealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = LLMHealthMonitor()
    return _monitor


def _reset_monitor_for_tests() -> None:
    """Test helper — resets the singleton between test cases."""
    global _monitor
    _monitor = None
