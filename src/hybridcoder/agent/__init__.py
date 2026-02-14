"""Agent system: tool registry, approval, and agent loop."""

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.context import ContextEngine
from hybridcoder.agent.event_recorder import EventRecorder
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import ToolDefinition, ToolRegistry

__all__ = [
    "AgentLoop",
    "ApprovalManager",
    "ApprovalMode",
    "ContextEngine",
    "EventRecorder",
    "ToolDefinition",
    "ToolRegistry",
]
