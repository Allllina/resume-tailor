"""Shared helpers for PPAF stage modules."""


async def _emit_call_metrics(state, tools, stage: str, metric_name: str = "claude_api_call"):
    """Read tools.llm.last_usage and emit metrics events. No-op if not a real dict."""
    usage = getattr(tools.llm, "last_usage", None)
    # Guard against AsyncMock / sentinel values from test doubles — only emit
    # when last_usage is a real dict-like with the expected keys.
    if not isinstance(usage, dict):
        return
    state.metrics["total_tokens"] = state.metrics.get("total_tokens", 0) + usage.get("total_tokens", 0)
    state.metrics["total_claude_calls"] = state.metrics.get("total_claude_calls", 0) + 1
    state.add_event(stage, metric_name, {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    })
