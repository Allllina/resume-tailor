"""LLM provider factory — selects via config.llm_provider.

Gate 2 (v0.6.2): adds `get_llm_provider()` singleton that reuses the same
provider (and its CircuitBreaker) across all requests in the process,
wiring the LLMHealthMonitor callbacks so health state is tracked globally.
`make_llm_provider()` is kept for tests / scripts that need ephemeral
providers.
"""
from loguru import logger

from .circuit_breaker import CircuitBreaker
from .health import get_monitor
from .protocol import LLMProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider


_provider: LLMProvider | None = None


def get_llm_provider(config=None) -> LLMProvider:
    """Return the module-level singleton LLM provider.

    Created on first call; subsequent calls return the same instance (and
    thus the same CircuitBreaker + health callbacks). This means breaker
    state accumulates across requests — intentional, it's the point.
    """
    global _provider
    if _provider is None:
        _provider = _build_provider(config)
    return _provider


def _reset_provider_for_tests() -> None:
    """Test helper — resets both the provider AND monitor singletons.

    Always resets both atomically: the provider holds callback references into
    the monitor, so resetting monitor after provider leaves the provider wired
    to the old (orphaned) monitor instance. Callers must NOT call
    _reset_monitor_for_tests() separately after this; they get the same effect
    for free.
    """
    global _provider
    _provider = None
    from harness.llm.health import _reset_monitor_for_tests
    _reset_monitor_for_tests()


def _build_provider(config=None) -> LLMProvider:
    """Build a provider with LLMHealthMonitor callbacks wired into its breaker."""
    if config is None:
        from harness.config import config as default_config
        config = default_config

    monitor = get_monitor()
    breaker = CircuitBreaker(
        on_success=monitor.record_success,
        on_failure=monitor.record_failure,
        on_circuit_open=monitor.record_circuit_open,
    )

    provider_name = config.llm_provider
    monitor._provider_name = provider_name  # update once we know the name

    if provider_name == "anthropic":
        if not config.anthropic_api_key or config.anthropic_api_key.startswith("sk-ant-..."):
            logger.warning(
                "HARNESS_ANTHROPIC_API_KEY is empty or placeholder — LLM calls will fail. "
                "Set it in packages/harness/.env (cp .env.example .env first)."
            )
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
            max_retries=config.anthropic_max_retries,
            timeout_seconds=config.anthropic_timeout_seconds,
            breaker=breaker,
        )
    if provider_name == "openai":
        if not config.openai_api_key or config.openai_api_key.startswith("sk-..."):
            logger.warning(
                "HARNESS_OPENAI_API_KEY is empty or placeholder — LLM calls will fail."
            )
        if config.openai_base_url and "localhost" in config.openai_base_url:
            logger.info(f"OpenAI provider routed to local proxy at {config.openai_base_url}")
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=config.openai_model,
            max_retries=config.openai_max_retries,
            timeout_seconds=config.openai_timeout_seconds,
            base_url=config.openai_base_url or None,
            breaker=breaker,
        )
    raise ValueError(f"Unknown llm_provider: {provider_name!r}. Use 'anthropic' or 'openai'.")


def make_llm_provider_for_thread(config=None) -> LLMProvider:
    """Build a fresh provider for use inside a per-request ``asyncio.run()`` call.

    The process-wide singleton returned by ``get_llm_provider()`` holds async
    HTTP clients that are bound to the event loop that was active when the
    provider was first constructed.  ``run_in_threadpool`` offloads execution
    to a worker thread, then ``asyncio.run()`` inside that thread creates and
    immediately closes a *new* event loop.  On the second request the singleton
    provider's clients are bound to the now-closed loop → ``RuntimeError:
    Event loop is closed`` (or silently corrupted I/O depending on the SDK).

    This function calls ``_build_provider()`` every time, so each
    ``asyncio.run()`` invocation gets fresh async HTTP clients that are bound
    to its own short-lived loop.  The CircuitBreaker callbacks are still wired
    to the global ``LLMHealthMonitor``, so per-request failures continue to
    update the health state that ``monitor.is_down()`` reads at request start.

    Do NOT use this outside of ``run_in_threadpool`` / ``asyncio.run()``
    contexts — creating a new provider per request has overhead.  For regular
    async request handlers use ``get_llm_provider()`` as usual.
    """
    return _build_provider(config)


def make_llm_provider(config=None) -> LLMProvider:
    """Construct the LLM provider per config.llm_provider.

    Default config = harness.config.config (lazy import to allow override
    in tests / scripts that build their own HarnessConfig). When the key
    for the chosen provider is unset / placeholder, log a single WARN so
    self-hosted users see a clear message before the first LLM call fails
    (rather than only seeing the SDK's auth-error stack trace).
    """
    if config is None:
        from harness.config import config as default_config
        config = default_config

    provider = config.llm_provider
    if provider == "anthropic":
        if not config.anthropic_api_key or config.anthropic_api_key.startswith("sk-ant-..."):
            logger.warning(
                "HARNESS_ANTHROPIC_API_KEY is empty or placeholder — LLM calls will fail. "
                "Set it in packages/harness/.env (cp .env.example .env first)."
            )
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
            max_retries=config.anthropic_max_retries,
            timeout_seconds=config.anthropic_timeout_seconds,
        )
    if provider == "openai":
        if not config.openai_api_key or config.openai_api_key.startswith("sk-..."):
            logger.warning(
                "HARNESS_OPENAI_API_KEY is empty or placeholder — LLM calls will fail. "
                "Set it in packages/harness/.env, OR switch to direct Anthropic by setting "
                "HARNESS_LLM_PROVIDER=anthropic + HARNESS_ANTHROPIC_API_KEY."
            )
        if config.openai_base_url and "localhost" in config.openai_base_url:
            logger.info(
                f"OpenAI provider routed to local proxy at {config.openai_base_url} — "
                "ensure the proxy is running before tailoring."
            )
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=config.openai_model,
            max_retries=config.openai_max_retries,
            timeout_seconds=config.openai_timeout_seconds,
            base_url=config.openai_base_url or None,
        )
    raise ValueError(f"Unknown llm_provider: {provider!r}. Use 'anthropic' or 'openai'.")
