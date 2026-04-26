"""Approval manager for tool execution safety."""

from __future__ import annotations

from enum import Enum
from typing import Any

from autocode.agent.tools import ToolDefinition
from autocode.config import ShellConfig


class ApprovalMode(Enum):
    READ_ONLY = "read-only"
    SUGGEST = "suggest"
    AUTO = "auto"
    AUTONOMOUS = "autonomous"


# Commands that are always blocked regardless of mode
BLOCKED_PATTERNS = ["rm -rf /", "rm -rf ~", "mkfs", "dd if=", ":(){", "fork bomb"]
WRITE_TOOL_NAMES = {"write_file", "edit_file"}
DANGEROUS_WRITE_PATH_PREFIXES = (
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/proc",
    "/root",
    "/sbin",
    "/sys",
    "/usr/bin",
    "/usr/sbin",
)
DANGEROUS_WRITE_PATH_FRAGMENTS = (
    "/.ssh/",
    "/.gnupg/",
)
DANGEROUS_WRITE_CONTENT_PATTERNS = (
    "rm -rf",
    "mkfs",
    "dd if=",
    ":(){",
    "fork bomb",
    "chmod -r 777 /",
    "chown -r",
)


def _path_is_dangerous(path: object) -> str | None:
    """Return the dangerous path marker when a write target is forbidden."""
    candidate = str(path or "").strip().replace("\\", "/")
    if not candidate:
        return None
    lowered = candidate.lower()
    for prefix in DANGEROUS_WRITE_PATH_PREFIXES:
        if lowered == prefix or lowered.startswith(f"{prefix}/"):
            return prefix
    if lowered.startswith("~/.ssh") or lowered.startswith("~/.gnupg"):
        return lowered.split("/", 2)[0] if "/" in lowered else lowered
    for fragment in DANGEROUS_WRITE_PATH_FRAGMENTS:
        if fragment in lowered:
            return fragment
    return None


def _content_is_dangerous(content: object) -> str | None:
    """Return the dangerous content marker when write content is forbidden."""
    candidate = str(content or "").lower()
    for pattern in DANGEROUS_WRITE_CONTENT_PATTERNS:
        if pattern in candidate:
            return pattern
    return None


def _iter_apply_patch_operations(arguments: dict[str, object]) -> list[dict[str, Any]]:
    operations = arguments.get("operations", [])
    if not isinstance(operations, list):
        return []
    return [op for op in operations if isinstance(op, dict)]


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
        if self.mode == ApprovalMode.AUTONOMOUS:
            # Non-interactive mode: never prompt; blocked tools must fail closed.
            return False
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

        if tool_name in WRITE_TOOL_NAMES:
            dangerous_path = _path_is_dangerous(arguments.get("path", ""))
            if dangerous_path is not None:
                return True, f"Blocked: dangerous write path '{dangerous_path}'"

            content_key = "content" if tool_name == "write_file" else "new_string"
            dangerous_content = _content_is_dangerous(arguments.get(content_key, ""))
            if dangerous_content is not None:
                return True, (
                    f"Blocked: dangerous write content pattern '{dangerous_content}'"
                )

        if tool_name == "apply_patch":
            for operation in _iter_apply_patch_operations(arguments):
                dangerous_path = _path_is_dangerous(operation.get("path", ""))
                if dangerous_path is not None:
                    return True, f"Blocked: dangerous write path '{dangerous_path}'"
                dangerous_content = _content_is_dangerous(operation.get("new_string", ""))
                if dangerous_content is not None:
                    return True, (
                        f"Blocked: dangerous write content pattern '{dangerous_content}'"
                    )

        return False, ""

    def is_shell_disabled(self) -> bool:
        """Check if shell execution is currently disabled."""
        return not self.shell_config.enabled

    def enable_shell(self) -> None:
        """Enable shell execution at runtime."""
        self.shell_config.enabled = True

    # Tools that mutate the filesystem or execute shell commands
    _MUTATING_TOOLS: frozenset[str] = frozenset({
        "write_file", "edit_file", "apply_patch", "run_command",
    })

    def is_write_blocked(self, tool_name: str) -> bool:
        """Check if write operations are blocked in read-only mode.

        Blocks ALL mutating tools: write_file, edit_file, run_command.
        """
        if self.mode == ApprovalMode.READ_ONLY:
            return tool_name in self._MUTATING_TOOLS
        return False
