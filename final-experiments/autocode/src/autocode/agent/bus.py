"""AgentBus — typed messaging between agents.

Runtime equivalent of AGENTS_CONVERSATION.MD. Supports REQUEST, RESULT,
and ISSUE message types with per-task threading and persistence.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    """Agent message types."""

    REQUEST = "request"
    RESULT = "result"
    ISSUE = "issue"


class MessageStatus(StrEnum):
    """Message delivery status for persistent mailbox."""

    PENDING = "pending"
    DELIVERED = "delivered"
    CLAIMED = "claimed"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """A single message between agents."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: str = ""
    to_agent: str | None = None  # None = broadcast
    message_type: MessageType = MessageType.REQUEST
    payload: dict[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


class AgentBus:
    """Runtime message bus for agent-to-agent communication.

    Supports send, subscribe, get_pending, and get_thread operations.
    Hard caps: max 3 messages per task edge, max 2 delegated agents.
    """

    MAX_MESSAGES_PER_TASK: int = 3
    MAX_DELEGATED_AGENTS: int = 2

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._subscribers: dict[str, list[Callable[[AgentMessage], None]]] = {}

    def send(self, message: AgentMessage) -> str:
        """Send a message. Returns message ID.

        Enforces per-task message cap.
        """
        if message.task_id:
            task_msgs = [
                m for m in self._messages
                if m.task_id == message.task_id
                and m.from_agent == message.from_agent
                and m.to_agent == message.to_agent
            ]
            if len(task_msgs) >= self.MAX_MESSAGES_PER_TASK:
                raise ValueError(
                    f"Message cap reached: {self.MAX_MESSAGES_PER_TASK} "
                    f"messages per task edge "
                    f"({message.from_agent} → {message.to_agent})"
                )

        self._messages.append(message)

        # Notify subscribers
        target = message.to_agent
        if target and target in self._subscribers:
            for callback in self._subscribers[target]:
                callback(message)
        # Broadcast messages go to all subscribers
        if target is None:
            for callbacks in self._subscribers.values():
                for callback in callbacks:
                    callback(message)

        return message.id

    def subscribe(
        self,
        agent_id: str,
        callback: Callable[[AgentMessage], None],
    ) -> None:
        """Subscribe an agent to receive messages."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def get_pending(self, agent_id: str) -> list[AgentMessage]:
        """Get unprocessed messages for an agent."""
        return [
            m for m in self._messages
            if m.to_agent == agent_id or m.to_agent is None
        ]

    def get_thread(self, task_id: str) -> list[AgentMessage]:
        """Get all messages for a task, ordered by timestamp."""
        return sorted(
            [m for m in self._messages if m.task_id == task_id],
            key=lambda m: m.timestamp,
        )

    def get_delegated_agents(self, task_id: str) -> set[str]:
        """Get unique agents that have been delegated to for a task."""
        return {
            m.to_agent
            for m in self._messages
            if m.task_id == task_id
            and m.message_type == MessageType.REQUEST
            and m.to_agent is not None
        }

    @property
    def message_count(self) -> int:
        """Total messages in the bus."""
        return len(self._messages)

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
