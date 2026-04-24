"""Tests for backend-host RPC dispatch ownership."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from autocode.backend.dispatcher import dispatch_request


@pytest.mark.asyncio
async def test_dispatch_request_routes_chat_to_background_task() -> None:
    host = MagicMock()
    host.handle_chat = AsyncMock(return_value=None)
    scheduled_task = MagicMock()

    def fake_create_task(coroutine):
        coroutine.close()
        return scheduled_task

    host._loop_create_task.side_effect = fake_create_task

    await dispatch_request(host, "chat", {"message": "hello", "session_id": "s1"}, 7)

    host.handle_chat.assert_called_once_with("hello", "s1", 7)
    host._loop_create_task.assert_called_once()
    assert host._agent_task is scheduled_task


@pytest.mark.asyncio
async def test_dispatch_request_routes_known_method() -> None:
    host = MagicMock()
    host.handle_session_list = AsyncMock(return_value=None)

    await dispatch_request(host, "session.list", {}, 8)

    host.handle_session_list.assert_awaited_once_with(8)


@pytest.mark.asyncio
async def test_dispatch_request_unknown_method_emits_structured_error() -> None:
    host = SimpleNamespace(emit_response=MagicMock())

    await dispatch_request(host, "missing.method", {}, 9)

    host.emit_response.assert_called_once_with(9, {"error": "Unknown method: missing.method"})
