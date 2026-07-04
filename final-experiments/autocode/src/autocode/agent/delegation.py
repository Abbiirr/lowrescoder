"""Delegation policy — bounded agent spawning with per-subagent rules.

Based on patterns from:
- Codex: agents.max_depth, agents.max_threads, default depth 1
- OpenCode: agent mode (primary/subagent/all), hidden agents, per-subagent permission.task rules
- Claude Code: per-subagent tool/permission config
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PermissionRule(StrEnum):
    """Permission for a specific action."""

    ALLOW = "allow"  # Always permitted
    ASK = "ask"  # Requires user confirmation
    DENY = "deny"  # Never permitted


class AgentMode(StrEnum):
    """Agent execution mode."""

    PRIMARY = "primary"  # Top-level agent (full permissions)
    SUBAGENT = "subagent"  # Spawned by another agent (restricted)
    INTERNAL = "internal"  # Hidden internal agent (compaction, title, summary)


@dataclass
class SubagentPermissions:
    """Per-subagent permission rules.

    Controls what a subagent can do. Primary agents inherit
    full permissions; subagents are restricted by default.
    """

    file_read: PermissionRule = PermissionRule.ALLOW
    file_write: PermissionRule = PermissionRule.ASK
    shell_exec: PermissionRule = PermissionRule.ASK
    network: PermissionRule = PermissionRule.DENY
    spawn_subagent: PermissionRule = PermissionRule.DENY
    git_operations: PermissionRule = PermissionRule.ASK

    # Tool allowlist/denylist
    allowed_tools: list[str] = field(default_factory=list)  # empty = all allowed
    denied_tools: list[str] = field(default_factory=list)

    def check_tool(self, tool_name: str) -> PermissionRule:
        """Check if a tool is permitted."""
        if tool_name in self.denied_tools:
            return PermissionRule.DENY
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return PermissionRule.DENY
        return PermissionRule.ALLOW

    @classmethod
    def primary(cls) -> SubagentPermissions:
        """Full permissions for primary agent."""
        return cls(
            file_read=PermissionRule.ALLOW,
            file_write=PermissionRule.ALLOW,
            shell_exec=PermissionRule.ALLOW,
            network=PermissionRule.ASK,
            spawn_subagent=PermissionRule.ALLOW,
            git_operations=PermissionRule.ALLOW,
        )

    @classmethod
    def restricted(cls) -> SubagentPermissions:
        """Restricted permissions for subagents."""
        return cls(
            file_read=PermissionRule.ALLOW,
            file_write=PermissionRule.ASK,
            shell_exec=PermissionRule.ASK,
            network=PermissionRule.DENY,
            spawn_subagent=PermissionRule.DENY,
            git_operations=PermissionRule.DENY,
        )

    @classmethod
    def read_only(cls) -> SubagentPermissions:
        """Read-only scout permissions."""
        return cls(
            file_read=PermissionRule.ALLOW,
            file_write=PermissionRule.DENY,
            shell_exec=PermissionRule.DENY,
            network=PermissionRule.DENY,
            spawn_subagent=PermissionRule.DENY,
            git_operations=PermissionRule.DENY,
            allowed_tools=["read_file", "search_code", "list_files",
                           "find_definition", "find_references"],
        )


@dataclass
class DelegationPolicy:
    """Controls agent spawning and delegation.

    Enforces depth limits, thread limits, and per-subagent permissions.
    """

    max_depth: int = 2  # Max nesting depth (Codex default: 1, ours: 2)
    max_threads: int = 3  # Max parallel subagents
    max_total_agents: int = 10  # Hard cap on total agents in a session

    # Per-role permission presets
    role_permissions: dict[str, SubagentPermissions] = field(
        default_factory=lambda: {
            "scout": SubagentPermissions.read_only(),
            "engineer": SubagentPermissions.restricted(),
            "architect": SubagentPermissions(
                file_read=PermissionRule.ALLOW,
                file_write=PermissionRule.ASK,
                shell_exec=PermissionRule.ASK,
                spawn_subagent=PermissionRule.ALLOW,
            ),
        },
    )

    # Tracking
    _current_depth: int = field(default=0, repr=False)
    _active_threads: int = field(default=0, repr=False)
    _total_spawned: int = field(default=0, repr=False)

    def can_spawn(self, role: str = "") -> tuple[bool, str]:
        """Check if a new subagent can be spawned.

        Returns (allowed, reason).
        """
        if self._current_depth >= self.max_depth:
            return False, f"Max depth reached ({self.max_depth})"
        if self._active_threads >= self.max_threads:
            return False, f"Max threads reached ({self.max_threads})"
        if self._total_spawned >= self.max_total_agents:
            return False, f"Max total agents reached ({self.max_total_agents})"
        return True, "ok"

    def spawn(self, role: str = "subagent") -> SubagentPermissions:
        """Register a spawn and return permissions for the new agent.

        Raises ValueError if spawn is not allowed.
        """
        allowed, reason = self.can_spawn(role)
        if not allowed:
            raise ValueError(f"Cannot spawn subagent: {reason}")

        self._current_depth += 1
        self._active_threads += 1
        self._total_spawned += 1

        # Look up role-specific permissions, fall back to restricted
        return self.role_permissions.get(role, SubagentPermissions.restricted())

    def release(self) -> None:
        """Release a completed subagent."""
        if self._active_threads > 0:
            self._active_threads -= 1
        if self._current_depth > 0:
            self._current_depth -= 1

    @property
    def stats(self) -> dict[str, int]:
        """Current delegation stats."""
        return {
            "current_depth": self._current_depth,
            "active_threads": self._active_threads,
            "total_spawned": self._total_spawned,
            "max_depth": self.max_depth,
            "max_threads": self.max_threads,
        }
