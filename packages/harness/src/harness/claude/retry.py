"""DEPRECATED — backward-compat re-export. Use harness.llm.circuit_breaker."""
from harness.llm.circuit_breaker import CircuitBreaker
from harness.llm.protocol import CircuitOpen

__all__ = ["CircuitBreaker", "CircuitOpen"]
