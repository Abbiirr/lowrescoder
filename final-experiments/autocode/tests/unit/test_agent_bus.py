"""Tests for AgentBus — typed messaging between agents."""

from __future__ import annotations

import pytest

from autocode.agent.bus import AgentBus, AgentMessage, MessageType


def test_send_and_receive() -> None:
    """Messages can be sent and retrieved."""
    bus = AgentBus()
    msg = AgentMessage(
        from_agent="scout",
        to_agent="architect",
        message_type=MessageType.REQUEST,
        payload={"task": "find files"},
        task_id="task-1",
    )
    msg_id = bus.send(msg)
    assert msg_id
    assert bus.message_count == 1


def test_get_pending() -> None:
    """Get pending messages for a specific agent."""
    bus = AgentBus()
    bus.send(AgentMessage(from_agent="scout", to_agent="architect", task_id="t1"))
    bus.send(AgentMessage(from_agent="scout", to_agent="engineer", task_id="t2"))

    pending = bus.get_pending("architect")
    assert len(pending) == 1
    assert pending[0].task_id == "t1"


def test_get_thread() -> None:
    """Get all messages for a task in order."""
    bus = AgentBus()
    bus.send(AgentMessage(from_agent="scout", to_agent="architect", task_id="t1", message_type=MessageType.REQUEST))
    bus.send(AgentMessage(from_agent="architect", to_agent="scout", task_id="t1", message_type=MessageType.RESULT))

    thread = bus.get_thread("t1")
    assert len(thread) == 2
    assert thread[0].message_type == MessageType.REQUEST
    assert thread[1].message_type == MessageType.RESULT


def test_broadcast() -> None:
    """Broadcast messages (to_agent=None) reach all subscribers."""
    bus = AgentBus()
    received: list[str] = []
    bus.subscribe("agent-a", lambda m: received.append("a"))
    bus.subscribe("agent-b", lambda m: received.append("b"))

    bus.send(AgentMessage(from_agent="coordinator", to_agent=None, message_type=MessageType.REQUEST))
    assert "a" in received
    assert "b" in received


def test_message_cap_per_task() -> None:
    """Enforce max messages per task edge."""
    bus = AgentBus()
    bus.MAX_MESSAGES_PER_TASK = 2

    bus.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))
    bus.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))

    with pytest.raises(ValueError, match="Message cap reached"):
        bus.send(AgentMessage(from_agent="a", to_agent="b", task_id="t1"))


def test_delegated_agents() -> None:
    """Track unique delegated agents per task."""
    bus = AgentBus()
    bus.send(AgentMessage(from_agent="coord", to_agent="scout", task_id="t1", message_type=MessageType.REQUEST))
    bus.send(AgentMessage(from_agent="coord", to_agent="engineer", task_id="t1", message_type=MessageType.REQUEST))
    bus.send(AgentMessage(from_agent="scout", to_agent="coord", task_id="t1", message_type=MessageType.RESULT))

    delegated = bus.get_delegated_agents("t1")
    assert delegated == {"scout", "engineer"}


def test_subscribe_callback() -> None:
    """Subscribers get notified on message send."""
    bus = AgentBus()
    received: list[AgentMessage] = []
    bus.subscribe("architect", lambda m: received.append(m))

    bus.send(AgentMessage(from_agent="scout", to_agent="architect", payload={"files": ["a.py"]}))
    assert len(received) == 1
    assert received[0].payload["files"] == ["a.py"]


def test_clear() -> None:
    """Clear removes all messages."""
    bus = AgentBus()
    bus.send(AgentMessage(from_agent="a", to_agent="b"))
    bus.clear()
    assert bus.message_count == 0
