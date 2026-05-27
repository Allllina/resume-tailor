"""Anthropic Claude provider implementation.

Per HARNESS_DESIGN.md §3.2 (Eval stage) and §11 (graceful degradation).

Retries on:
- APITimeoutError
- APIConnectionError
- RateLimitError

Does NOT retry on:
- ValueError / TypeError / other client-side bugs
- 4xx errors signaling permanent issues (the SDK raises subclasses we don't
  retry on by default; extend `_RETRY_EXCEPTIONS` if you have specific
  ones to add)
"""
from anthropic import (
    AsyncAnthropic,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
)
from loguru import logger
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .circuit_breaker import CircuitBreaker
from .protocol import CircuitOpen  # noqa: F401  (re-exported for callers)


_RETRY_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError)


class AnthropicProvider:
    def __init__(
        self,
        anthropic_client: AsyncAnthropic | None = None,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 3,
        timeout_seconds: int = 60,
        breaker: CircuitBreaker | None = None,
    ):
        if anthropic_client is None:
            anthropic_client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self._client = anthropic_client
        self._model = model
        self._max_retries = max_retries
        self.breaker = breaker if breaker is not None else CircuitBreaker()
        self.last_usage: dict | None = None

    async def call(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        # Pre-flight breaker check — fail fast if recently overloaded
        self.breaker.check_or_raise()

        retry_policy = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
            reraise=True,
        )

        try:
            async for attempt in retry_policy:
                with attempt:
                    response = await self._client.messages.create(
                        model=self._model,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    self.breaker.record_success()
                    text = "".join(b.text for b in response.content if hasattr(b, "text"))
                    # Capture usage
                    if hasattr(response, "usage") and response.usage is not None:
                        in_t = getattr(response.usage, "input_tokens", 0) or 0
                        out_t = getattr(response.usage, "output_tokens", 0) or 0
                        self.last_usage = {
                            "input_tokens": in_t,
                            "output_tokens": out_t,
                            "total_tokens": in_t + out_t,
                        }
                    logger.debug(f"Anthropic call ok: {len(text)} chars")
                    return text
        except _RETRY_EXCEPTIONS as e:
            self.last_usage = None
            self.breaker.record_failure()
            logger.warning(f"Anthropic call failed after {self._max_retries} retries: {e}")
            raise

        return ""  # unreachable; satisfies type checker
