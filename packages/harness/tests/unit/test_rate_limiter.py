"""Test RateLimiter — per-channel async interval enforcement."""
import asyncio
import pytest
from harness.submit.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_first_call_no_wait():
    """First call on a fresh channel returns immediately."""
    limiter = RateLimiter(intervals={"linkedin": 1})
    started = asyncio.get_event_loop().time()
    await limiter.wait("linkedin")
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_subsequent_call_waits():
    limiter = RateLimiter(intervals={"linkedin": 1})  # 1s
    await limiter.wait("linkedin")
    started = asyncio.get_event_loop().time()
    await limiter.wait("linkedin")
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed >= 0.9  # allow small clock noise
    assert elapsed < 1.5


@pytest.mark.asyncio
async def test_different_channels_dont_block_each_other():
    limiter = RateLimiter(intervals={"linkedin": 5, "boss": 5})
    await limiter.wait("linkedin")
    started = asyncio.get_event_loop().time()
    await limiter.wait("boss")
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_force_reset_clears_last_timestamp():
    limiter = RateLimiter(intervals={"linkedin": 5})
    await limiter.wait("linkedin")
    limiter.force_reset("linkedin")
    started = asyncio.get_event_loop().time()
    await limiter.wait("linkedin")
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_unknown_channel_uses_default_interval():
    limiter = RateLimiter(intervals={}, default_interval=1)
    await limiter.wait("xyz")
    started = asyncio.get_event_loop().time()
    await limiter.wait("xyz")
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed >= 0.9
