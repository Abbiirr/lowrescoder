"""Tests for delegation policy."""

from __future__ import annotations

import pytest

from autocode.agent.delegation import (
    DelegationPolicy,
    PermissionRule,
    SubagentPermissions,
)


def test_can_spawn_within_limits() -> None:
    """Spawning allowed when within limits."""
    policy = DelegationPolicy(max_depth=3, max_threads=2)
    allowed, reason = policy.can_spawn()
    assert allowed


def test_depth_limit() -> None:
    """Spawning blocked at max depth."""
    policy = DelegationPolicy(max_depth=1)
    policy.spawn()
    allowed, reason = policy.can_spawn()
    assert not allowed
    assert "depth" in reason.lower()


def test_thread_limit() -> None:
    """Spawning blocked at max threads."""
    policy = DelegationPolicy(max_depth=10, max_threads=2)
    policy.spawn()
    policy.spawn()
    allowed, reason = policy.can_spawn()
    assert not allowed
    assert "threads" in reason.lower()


def test_release_frees_slot() -> None:
    """Releasing a subagent frees a thread slot."""
    policy = DelegationPolicy(max_depth=2, max_threads=1)
    policy.spawn()
    allowed, _ = policy.can_spawn()
    assert not allowed

    policy.release()
    allowed, _ = policy.can_spawn()
    assert allowed


def test_spawn_returns_permissions() -> None:
    """Spawn returns appropriate permissions for role."""
    policy = DelegationPolicy()
    perms = policy.spawn("scout")
    assert perms.file_read == PermissionRule.ALLOW
    assert perms.file_write == PermissionRule.DENY
    assert perms.shell_exec == PermissionRule.DENY


def test_primary_permissions() -> None:
    """Primary agent has full permissions."""
    perms = SubagentPermissions.primary()
    assert perms.file_write == PermissionRule.ALLOW
    assert perms.shell_exec == PermissionRule.ALLOW
    assert perms.spawn_subagent == PermissionRule.ALLOW


def test_restricted_permissions() -> None:
    """Restricted subagent asks for dangerous operations."""
    perms = SubagentPermissions.restricted()
    assert perms.file_write == PermissionRule.ASK
    assert perms.shell_exec == PermissionRule.ASK
    assert perms.network == PermissionRule.DENY


def test_tool_allowlist() -> None:
    """Tool allowlist restricts available tools."""
    perms = SubagentPermissions.read_only()
    assert perms.check_tool("read_file") == PermissionRule.ALLOW
    assert perms.check_tool("write_file") == PermissionRule.DENY
    assert perms.check_tool("run_command") == PermissionRule.DENY


def test_total_agent_limit() -> None:
    """Hard cap on total agents in session."""
    policy = DelegationPolicy(max_depth=100, max_threads=100, max_total_agents=3)
    policy.spawn(); policy.release()
    policy.spawn(); policy.release()
    policy.spawn(); policy.release()
    allowed, reason = policy.can_spawn()
    assert not allowed
    assert "total" in reason.lower()


def test_stats() -> None:
    """Stats reflect current delegation state."""
    policy = DelegationPolicy(max_depth=5, max_threads=3)
    policy.spawn()
    policy.spawn()
    stats = policy.stats
    assert stats["current_depth"] == 2
    assert stats["active_threads"] == 2
    assert stats["total_spawned"] == 2
