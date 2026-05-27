"""LLMProvider Protocol — uniform interface across Anthropic / OpenAI / etc."""
from typing import Protocol, runtime_checkable


class CircuitOpen(Exception):
    """Raised when an LLM provider's circuit breaker is open."""


@runtime_checkable
class LLMProvider(Protocol):
    """Common interface for LLM providers.

    Implementations should expose a `last_usage` attribute (dict | None)
    populated after each successful .call(). Format:
      {"input_tokens": int, "output_tokens": int, "total_tokens": int}
    Set to None on failure or before first call.
    """

    async def call(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        """Send a single completion request, return response text.

        Raises provider-specific transient errors (caller may retry) or
        CircuitOpen when too many recent failures have tripped the breaker.
        """
        ...
