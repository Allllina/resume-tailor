"""OpenAI provider implementation — same .call() signature as AnthropicProvider."""
from openai import (
    AsyncOpenAI,
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


_RETRY_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError)


class OpenAIProvider:
    def __init__(
        self,
        openai_client: AsyncOpenAI | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o",
        max_retries: int = 3,
        timeout_seconds: int = 60,
        base_url: str | None = None,
        breaker: CircuitBreaker | None = None,
    ):
        if openai_client is None:
            kwargs: dict = {"api_key": api_key, "timeout": timeout_seconds}
            if base_url:
                kwargs["base_url"] = base_url
            openai_client = AsyncOpenAI(**kwargs)
        self._client = openai_client
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
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    self.breaker.record_success()
                    choice = response.choices[0]
                    text = choice.message.content or ""
                    if hasattr(response, "usage") and response.usage is not None:
                        prompt_t = getattr(response.usage, "prompt_tokens", 0) or 0
                        completion_t = getattr(response.usage, "completion_tokens", 0) or 0
                        self.last_usage = {
                            "input_tokens": prompt_t,
                            "output_tokens": completion_t,
                            "total_tokens": prompt_t + completion_t,
                        }
                    logger.debug(f"OpenAI call ok: {len(text)} chars")
                    return text
        except _RETRY_EXCEPTIONS as e:
            self.last_usage = None
            self.breaker.record_failure()
            logger.warning(f"OpenAI call failed after {self._max_retries} retries: {e}")
            raise

        return ""  # unreachable
