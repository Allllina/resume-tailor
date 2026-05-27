"""DEPRECATED — backward-compat re-export. Use harness.llm.anthropic_provider."""
from harness.llm.anthropic_provider import AnthropicProvider as ClaudeClient

__all__ = ["ClaudeClient"]
