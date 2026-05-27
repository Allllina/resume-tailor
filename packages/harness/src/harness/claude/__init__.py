"""harness.claude — DEPRECATED alias for harness.llm.

Kept for Wave 1 backward compatibility. New code should import from
harness.llm directly.
"""
from harness.llm.anthropic_provider import AnthropicProvider as ClaudeClient
from harness.llm.circuit_breaker import CircuitBreaker
from harness.llm.protocol import CircuitOpen

__all__ = ["ClaudeClient", "CircuitBreaker", "CircuitOpen"]
