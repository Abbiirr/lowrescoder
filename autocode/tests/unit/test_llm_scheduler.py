"""Tests for LLMScheduler — Sprint 4B."""

from __future__ import annotations

import asyncio

import pytest

from autocode.agent.subagent import LLMScheduler


@pytest.fixture
def scheduler():
    s = LLMScheduler()
    s.start()
    yield s
    # Cleanup
    asyncio.get_event_loop().run_until_complete(s.shutdown())


@pytest.mark.asyncio
async def test_scheduler_foreground_priority():
    """Foreground requests (priority=0) run before background (priority=1)."""
    scheduler = LLMScheduler()
    order: list[str] = []

    # Don't start the worker yet — queue items first
    async def bg():
        await asyncio.sleep(0)
        order.append("bg")
        return "bg"

    async def fg():
        await asyncio.sleep(0)
        order.append("fg")
        return "fg"

    # Put background first, then foreground
    loop = asyncio.get_running_loop()
    bg_future: asyncio.Future[str] = loop.create_future()
    fg_future: asyncio.Future[str] = loop.create_future()

    scheduler._counter += 1
    await scheduler._queue.put((1, scheduler._counter, bg(), bg_future))
    scheduler._counter += 1
    await scheduler._queue.put((0, scheduler._counter, fg(), fg_future))

    # Start worker — should process fg first (priority 0)
    scheduler.start()
    await asyncio.sleep(0.2)
    await scheduler.shutdown()

    assert order == ["fg", "bg"]


@pytest.mark.asyncio
async def test_scheduler_fifo_within_tier():
    """Same-priority items processed in FIFO order (counter-based)."""
    scheduler = LLMScheduler()
    order: list[int] = []

    async def make_coro(n: int):
        order.append(n)
        return n

    # Queue multiple items at same priority
    loop = asyncio.get_running_loop()
    for i in range(3):
        future: asyncio.Future[int] = loop.create_future()
        scheduler._counter += 1
        await scheduler._queue.put((0, scheduler._counter, make_coro(i), future))

    scheduler.start()
    await asyncio.sleep(0.2)
    await scheduler.shutdown()

    assert order == [0, 1, 2]


@pytest.mark.asyncio
async def test_scheduler_queue_depth():
    """Queue depth reflects pending items."""
    scheduler = LLMScheduler()
    assert scheduler.queue_depth == 0

    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    async def dummy():
        return "ok"

    coro = dummy()
    scheduler._counter += 1
    await scheduler._queue.put((0, scheduler._counter, coro, future))
    assert scheduler.queue_depth == 1

    # Drain the queued coroutine to avoid unawaited warning
    _, _, queued_coro, queued_future = await scheduler._queue.get()
    queued_future.cancel()
    await asyncio.sleep(0)  # let cancel propagate
    coro.close()  # explicitly close the coroutine

    await scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_submit_returns_result():
    """submit() returns the coroutine result."""
    scheduler = LLMScheduler()
    scheduler.start()

    async def compute():
        return 42

    result = await scheduler.submit(compute(), foreground=True)
    assert result == 42

    await scheduler.shutdown()
