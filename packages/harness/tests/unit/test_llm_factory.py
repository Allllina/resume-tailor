"""Test make_llm_provider factory."""
import pytest
from unittest.mock import MagicMock
from harness.llm.factory import make_llm_provider
from harness.llm.anthropic_provider import AnthropicProvider
from harness.llm.openai_provider import OpenAIProvider


def _config(provider: str, **kw):
    cfg = MagicMock()
    cfg.llm_provider = provider
    cfg.anthropic_api_key = "sk-ant-test"
    cfg.anthropic_model = "claude-sonnet-4-6"
    cfg.anthropic_max_retries = 3
    cfg.anthropic_timeout_seconds = 60
    cfg.openai_api_key = "sk-oai-test"
    cfg.openai_model = "gpt-4o"
    cfg.openai_max_retries = 3
    cfg.openai_timeout_seconds = 60
    cfg.openai_base_url = ""
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def test_factory_returns_anthropic_by_default():
    cfg = _config("anthropic")
    p = make_llm_provider(cfg)
    assert isinstance(p, AnthropicProvider)


def test_factory_returns_openai():
    cfg = _config("openai")
    p = make_llm_provider(cfg)
    assert isinstance(p, OpenAIProvider)


def test_factory_unknown_raises():
    cfg = _config("groq")
    with pytest.raises(ValueError, match="Unknown llm_provider"):
        make_llm_provider(cfg)


def test_factory_uses_default_config_when_none():
    """Calling without config arg falls back to harness.config.config."""
    # Just ensure it doesn't crash; will use real config (env-driven).
    # Default llm_provider="anthropic" + empty api_key still constructs fine
    # (HarnessConfig has empty default — Anthropic SDK won't fail at init).
    p = make_llm_provider()
    assert isinstance(p, (AnthropicProvider, OpenAIProvider))


def test_factory_passes_openai_base_url():
    cfg = _config("openai")
    cfg.openai_base_url = "http://localhost:3456/v1"
    p = make_llm_provider(cfg)
    assert isinstance(p, OpenAIProvider)
    # base_url is stored inside the AsyncOpenAI client; verify provider was constructed
    # without error (full base_url propagation tested in test_openai_provider)
