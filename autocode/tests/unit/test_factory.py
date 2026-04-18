"""Tests for the shared AgentLoop factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.delegation import DelegationPolicy
from autocode.agent.factory import create_agent_loop, load_project_memory_content
from autocode.agent.tools import create_default_registry
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore


def test_create_agent_loop_preserves_runtime_dependencies(tmp_path: Path) -> None:
    """Factory should preserve optional runtime modules, not just the base loop."""
    session_store = SessionStore(tmp_path / "sessions.db")
    session_id = session_store.create_session(title="Test", model="m", provider="mock")
    tool_registry = create_default_registry(project_root=str(tmp_path))
    approval_manager = ApprovalManager(ApprovalMode.AUTO)
    task_store = TaskStore(session_store.get_connection(), session_id)
    subagent_manager = object()
    delegation_policy = DelegationPolicy(max_threads=2)

    loop, session_stats = create_agent_loop(
        provider=AsyncMock(),
        tool_registry=tool_registry,
        approval_manager=approval_manager,
        session_store=session_store,
        session_id=session_id,
        memory_content="project memory",
        task_store=task_store,
        subagent_manager=subagent_manager,
        memory_context="remember this",
        delegation_policy=delegation_policy,
        context_length=4096,
        compaction_threshold=0.8,
    )

    assert loop._context_engine is not None
    assert loop._context_engine._context_length == 4096
    assert loop._context_engine._compaction_threshold == 0.8
    assert loop._task_store is task_store
    assert loop._subagent_manager is subagent_manager
    assert loop._memory_context == "remember this"
    assert loop._delegation_policy is delegation_policy
    assert loop._middleware is not None
    assert loop._tool_shim is not None
    assert session_stats.token_tracker is loop._token_tracker
    assert loop._session_stats is session_stats
    assert session_stats.profiler is loop._profiler

    session_store.close()


def test_create_agent_loop_bootstraps_task_board_when_missing(tmp_path: Path) -> None:
    """Factory should create a task store and register task tools automatically."""
    session_store = SessionStore(tmp_path / "sessions.db")
    session_id = session_store.create_session(title="Test", model="m", provider="mock")
    tool_registry = create_default_registry(project_root=str(tmp_path))
    approval_manager = ApprovalManager(ApprovalMode.AUTO)

    loop, _ = create_agent_loop(
        provider=AsyncMock(),
        tool_registry=tool_registry,
        approval_manager=approval_manager,
        session_store=session_store,
        session_id=session_id,
    )

    assert loop._task_store is not None
    assert tool_registry.get("create_task") is not None
    assert tool_registry.get("list_tasks") is not None

    session_store.close()


def test_load_project_memory_content_merges_rules_and_memory(tmp_path: Path) -> None:
    """Always-on rules should be prepended ahead of project memory.

    Skill catalog section is orthogonal to this test — mock it empty so the
    rules-vs-memory ordering is the only thing asserted.
    """
    memory_dir = tmp_path / ".autocode"
    memory_dir.mkdir()
    (memory_dir / "memory.md").write_text("project memory", encoding="utf-8")

    with (
        patch("autocode.layer2.rules.RulesLoader") as mock_rules,
        patch("autocode.agent.skills.default_catalog") as mock_catalog,
    ):
        mock_rules.return_value.load.return_value = "rule A\nrule B"
        mock_catalog.return_value.scan.return_value = []
        result = load_project_memory_content(tmp_path)

    assert result == "rule A\nrule B\n\nproject memory"
