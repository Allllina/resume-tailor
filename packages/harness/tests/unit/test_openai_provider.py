"""Test OpenAIProvider (mocked openai SDK)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from openai import APITimeoutError
from harness.llm.openai_provider import OpenAIProvider
from harness.llm.protocol import CircuitOpen


def _mock_response(text: str = "ok") -> MagicMock:
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    response.choices = [choice]
    return response


def _timeout_error() -> APITimeoutError:
    return APITimeoutError(MagicMock())


@pytest.mark.asyncio
async def test_openai_succeeds_first_try():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(return_value=_mock_response("hello"))
    p = OpenAIProvider(openai_client=mock_oai, max_retries=3)
    result = await p.call("sys", "usr", max_tokens=10)
    assert result == "hello"


@pytest.mark.asyncio
async def test_openai_passes_system_and_user_messages():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(return_value=_mock_response("ok"))
    p = OpenAIProvider(openai_client=mock_oai, max_retries=3)
    await p.call("you are helpful", "what is 2+2", max_tokens=10)
    call_kwargs = mock_oai.chat.completions.create.call_args.kwargs
    msgs = call_kwargs["messages"]
    assert msgs[0] == {"role": "system", "content": "you are helpful"}
    assert msgs[1] == {"role": "user", "content": "what is 2+2"}


@pytest.mark.asyncio
async def test_openai_retries_on_timeout():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(side_effect=[
        _timeout_error(),
        _mock_response("recovered"),
    ])
    p = OpenAIProvider(openai_client=mock_oai, max_retries=3)
    result = await p.call("s", "u", max_tokens=10)
    assert result == "recovered"
    assert mock_oai.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_openai_circuit_breaks_after_threshold():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(side_effect=_timeout_error())
    p = OpenAIProvider(openai_client=mock_oai, max_retries=1)
    for _ in range(p.breaker.failure_threshold):
        with pytest.raises(APITimeoutError):
            await p.call("s", "u", max_tokens=10)
    with pytest.raises(CircuitOpen):
        await p.call("s", "u", max_tokens=10)


@pytest.mark.asyncio
async def test_openai_handles_none_content():
    """OpenAI may return content=None for tool calls. We coerce to ""."""
    mock_oai = MagicMock()
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = None
    response.choices = [choice]
    mock_oai.chat.completions.create = AsyncMock(return_value=response)
    p = OpenAIProvider(openai_client=mock_oai, max_retries=3)
    result = await p.call("s", "u", max_tokens=10)
    assert result == ""


@pytest.mark.asyncio
async def test_openai_base_url_passed_to_client():
    """When base_url is provided, it should reach AsyncOpenAI."""
    from unittest.mock import patch
    with patch("harness.llm.openai_provider.AsyncOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        OpenAIProvider(api_key="sk-x", base_url="http://localhost:3456/v1")
        mock_cls.assert_called_once()
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["base_url"] == "http://localhost:3456/v1"


@pytest.mark.asyncio
async def test_openai_no_base_url_omits_kwarg():
    """When base_url is None/empty, AsyncOpenAI should NOT receive a base_url kwarg."""
    from unittest.mock import patch
    with patch("harness.llm.openai_provider.AsyncOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        OpenAIProvider(api_key="sk-x", base_url=None)
        mock_cls.assert_called_once()
        kwargs = mock_cls.call_args.kwargs
        assert "base_url" not in kwargs


@pytest.mark.asyncio
async def test_openai_captures_usage():
    mock_oai = MagicMock()
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = "ok"
    response.choices = [choice]
    response.usage.prompt_tokens = 100
    response.usage.completion_tokens = 50
    mock_oai.chat.completions.create = AsyncMock(return_value=response)
    p = OpenAIProvider(openai_client=mock_oai, max_retries=3)
    await p.call("s", "u", max_tokens=10)
    assert p.last_usage == {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
