"""RateLimiter — per-channel async semaphore enforcing min-interval between submits.

Per Wave 3 plan §Phase 0 Task 3. Used by batch_runner to space out submits.
Default intervals are configured by HarnessConfig; can be overridden per
submit call (e.g., when a previous submit failed and we want immediate retry).
"""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(
        self,
        intervals: dict[str, int] | None = None,
        default_interval: int = 60,
    ):
        """intervals: {channel: seconds}. default_interval: fallback for unknown channels."""
        self._intervals = intervals or {}
        self._default_interval = default_interval
        self._last_submit_at: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _interval_for(self, channel: str) -> int:
        return self._intervals.get(channel, self._default_interval)

    def _lock_for(self, channel: str) -> asyncio.Lock:
        if channel not in self._locks:
            self._locks[channel] = asyncio.Lock()
        return self._locks[channel]

    async def wait(self, channel: str) -> None:
        """Block until enough time has elapsed since last submit on this channel."""
        async with self._lock_for(channel):
            interval = self._interval_for(channel)
            last = self._last_submit_at.get(channel, 0.0)
            elapsed = time.monotonic() - last
            wait_for = interval - elapsed
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_submit_at[channel] = time.monotonic()

    def force_reset(self, channel: str) -> None:
        """Clear last-submit timestamp for a channel (for tests / manual override)."""
        self._last_submit_at.pop(channel, None)
