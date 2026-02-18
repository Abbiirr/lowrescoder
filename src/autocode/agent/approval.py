"""Approval manager for tool execution safety."""

from __future__ import annotations

from enum import Enum

from autocode.agent.tools import ToolDefinition
from autocode.config import ShellConfig


class ApprovalMode(Enum):
    READ_ONLY = "read-only"
    SUGGEST = "suggest"
    AUTO = "auto"


# Commands that are always blocked regardless of mode
BLOCKED_PATTERNS = ["rm -rf /", "rm -rf ~", "mkfs", "dd if=", ":(){", "fork bomb"]


class ApprovalManager:
    """Determines whether tool calls need approval based on mode and tool type."""

    def __init__(self, mode: ApprovalMode, shell_config: ShellConfig | None = None) -> None:
        self.mode = mode
        self.shell_config = shell_config or ShellConfig()

    def needs_approval(self, tool: ToolDefinition) -> bool:
        """Check if a tool call requires user approval."""
        if self.mode == ApprovalMode.READ_ONLY:
            return tool.requires_approval  # block all writes
        if self.mode == ApprovalMode.SUGGEST:
            return tool.requires_approval
        if self.mode == ApprovalMode.AUTO:
            # Auto mode: file writes auto-approved, shell always needs approval
            return tool.name == "run_command"
        return True

    def is_blocked(self, tool_name: str, arguments: dict[str, object]) -> tuple[bool, str]:
        """Check if a tool call is always blocked (dangerous commands).

        Note: shell-disabled is NOT a hard block — it routes through approval
        so the user can enable shell on demand.
        """
        if tool_name == "run_command":
            command = str(arguments.get("command", ""))

            # Check blocked patterns (always, regardless of shell state)
            for pattern in BLOCKED_PATTERNS:
                if pattern in command:
                    return True, f"Blocked: dangerous command pattern '{pattern}'"

            # Check shell config blocked commands
            for blocked in self.shell_config.blocked_commands:
                if blocked in command:
                    return True, f"Blocked: command matches blocked pattern '{blocked}'"

        return False, ""

    def is_shell_disabled(self) -> bool:
        """Check if shell execution is currently disabled."""
        return not self.shell_config.enabled

    def enable_shell(self) -> None:
        """Enable shell execution at runtime."""
        self.shell_config.enabled = True

    def is_write_blocked(self, tool_name: str) -> bool:
        """Check if write operations are blocked in read-only mode."""
        if self.mode == ApprovalMode.READ_ONLY:
            return tool_name in ("write_file", "run_command")
        return False
