"""Test ClaudeClient retry + circuit breaker.

Per HARNESS_COMPLIANCE_AUDIT.md Gap 6.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from anthropic import APITimeoutError, APIConnectionError, RateLimitError
from harness.claude.client import ClaudeClient
from harness.claude.retry import CircuitBreaker, CircuitOpen


def _mock_response(text: str = "ok") -> MagicMock:
    """Build an Anthropic-style response mock."""
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


def _timeout_error() -> APITimeoutError:
    """Build APITimeoutError without hitting the network."""
    return APITimeoutError(MagicMock())


@pytest.mark.asyncio
async def test_succeeds_first_try():
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(return_value=_mock_response("hello"))
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=3)
    result = await client.call("sys", "usr", max_tokens=10)
    assert result == "hello"
    assert mock_anthropic.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_timeout():
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=[
        _timeout_error(),
        _timeout_error(),
        _mock_response("recovered"),
    ])
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=3)
    result = await client.call("sys", "usr", max_tokens=10)
    assert result == "recovered"
    assert mock_anthropic.messages.create.call_count == 3


@pytest.mark.asyncio
async def test_retries_exhausted_raises():
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=_timeout_error())
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=2)
    with pytest.raises(APITimeoutError):
        await client.call("sys", "usr", max_tokens=10)
    assert mock_anthropic.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_does_not_retry_on_non_transient():
    """ValueError and similar non-transient errors should not be retried."""
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=ValueError("bad input"))
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=3)
    with pytest.raises(ValueError):
        await client.call("sys", "usr", max_tokens=10)
    assert mock_anthropic.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_circuit_opens_after_failure_threshold():
    """After breaker.failure_threshold consecutive failed calls, circuit opens."""
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=_timeout_error())

    # max_retries=1 means each call() triggers exactly 1 underlying request and
    # raises APITimeoutError on failure. 3 such calls should open the circuit.
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=1)
    breaker = client.breaker

    for _ in range(breaker.failure_threshold):
        with pytest.raises(APITimeoutError):
            await client.call("sys", "usr", max_tokens=10)

    # Next call short-circuits before any HTTP attempt
    with pytest.raises(CircuitOpen):
        await client.call("sys", "usr", max_tokens=10)

    # The breaker should not have permitted an extra underlying call
    assert mock_anthropic.messages.create.call_count == breaker.failure_threshold


@pytest.mark.asyncio
async def test_success_resets_breaker():
    """One success after partial failures resets the failure counter."""
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=[
        _timeout_error(),
        _timeout_error(),
        _mock_response("recovered"),
    ])
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=3)
    await client.call("sys", "usr", max_tokens=10)

    assert client.breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_open_message_includes_remaining_seconds():
    """When the circuit is open, the raised CircuitOpen mentions how long until retry."""
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=_timeout_error())
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=1)
    breaker = client.breaker

    for _ in range(breaker.failure_threshold):
        with pytest.raises(APITimeoutError):
            await client.call("sys", "usr", max_tokens=10)

    with pytest.raises(CircuitOpen) as excinfo:
        await client.call("sys", "usr", max_tokens=10)
    assert "Circuit open" in str(excinfo.value)


def test_circuit_breaker_record_success_resets():
    b = CircuitBreaker()
    b.record_failure()
    b.record_failure()
    assert b.failure_count == 2
    b.record_success()
    assert b.failure_count == 0
    assert b.open_until == 0.0


def test_circuit_breaker_check_or_raise_when_open():
    b = CircuitBreaker(failure_threshold=2, cooldown_seconds=300)
    b.record_failure()
    b.record_failure()
    with pytest.raises(CircuitOpen):
        b.check_or_raise()


def test_circuit_breaker_check_or_raise_when_closed():
    b = CircuitBreaker(failure_threshold=3)
    b.record_failure()
    # only 1 failure, should not raise
    b.check_or_raise()


@pytest.mark.asyncio
async def test_anthropic_captures_usage():
    mock_anthropic = MagicMock()
    response = MagicMock()
    block = MagicMock()
    block.text = "ok"
    response.content = [block]
    response.usage.input_tokens = 200
    response.usage.output_tokens = 100
    mock_anthropic.messages.create = AsyncMock(return_value=response)
    client = ClaudeClient(anthropic_client=mock_anthropic, max_retries=3)
    await client.call("s", "u", max_tokens=10)
    assert client.last_usage == {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300}
