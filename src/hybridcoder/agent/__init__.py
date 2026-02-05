"""Agent system: tool registry, approval, and agent loop."""

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.tools import ToolDefinition, ToolRegistry

__all__ = [
    "AgentLoop",
    "ApprovalManager",
    "ApprovalMode",
    "ToolDefinition",
    "ToolRegistry",
]
