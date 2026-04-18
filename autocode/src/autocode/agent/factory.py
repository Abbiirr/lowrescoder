"""Shared AgentLoop factory — ensures all frontends get the same runtime wiring.

All entry points (inline, backend, TUI) must use this factory instead of
constructing AgentLoop directly. This guarantees middleware, tool_shim,
token_tracker, and session_stats are always present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autocode.agent.approval import ApprovalManager
from autocode.agent.completion import SessionStats
from autocode.agent.context import ContextEngine
from autocode.agent.loop import AgentLoop
from autocode.agent.middleware import create_default_middleware
from autocode.agent.profiler import Profiler
from autocode.agent.task_tools import register_task_tools
from autocode.agent.token_tracker import TokenTracker
from autocode.agent.tool_shim import ToolShim
from autocode.agent.tools import ToolRegistry
from autocode.config import Layer2Config
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore

_RULES_MAX_CHARS = 3000  # Cap injected rules to ~750 tokens to prevent context pollution


def load_project_memory_content(project_root: Path) -> str | None:
    """Load project memory plus always-on rules for runtime prompt injection.

    Rules injection is capped at _RULES_MAX_CHARS characters to prevent large
    files (e.g. CLAUDE.md at 10KB) from polluting the LLM context and causing
    it to reproduce internal status text in its responses.
    """
    memory_content = None
    try:
        memory_content = (project_root / ".autocode" / "memory.md").read_text(encoding="utf-8")
    except OSError:
        pass

    try:
        from autocode.layer2.rules import RulesLoader

        rules_text = RulesLoader().load(project_root)
        if rules_text:
            # Truncate to cap — keep the start of the rules (invariants, stack)
            # which is more stable than the status/frontier sections at the end.
            if len(rules_text) > _RULES_MAX_CHARS:
                rules_text = (
                    rules_text[:_RULES_MAX_CHARS]
                    + "\n\n[...rules truncated for context budget...]"
                )
            memory_content = (
                f"{rules_text}\n\n{memory_content}"
                if memory_content
                else rules_text
            )
    except Exception:  # noqa: BLE001 — layer2 is optional; any failure degrades to no rules
        pass

    # Append a skills catalog (frontmatter only) so the model sees available
    # skills without loading their bodies. Loading is lazy per invocation.
    try:
        from autocode.agent.skills import default_catalog, skill_catalog_section

        catalog = default_catalog(project_root)
        entries = catalog.scan()
        section = skill_catalog_section(entries)
        if section:
            memory_content = (
                f"{memory_content}\n\n{section}" if memory_content else section
            )
    except Exception:  # noqa: BLE001 — skills discovery is optional; degrade silently
        pass

    return memory_content


def create_agent_loop(
    *,
    provider: Any,
    tool_registry: ToolRegistry,
    approval_manager: ApprovalManager,
    session_store: SessionStore,
    session_id: str,
    memory_content: str | None = None,
    task_store: Any | None = None,
    event_recorder: Any | None = None,
    subagent_manager: Any | None = None,
    memory_context: str = "",
    delegation_policy: Any | None = None,
    context_length: int = 8192,
    compaction_threshold: float = 0.75,
    layer2_config: Layer2Config | None = None,
) -> tuple[AgentLoop, SessionStats]:
    """Create a fully-wired AgentLoop with all Phase 7 runtime modules.

    Returns (loop, session_stats) so the caller can access stats after run.

    All frontends (inline, backend, TUI) should use this instead of
    constructing AgentLoop directly.
    """
    # Ensure the live runtime always has a task board and task tools available.
    if task_store is None:
        task_store = TaskStore(session_store.get_connection(), session_id)
    if tool_registry.get("create_task") is None:
        register_task_tools(tool_registry, task_store)

    # Context compaction
    context_engine = ContextEngine(
        provider=provider,
        session_store=session_store,
        context_length=context_length,
        compaction_threshold=compaction_threshold,
    )

    # Token tracking
    token_tracker = TokenTracker()
    session_stats = SessionStats()
    session_stats.token_tracker = token_tracker
    profiler = Profiler()
    session_stats.profiler = profiler

    # Middleware (dangerous command guard, repetition detection, etc.)
    middleware = create_default_middleware()

    # Tool shim for weak models
    tool_names = [t.name for t in tool_registry.get_all()]
    tool_shim = ToolShim(available_tools=tool_names)

    loop = AgentLoop(
        provider=provider,
        tool_registry=tool_registry,
        approval_manager=approval_manager,
        session_store=session_store,
        session_id=session_id,
        memory_content=memory_content,
        event_recorder=event_recorder,
        context_engine=context_engine,
        task_store=task_store,
        subagent_manager=subagent_manager,
        memory_context=memory_context,
        token_tracker=token_tracker,
        session_stats=session_stats,
        profiler=profiler,
        middleware=middleware,
        delegation_policy=delegation_policy,
        tool_shim=tool_shim,
        layer2_config=layer2_config,
    )

    return loop, session_stats


def create_orchestrator(
    *,
    provider: Any,
    tool_registry: ToolRegistry,
    approval_manager: ApprovalManager,
    session_store: SessionStore,
    session_id: str,
    memory_content: str | None = None,
    task_store: Any | None = None,
    event_recorder: Any | None = None,
    subagent_manager: Any | None = None,
    memory_context: str = "",
    delegation_policy: Any | None = None,
    context_length: int = 8192,
    compaction_threshold: float = 0.75,
    layer2_config: Layer2Config | None = None,
) -> tuple[Any, SessionStats]:
    """Create a fully-wired Orchestrator wrapping an AgentLoop.

    Returns (orchestrator, session_stats). The Orchestrator is the sole
    control plane; the AgentLoop is its internal worker accessible via
    orchestrator.agent_loop.
    """
    from autocode.agent.events import SqliteEventSink
    from autocode.agent.message_store import MessageStore
    from autocode.agent.orchestrator import Orchestrator

    # Create the inner AgentLoop
    loop, session_stats = create_agent_loop(
        provider=provider,
        tool_registry=tool_registry,
        approval_manager=approval_manager,
        session_store=session_store,
        session_id=session_id,
        memory_content=memory_content,
        task_store=task_store,
        event_recorder=event_recorder,
        subagent_manager=subagent_manager,
        memory_context=memory_context,
        delegation_policy=delegation_policy,
        context_length=context_length,
        compaction_threshold=compaction_threshold,
        layer2_config=layer2_config,
    )

    # Event infrastructure
    conn = session_store.get_connection()
    event_sink = SqliteEventSink(conn)
    message_store = MessageStore(conn, session_id, event_sink=event_sink)

    orchestrator = Orchestrator(
        agent_loop=loop,
        task_store=task_store,
        message_store=message_store,
        event_sink=event_sink,
        subagent_manager=subagent_manager,
        delegation_policy=delegation_policy,
        session_id=session_id,
    )

    return orchestrator, session_stats
