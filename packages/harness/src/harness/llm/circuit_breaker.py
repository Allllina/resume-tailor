"""Circuit breaker for LLM provider calls.

Per HARNESS_COMPLIANCE_AUDIT.md Gap 6.

After N consecutive failures, short-circuits subsequent calls for
cooldown_seconds; caller should catch CircuitOpen and degrade to
fallback per HARNESS_DESIGN.md §11.

Gate 2 (v0.6.2): accepts optional `on_success`, `on_failure`,
`on_circuit_open` callbacks so the LLMHealthMonitor can track state
without the breaker depending on the monitor directly.
"""
import time
from dataclasses import dataclass, field
from typing import Callable

from .protocol import CircuitOpen


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    cooldown_seconds: int = 300  # 5 min
    failure_count: int = 0
    open_until: float = 0.0
    on_success: Callable[[], None] | None = field(default=None, repr=False)
    on_failure: Callable[[], None] | None = field(default=None, repr=False)
    on_circuit_open: Callable[[], None] | None = field(default=None, repr=False)

    def record_success(self) -> None:
        self.failure_count = 0
        self.open_until = 0.0
        if self.on_success:
            self.on_success()

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.on_failure:
            self.on_failure()
        if self.failure_count >= self.failure_threshold:
            self.open_until = time.monotonic() + self.cooldown_seconds
            if self.on_circuit_open:
                self.on_circuit_open()

    def check_or_raise(self) -> None:
        remaining = self.open_until - time.monotonic()
        if remaining > 0:
            raise CircuitOpen(f"Circuit open for another {remaining:.0f}s")
