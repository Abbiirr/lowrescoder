# Phase 4: Agent Orchestration & Context Intelligence

> **Version:** 1.0
> **Created:** 2026-02-06
> **Status:** DRAFT — Awaiting Review
> **Research:** [`docs/claude/09-agent-orchestration-research.md`](../claude/09-agent-orchestration-research.md)
> **Prerequisites:** Phase 2 complete (307 tests passing), Sprint 2C (inline mode) in progress
> **Estimated effort:** ~2.5 weeks (Sprint 4A: ~1 week, Sprint 4B: ~1.5 weeks)

---

## Table of Contents

1. [Goals & Non-Goals](#1-goals--non-goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Sprint 4A: Context Engine + Task System](#3-sprint-4a-context-engine--task-system)
4. [Sprint 4B: Subagent Framework + Memory + Checkpoints](#4-sprint-4b-subagent-framework--memory--checkpoints)
5. [SQLite Schema Additions](#5-sqlite-schema-additions)
6. [File Inventory](#6-file-inventory)
7. [Configuration Additions](#7-configuration-additions)
8. [System Prompt Changes](#8-system-prompt-changes)
9. [Testing Strategy](#9-testing-strategy)
10. [Exit Criteria](#10-exit-criteria)
11. [Risks & Mitigations](#11-risks--mitigations)
12. [Dependencies](#12-dependencies)

---

## 1. Goals & Non-Goals

### Goals

1. **Context never exceeds `context_length` tokens** — auto-compaction enforced
2. **LLM can create, track, and complete tasks** with DAG dependencies
3. **Subagents** spawn in background, share LLM via asyncio.Lock, return summaries
4. **Episodic memories** extracted from sessions and injected into prompts
5. **Checkpoints** can be created and restored for resumable workflows
6. **~45 new tests** passing, all existing 307 tests still pass (target: ~352+)

### Non-Goals (Deferred)

| Item | Deferred To | Reason |
|------|------------|--------|
| Architect/Editor split | Phase 5 | Requires Layer 3 constrained generation |
| LLMLOOP feedback | Phase 5 | Requires tree-sitter + LSP (Layer 1) |
| Vector memory | Phase 4 Layer 2 | Requires embedding infrastructure |
| Dynamic agent swarms | Never | Not feasible on single GPU |
| MCP server | Phase 5+ | Out of scope for orchestration core |
| Git integration | Phase 3 | Separate concern |

---

## 2. Architecture Overview

### 2.1 Component Diagram

```
┌──────────────────────────────────────────────────────┐
│                    HybridCoderApp                     │
│  (TUI or Inline — both use the same agent backend)   │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ InputBar/    │  │  ChatView/   │  │ StatusBar/  │ │
│  │ PromptSession│  │  Console     │  │ TaskPanel   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                 │                  │        │
│  ┌──────▼─────────────────▼──────────────────▼──────┐ │
│  │              AgentLoop (refactored)               │ │
│  │  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ContextEngine │  │  LLM Lock    │              │ │
│  │  │(auto-compact)│  │(asyncio.Lock)│              │ │
│  │  └──────────────┘  └──────┬───────┘              │ │
│  │                           │                       │ │
│  │  ┌──────────────┐  ┌─────▼────────┐             │ │
│  │  │ToolRegistry  │  │SubagentMgr   │             │ │
│  │  │(+task tools) │  │(spawn/cancel)│             │ │
│  │  └──────────────┘  └──────────────┘             │ │
│  └───────────────────────┬───────────────────────────┘ │
│                          │                              │
│  ┌───────────────────────▼───────────────────────────┐ │
│  │                 SessionStore                       │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐           │ │
│  │  │TaskStore │ │MemoryStr │ │Chkpt    │           │ │
│  │  │(DAG)     │ │(episodic)│ │Store    │           │ │
│  │  └──────────┘ └──────────┘ └─────────┘           │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Single LLM + asyncio.Lock** | One 8B model on 8GB VRAM; cannot run parallel inference |
| **Non-LLM parallelism** | File I/O, search, parsing run concurrently while LLM is locked |
| **Auto-compaction at 75%** | Leaves 25% headroom for response + tool calls |
| **Tool result truncation** | >500 tokens → first 200 + last 100 + "[truncated]" (no LLM needed) |
| **Flat subagent hierarchy** | Subagents cannot spawn subagents (prevents recursive explosion) |
| **Subagent max 5 iterations** | Limits LLM lock contention; keeps subagents focused |
| **Memory max 50 entries** | Token budget for memory injection: ~500 tokens |
| **Memory decay 0.95x/session** | Unused memories fade; frequently-used memories persist |
| **TaskStore in same SQLite DB** | Shares connection with SessionStore; no new DB files |

### 2.3 Token Budget

For `context_length = 8192` (Qwen3-8B default):

| Component | Tokens | % | Notes |
|-----------|--------|---|-------|
| System prompt (base) | 400 | 5% | Static instructions |
| Environment section | 200 | 2% | Shell, approval, model info |
| Tool definitions | 600 | 7% | 6 base + 5 new tools |
| Memory context | 500 | 6% | Top-N memories by relevance |
| Task summary | 300 | 4% | Current task state (compact) |
| Subagent status | 200 | 2% | Running subagent summaries |
| Compact summary | 600 | 7% | Summarized older messages |
| Recent messages | 3400 | 41% | Last 4-8 messages (full) |
| Response headroom | 2000 | 24% | Space for LLM response |
| **Total** | **8200** | **~100%** | |

**Compaction trigger:** When `system + tools + memory + tasks + subagents + messages > 0.75 * context_length` (~6144 tokens), auto-compact older messages.

---

## 3. Sprint 4A: Context Engine + Task System

**Duration:** ~1 week
**Goal:** Automatic context management + LLM-driven task tracking

### 3.1 ContextEngine (`agent/context.py`)

The ContextEngine replaces the raw message-building logic in AgentLoop. It enforces token budgets and triggers auto-compaction.

#### 3.1.1 Class Definition

```python
class ContextEngine:
    """Manages context assembly and automatic compaction.

    Responsibilities:
    - Assemble messages for LLM calls with token budgets
    - Track token usage across components
    - Trigger auto-compaction when approaching budget limits
    - Truncate oversized tool results
    """

    def __init__(
        self,
        provider: Any,  # LLM provider (for count_tokens + compaction calls)
        session_store: SessionStore,
        context_length: int = 8192,
        compaction_threshold: float = 0.75,
    ) -> None: ...

    def count_tokens(self, text: str) -> int:
        """Count tokens using the provider's tokenizer."""
        ...

    def build_messages(
        self,
        session_id: str,
        system_prompt: str,
        tool_schemas: list[dict],
        *,
        memory_context: str = "",
        task_summary: str = "",
        subagent_status: str = "",
        extra_messages: list[dict] | None = None,
    ) -> list[dict]:
        """Assemble the message list for an LLM call.

        Token budget enforcement:
        1. Calculate fixed overhead (system + tools + memory + tasks + subagents)
        2. Allocate remaining budget to messages (oldest first)
        3. If over budget, trigger compaction
        4. Truncate individual tool results if >500 tokens
        """
        ...

    def truncate_tool_result(self, result: str, max_tokens: int = 500) -> str:
        """Truncate a tool result if it exceeds max_tokens.

        Strategy: keep first 200 tokens + last 100 tokens + "[truncated N tokens]"
        """
        ...

    async def auto_compact(
        self,
        session_id: str,
        kept_messages: int = 4,
    ) -> str:
        """Summarize old messages using the LLM, store summary.

        Called automatically when context exceeds 75% of budget.
        Returns the compact summary text.
        """
        ...

    def _estimate_tool_schema_tokens(self, schemas: list[dict]) -> int:
        """Estimate token count for tool schemas."""
        ...
```

#### 3.1.2 Auto-Compaction Flow

```
build_messages() called
    ↓
Calculate total tokens:
  fixed = system + tools + memory + tasks + subagents
  messages_tokens = sum(count_tokens(m) for m in session_messages)
  total = fixed + messages_tokens
    ↓
total > 0.75 * context_length?
  YES → await auto_compact(session_id)
        Re-fetch messages (now includes summary)
        Rebuild messages list
  NO  → Continue
    ↓
For each message:
  If role == "tool" and tokens > 500:
    message.content = truncate_tool_result(content)
    ↓
Return assembled messages
```

#### 3.1.3 Compaction Prompt

```python
COMPACTION_PROMPT = """Summarize the following conversation in under 300 tokens.
Focus on:
- What the user asked for
- Key decisions made
- Files modified and how
- Current state of the task
- Any unresolved issues

Conversation:
{messages_text}

Summary:"""
```

### 3.2 TaskStore (`session/task_store.py`)

SQLite-backed task storage with DAG dependencies.

#### 3.2.1 Class Definition

```python
@dataclass
class TaskRow:
    """A task in the task store."""
    id: str
    session_id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed
    priority: int  # 1=high, 2=medium, 3=low
    assigned_to: str  # "main" or subagent name
    parent_id: str | None  # for subtask grouping
    created_at: datetime
    updated_at: datetime


class TaskStore:
    """SQLite-backed task storage with DAG dependencies."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Use the same connection as SessionStore."""
        ...

    def create_task(
        self,
        session_id: str,
        title: str,
        description: str = "",
        priority: int = 2,
        assigned_to: str = "main",
        parent_id: str | None = None,
    ) -> str:
        """Create a task, returning its UUID."""
        ...

    def update_task(
        self,
        task_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        assigned_to: str | None = None,
    ) -> None:
        """Update task fields."""
        ...

    def get_task(self, task_id: str) -> TaskRow | None: ...
    def list_tasks(self, session_id: str) -> list[TaskRow]: ...
    def delete_task(self, task_id: str) -> None: ...

    # --- Dependencies ---

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Mark task_id as blocked by depends_on."""
        ...

    def remove_dependency(self, task_id: str, depends_on: str) -> None: ...

    def get_dependencies(self, task_id: str) -> list[str]:
        """Return IDs of tasks that this task depends on."""
        ...

    def get_dependents(self, task_id: str) -> list[str]:
        """Return IDs of tasks that depend on this task."""
        ...

    def is_ready(self, task_id: str) -> bool:
        """True if all dependencies are completed."""
        ...

    # --- Utilities ---

    def get_summary(self, session_id: str) -> str:
        """Return a compact text summary of all tasks for system prompt injection.

        Format:
        Tasks (3 pending, 1 in_progress, 2 completed):
        - [in_progress] #a1b2: Refactor auth module
        - [pending] #c3d4: Add unit tests (blocked by #a1b2)
        - [pending] #e5f6: Update docs
        """
        ...

    def snapshot(self, session_id: str) -> dict:
        """Return JSON-serializable snapshot for checkpoints."""
        ...
```

### 3.3 Task LLM Tools (`agent/task_tools.py`)

Three tools exposed to the LLM for task management.

#### 3.3.1 Tool Definitions

```python
def create_task_tool_definitions() -> list[ToolDefinition]:
    """Return ToolDefinitions for create_task, update_task, list_tasks."""
    return [
        ToolDefinition(
            name="create_task",
            description=(
                "Create a new task to track work. Use this to break down "
                "complex requests into smaller, trackable steps."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short task title (imperative form, e.g., 'Fix auth bug')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what needs to be done",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "1=high, 2=medium (default), 3=low",
                        "enum": [1, 2, 3],
                    },
                    "blocked_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs that must complete before this one",
                    },
                },
                "required": ["title"],
            },
            handler=...,  # Bound at registration time
            requires_approval=False,
        ),
        ToolDefinition(
            name="update_task",
            description=(
                "Update a task's status or details. Mark tasks as "
                "in_progress when starting work, completed when done."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to update (short prefix OK)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["task_id"],
            },
            handler=...,
            requires_approval=False,
        ),
        ToolDefinition(
            name="list_tasks",
            description="List all tasks for the current session.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            handler=...,
            requires_approval=False,
        ),
    ]
```

#### 3.3.2 Tool Handlers

```python
def _handle_create_task(
    task_store: TaskStore,
    session_id: str,
    title: str,
    description: str = "",
    priority: int = 2,
    blocked_by: list[str] | None = None,
) -> str:
    """Create a task and optionally add dependencies."""
    task_id = task_store.create_task(
        session_id=session_id,
        title=title,
        description=description,
        priority=priority,
    )
    if blocked_by:
        for dep_id in blocked_by:
            resolved = task_store.resolve_prefix(dep_id)
            if resolved:
                task_store.add_dependency(task_id, resolved)
    return f"Created task #{task_id[:8]}: {title}"


def _handle_update_task(
    task_store: TaskStore,
    task_id: str,
    status: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> str:
    """Update a task."""
    resolved = task_store.resolve_prefix(task_id)
    if not resolved:
        return f"Task not found: {task_id}"
    task_store.update_task(resolved, status=status, title=title, description=description)
    task = task_store.get_task(resolved)
    return f"Updated task #{resolved[:8]}: {task.title} [{task.status}]"


def _handle_list_tasks(task_store: TaskStore, session_id: str) -> str:
    """List all tasks."""
    return task_store.get_summary(session_id)
```

### 3.4 AgentLoop Refactor (`agent/loop.py`)

The AgentLoop is refactored to use ContextEngine and support task awareness.

#### 3.4.1 Changes Summary

| Current | After Refactor |
|---------|---------------|
| Raw message list building in `run()` | Delegated to `ContextEngine.build_messages()` |
| No token tracking | Token counting via provider |
| No auto-compaction | Auto-compaction at 75% budget |
| No task awareness | Task summary injected into system prompt |
| No LLM lock | `asyncio.Lock` for sequential LLM access |
| Tool results stored as-is | Tool results truncated if >500 tokens |

#### 3.4.2 Updated `__init__`

```python
class AgentLoop:
    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        approval_manager: ApprovalManager,
        session_store: SessionStore,
        session_id: str,
        memory_content: str | None = None,
        *,
        # New in Phase 4:
        context_engine: ContextEngine | None = None,
        task_store: TaskStore | None = None,
        llm_lock: asyncio.Lock | None = None,
    ) -> None:
        ...
        # Phase 4 additions
        self._context_engine = context_engine or ContextEngine(
            provider=provider,
            session_store=session_store,
            context_length=getattr(provider, 'context_length', 8192),
        )
        self._task_store = task_store
        self._llm_lock = llm_lock or asyncio.Lock()
```

#### 3.4.3 Updated `run()` — Key Diff

```python
async def run(self, user_message: str, ...) -> str:
    self._cancelled = False
    self.session_store.add_message(self.session_id, "user", user_message)

    # Build task summary if task store is available
    task_summary = ""
    if self._task_store:
        task_summary = self._task_store.get_summary(self.session_id)

    tool_schemas = self.tool_registry.get_schemas_openai_format()

    for _iteration in range(self.MAX_ITERATIONS):
        if self._cancelled:
            return "[Cancelled]"

        # Use ContextEngine to build messages (handles compaction + truncation)
        messages = await self._context_engine.build_messages(
            session_id=self.session_id,
            system_prompt=self._build_system_prompt(),
            tool_schemas=tool_schemas,
            memory_context=self._memory_content or "",
            task_summary=task_summary,
        )

        # Acquire LLM lock for sequential access
        async with self._llm_lock:
            response = await self.provider.generate_with_tools(
                messages, tool_schemas,
                on_chunk=on_chunk,
                on_thinking_chunk=on_thinking_chunk,
            )

        # ... rest of loop (tool execution, etc.) stays the same
        # Tool results are truncated by ContextEngine on next build_messages()
```

### 3.5 System Prompt Updates (`agent/prompts.py`)

#### 3.5.1 New Sections

```python
def build_system_prompt(
    memory_content: str | None = None,
    *,
    shell_enabled: bool = False,
    approval_mode: str = "suggest",
    # New in Phase 4:
    task_summary: str = "",
    memory_context: str = "",
    subagent_status: str = "",
) -> str:
    prompt = SYSTEM_PROMPT

    # Existing environment section
    env_lines = ["\n## Current Environment\n"]
    env_lines.append(f"- Approval mode: {approval_mode}\n")
    # ... existing shell status ...
    prompt += "".join(env_lines)

    # New: Task awareness
    if task_summary:
        prompt += f"\n## Active Tasks\n{task_summary}\n"

    # New: Memory context
    if memory_context:
        prompt += f"\n## Learned Patterns\n{memory_context}\n"

    # New: Subagent status
    if subagent_status:
        prompt += f"\n## Background Work\n{subagent_status}\n"

    # Existing memory injection
    if memory_content:
        prompt += f"\n## Project Memory\n{memory_content}\n"

    return prompt
```

#### 3.5.2 Task-Related System Prompt Addition

Add to `SYSTEM_PROMPT`:

```python
SYSTEM_PROMPT += (
    "\n\nTask management:\n"
    "- For multi-step work, use create_task to break it into trackable steps\n"
    "- Mark tasks in_progress when starting, completed when done\n"
    "- Check the Active Tasks section for current task state\n"
    "- You don't need tasks for simple questions or single-step work\n"
)
```

### 3.6 `/tasks` Slash Command (`tui/commands.py`)

```python
async def _handle_tasks(app: HybridCoderApp, args: str) -> None:
    """Show the task board for the current session."""
    chat = _get_chat(app)

    if not hasattr(app, '_task_store') or app._task_store is None:
        chat.add_message("system", "Task store not initialized.")
        return

    arg = args.strip().lower()

    if arg == "clear":
        tasks = app._task_store.list_tasks(app.session_id)
        for t in tasks:
            app._task_store.delete_task(t.id)
        chat.add_message("system", "All tasks cleared.")
        return

    summary = app._task_store.get_summary(app.session_id)
    if not summary or "0 pending" in summary and "0 in_progress" in summary:
        chat.add_message("system", "No tasks for this session.")
    else:
        chat.add_message("system", summary)
```

### 3.7 Sprint 4A Test Plan

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `tests/unit/test_context_engine.py` | 8 | Token counting, build_messages, truncation, auto-compact trigger, budget enforcement |
| `tests/unit/test_task_store.py` | 7 | CRUD, dependencies, ready check, summary, snapshot, prefix resolution |
| `tests/unit/test_task_tools.py` | 6 | create_task, update_task, list_tasks handlers, dependency wiring, error cases |
| **Total** | **21** | |

#### Key Test Cases — ContextEngine

```
test_count_tokens_basic
test_truncate_tool_result_short_passthrough
test_truncate_tool_result_long_truncated
test_build_messages_within_budget
test_build_messages_triggers_compaction
test_build_messages_injects_memory_and_tasks
test_auto_compact_summarizes_old_messages
test_tool_result_truncation_in_messages
```

#### Key Test Cases — TaskStore

```
test_create_and_get_task
test_update_task_status
test_list_tasks_by_session
test_add_dependency_and_check_ready
test_dependency_blocks_ready
test_get_summary_format
test_snapshot_and_restore
```

#### Key Test Cases — Task Tools

```
test_create_task_handler
test_create_task_with_dependencies
test_update_task_handler
test_update_task_not_found
test_list_tasks_handler
test_prefix_resolution
```

---

## 4. Sprint 4B: Subagent Framework + Memory + Checkpoints

**Duration:** ~1.5 weeks
**Goal:** Isolated subagent execution, episodic memory, resumable checkpoints
**Depends on:** Sprint 4A (ContextEngine, LLM lock, TaskStore)

### 4.1 SubagentLoop (`agent/subagent.py`)

#### 4.1.1 Subagent Types

| Type | Tools Available | Max Iterations | Use Case |
|------|----------------|---------------|----------|
| `explore` | read_file, list_files, search_text | 5 | Read-only codebase exploration |
| `plan` | read_file, list_files, search_text, create_task | 5 | Research + task planning |
| `execute` | All tools (subject to approval) | 5 | Full tool access for subtask execution |

#### 4.1.2 Class Definition

```python
@dataclass
class SubagentResult:
    """Result from a completed subagent run."""
    subagent_id: str
    subagent_type: str
    task: str
    summary: str
    status: str  # completed, failed, cancelled
    iterations_used: int
    duration_ms: int


class SubagentLoop:
    """An isolated agent loop with restricted tools and separate context.

    Key differences from main AgentLoop:
    - Max 5 iterations (not 10)
    - No approval callbacks (restricted tool set handles safety)
    - No streaming (runs in background, returns summary)
    - Shares LLM lock with main agent
    - No session persistence (transient context)
    """

    MAX_ITERATIONS = 5

    def __init__(
        self,
        subagent_id: str,
        subagent_type: str,  # explore, plan, execute
        provider: Any,
        tool_registry: ToolRegistry,  # Restricted per type
        llm_lock: asyncio.Lock,
        task_store: TaskStore | None = None,
    ) -> None: ...

    async def run(self, task: str, context: str = "") -> SubagentResult:
        """Run the subagent to completion.

        Args:
            task: The task description for the subagent.
            context: Optional context from the main agent (e.g., relevant file contents).

        Returns:
            SubagentResult with summary of what was accomplished.
        """
        ...

    def cancel(self) -> None: ...


class SubagentManager:
    """Manages spawning, monitoring, and cancelling subagents.

    Responsibilities:
    - Spawn subagents as asyncio tasks
    - Track running subagents and their status
    - Cancel subagents on request
    - Provide status summary for system prompt injection
    - Limit concurrent subagents (max 3)
    """

    MAX_CONCURRENT = 3

    def __init__(
        self,
        provider: Any,
        base_tool_registry: ToolRegistry,
        llm_lock: asyncio.Lock,
        task_store: TaskStore | None = None,
    ) -> None: ...

    async def spawn(
        self,
        subagent_type: str,
        task: str,
        context: str = "",
    ) -> str:
        """Spawn a subagent, returning its ID.

        Raises ValueError if max concurrent subagents reached.
        """
        ...

    async def check(self, subagent_id: str) -> SubagentResult | None:
        """Check if a subagent has completed. Returns None if still running."""
        ...

    def cancel(self, subagent_id: str) -> bool:
        """Cancel a running subagent."""
        ...

    def cancel_all(self) -> None:
        """Cancel all running subagents."""
        ...

    def get_status_summary(self) -> str:
        """Return a compact summary of all subagent states.

        Format:
        Subagents:
        - [running] #sa01 (explore): Searching for auth modules...
        - [completed] #sa02 (plan): Found 3 relevant files → summary available
        """
        ...

    def _create_restricted_registry(self, subagent_type: str) -> ToolRegistry:
        """Create a tool registry restricted to the subagent's allowed tools."""
        ...
```

#### 4.1.3 Subagent System Prompt

```python
SUBAGENT_PROMPT_TEMPLATE = """You are a HybridCoder subagent ({subagent_type}).
Your task: {task}

{context_section}

Rules:
- Stay focused on your assigned task
- Be concise — your output is summarized for the main agent
- You have {max_iterations} iterations maximum
- Available tools: {tool_list}

When done, provide a clear summary of:
1. What you found or accomplished
2. Key files or facts discovered
3. Any recommendations
"""
```

### 4.2 Subagent LLM Tools (`agent/subagent_tools.py`)

Two tools for the main LLM to manage subagents.

```python
def create_subagent_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="spawn_subagent",
            description=(
                "Spawn a background subagent to handle a subtask. "
                "Types: 'explore' (read-only search), 'plan' (research + plan), "
                "'execute' (full tools). Use for parallel research or delegated work."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "subagent_type": {
                        "type": "string",
                        "enum": ["explore", "plan", "execute"],
                    },
                    "task": {
                        "type": "string",
                        "description": "What the subagent should do",
                    },
                    "context": {
                        "type": "string",
                        "description": "Relevant context to pass to the subagent",
                    },
                },
                "required": ["subagent_type", "task"],
            },
            handler=...,
            requires_approval=False,
        ),
        ToolDefinition(
            name="check_subagent",
            description="Check the status of a running subagent.",
            parameters={
                "type": "object",
                "properties": {
                    "subagent_id": {
                        "type": "string",
                        "description": "The subagent ID to check",
                    },
                },
                "required": ["subagent_id"],
            },
            handler=...,
            requires_approval=False,
        ),
    ]
```

### 4.3 MemoryStore (`agent/memory.py`)

Episodic memory stored in SQLite, injected into system prompts.

#### 4.3.1 Memory Categories

| Category | Example | Extraction Trigger |
|----------|---------|-------------------|
| `tool_pattern` | "User prefers write_file over run_command for edits" | Tool usage patterns |
| `user_preference` | "User uses pytest with -v flag" | User behavior |
| `project_fact` | "Auth module is in src/auth/handler.py" | Codebase discoveries |
| `error_resolution` | "ImportError for X fixed by installing Y" | Error → fix sequences |

#### 4.3.2 Class Definition

```python
@dataclass
class MemoryEntry:
    id: str
    project_dir: str
    category: str  # tool_pattern, user_preference, project_fact, error_resolution
    content: str
    relevance: float  # 0.0-1.0, decays by 0.95x per session
    use_count: int
    created_at: datetime
    updated_at: datetime


class MemoryStore:
    """Episodic memory storage with relevance decay."""

    MAX_ENTRIES_PER_PROJECT = 50

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Share connection with SessionStore."""
        ...

    def add_memory(
        self,
        project_dir: str,
        category: str,
        content: str,
        relevance: float = 1.0,
    ) -> str:
        """Add a memory entry. Deduplicates similar content."""
        ...

    def get_memories(
        self,
        project_dir: str,
        categories: list[str] | None = None,
        min_relevance: float = 0.1,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Get memories sorted by relevance * recency."""
        ...

    def touch_memory(self, memory_id: str) -> None:
        """Increment use_count and refresh relevance to 1.0."""
        ...

    def decay_all(self, project_dir: str, factor: float = 0.95) -> None:
        """Decay all memories for a project by factor.

        Called at the start of each new session.
        Memories below min_relevance (0.1) are deleted.
        """
        ...

    def get_context(self, project_dir: str, max_tokens: int = 500) -> str:
        """Build memory context for system prompt injection.

        Format:
        Learned patterns:
        - [project_fact] Auth module is in src/auth/handler.py
        - [user_preference] User prefers pytest -v
        - [error_resolution] ImportError for X → install Y
        """
        ...

    async def learn_from_session(
        self,
        session_store: SessionStore,
        session_id: str,
        project_dir: str,
        provider: Any,
        llm_lock: asyncio.Lock,
    ) -> list[MemoryEntry]:
        """Analyze a session's messages to extract memories.

        Uses the LLM to identify patterns, preferences, and facts.
        Called after a session ends or on /memory save.
        """
        ...

    def _deduplicate(self, project_dir: str, content: str) -> str | None:
        """Check for similar existing memory. Returns existing ID if duplicate."""
        ...
```

#### 4.3.3 Memory Extraction Prompt

```python
MEMORY_EXTRACTION_PROMPT = """Analyze the following conversation and extract useful memories.
Return a JSON array of objects with fields: category, content

Categories:
- tool_pattern: Patterns in how tools were used effectively
- user_preference: User's coding style, tool preferences, workflow habits
- project_fact: Important facts about the project structure or architecture
- error_resolution: Errors encountered and how they were resolved

Only extract genuinely useful, reusable insights. Skip trivial or one-off items.
Maximum 5 entries.

Conversation:
{messages_text}

JSON:"""
```

### 4.4 CheckpointStore (`session/checkpoint_store.py`)

Save/restore agent state for resumable workflows.

#### 4.4.1 Class Definition

```python
@dataclass
class Checkpoint:
    id: str
    session_id: str
    label: str
    plan: str  # Current plan text
    tasks_snapshot: str  # JSON of task states
    context_summary: str  # Compact summary at checkpoint time
    active_files: str  # JSON list of files being worked on
    created_at: datetime


class CheckpointStore:
    """Save and restore agent state checkpoints."""

    def __init__(self, conn: sqlite3.Connection) -> None: ...

    def save_checkpoint(
        self,
        session_id: str,
        label: str,
        *,
        plan: str = "",
        tasks_snapshot: str = "{}",
        context_summary: str = "",
        active_files: str = "[]",
    ) -> str:
        """Save a checkpoint, returning its UUID."""
        ...

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None: ...

    def list_checkpoints(self, session_id: str) -> list[Checkpoint]:
        """List checkpoints for a session, newest first."""
        ...

    def delete_checkpoint(self, checkpoint_id: str) -> None: ...

    def restore_context(self, checkpoint_id: str) -> dict:
        """Return checkpoint data for restoring agent state.

        Returns dict with keys: plan, tasks_snapshot, context_summary, active_files
        """
        ...
```

### 4.5 `/memory` and `/checkpoint` Slash Commands

```python
async def _handle_memory(app: HybridCoderApp, args: str) -> None:
    """View or manage episodic memories."""
    chat = _get_chat(app)
    arg = args.strip().lower()

    if not hasattr(app, '_memory_store') or app._memory_store is None:
        chat.add_message("system", "Memory store not initialized.")
        return

    if arg == "save":
        # Extract memories from current session
        chat.add_message("system", "Analyzing session for patterns...")
        memories = await app._memory_store.learn_from_session(
            app.session_store, app.session_id,
            str(app.project_root), app._provider, app._llm_lock,
        )
        if memories:
            lines = [f"Extracted {len(memories)} memories:"]
            for m in memories:
                lines.append(f"- [{m.category}] {m.content}")
            chat.add_message("system", "\n".join(lines))
        else:
            chat.add_message("system", "No new patterns found.")
        return

    if arg == "clear":
        # Not implemented yet — would need project_dir filtering
        chat.add_message("system", "Use /memory save to extract, or view current memories.")
        return

    # Default: show current memories
    context = app._memory_store.get_context(str(app.project_root))
    if context:
        chat.add_message("system", context)
    else:
        chat.add_message("system", "No memories stored for this project.")


async def _handle_checkpoint(app: HybridCoderApp, args: str) -> None:
    """Save or restore checkpoints."""
    chat = _get_chat(app)
    arg = args.strip()

    if not hasattr(app, '_checkpoint_store') or app._checkpoint_store is None:
        chat.add_message("system", "Checkpoint store not initialized.")
        return

    if arg.startswith("save"):
        label = arg[4:].strip() or f"checkpoint-{datetime.now().strftime('%H%M')}"
        # Build checkpoint data
        tasks_snapshot = "{}"
        if hasattr(app, '_task_store') and app._task_store:
            import json
            tasks_snapshot = json.dumps(app._task_store.snapshot(app.session_id))
        cp_id = app._checkpoint_store.save_checkpoint(
            session_id=app.session_id,
            label=label,
            tasks_snapshot=tasks_snapshot,
        )
        chat.add_message("system", f"Checkpoint saved: {label} (#{cp_id[:8]})")
        return

    if arg.startswith("restore"):
        cp_id_prefix = arg[7:].strip()
        if not cp_id_prefix:
            chat.add_message("system", "Usage: /checkpoint restore <id-prefix>")
            return
        checkpoints = app._checkpoint_store.list_checkpoints(app.session_id)
        match = None
        for cp in checkpoints:
            if cp.id.startswith(cp_id_prefix):
                match = cp
                break
        if not match:
            chat.add_message("system", f"Checkpoint not found: {cp_id_prefix}")
            return
        chat.add_message("system", f"Restored checkpoint: {match.label}")
        return

    # Default: list checkpoints
    checkpoints = app._checkpoint_store.list_checkpoints(app.session_id)
    if not checkpoints:
        chat.add_message("system", "No checkpoints for this session.")
    else:
        lines = ["**Checkpoints:**"]
        for cp in checkpoints:
            lines.append(f"- `{cp.id[:8]}` {cp.label} ({cp.created_at.strftime('%H:%M')})")
        chat.add_message("system", "\n".join(lines))
```

### 4.6 TaskPanel Widget (`tui/widgets/task_panel.py`)

A collapsible panel showing active tasks in the TUI.

```python
class TaskPanel(Static):
    """Collapsible task display panel for the TUI sidebar.

    Shows active tasks as a compact list, updated after each agent iteration.
    """

    def __init__(self, task_store: TaskStore | None = None, session_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self._task_store = task_store
        self._session_id = session_id
        self._collapsed = True

    def refresh_tasks(self, session_id: str | None = None) -> None:
        """Re-render the task list from the store."""
        if session_id:
            self._session_id = session_id
        if not self._task_store or not self._session_id:
            self.update("")
            return

        tasks = self._task_store.list_tasks(self._session_id)
        if not tasks:
            self.update("")
            return

        # Build compact display
        lines = []
        status_icons = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
        for t in tasks:
            icon = status_icons.get(t.status, "[?]")
            lines.append(f"{icon} {t.title}")
        self.update("\n".join(lines))

    def toggle(self) -> None:
        """Toggle collapsed state."""
        self._collapsed = not self._collapsed
        self.display = not self._collapsed
```

### 4.7 App Integration (`tui/app.py`)

Changes to `HybridCoderApp` to wire everything together:

```python
class HybridCoderApp(App[None]):
    def __init__(self, ...):
        ...
        # Phase 4 additions
        self._llm_lock: asyncio.Lock = asyncio.Lock()
        self._task_store: TaskStore | None = None
        self._memory_store: MemoryStore | None = None
        self._checkpoint_store: CheckpointStore | None = None
        self._subagent_manager: SubagentManager | None = None

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize with Phase 4 components."""
        if self._agent_loop is not None:
            return self._agent_loop

        # ... existing provider/registry/approval init ...

        # Phase 4: Initialize stores using same DB connection
        conn = self.session_store._conn
        self._task_store = TaskStore(conn)
        self._memory_store = MemoryStore(conn)
        self._checkpoint_store = CheckpointStore(conn)

        # Register task tools
        from hybridcoder.agent.task_tools import register_task_tools
        register_task_tools(self._tool_registry, self._task_store, self.session_id)

        # Register subagent tools
        from hybridcoder.agent.subagent_tools import register_subagent_tools
        self._subagent_manager = SubagentManager(
            provider=self._provider,
            base_tool_registry=self._tool_registry,
            llm_lock=self._llm_lock,
            task_store=self._task_store,
        )
        register_subagent_tools(self._tool_registry, self._subagent_manager)

        # Create ContextEngine
        from hybridcoder.agent.context import ContextEngine
        context_engine = ContextEngine(
            provider=self._provider,
            session_store=self.session_store,
            context_length=self.config.llm.context_length,
        )

        # Decay memories at session start
        self._memory_store.decay_all(str(self.project_root))

        self._agent_loop = AgentLoop(
            provider=self._provider,
            tool_registry=self._tool_registry,
            approval_manager=self._approval_manager,
            session_store=self.session_store,
            session_id=self.session_id,
            memory_content=memory_content,
            context_engine=context_engine,
            task_store=self._task_store,
            llm_lock=self._llm_lock,
        )
        return self._agent_loop
```

### 4.8 Sprint 4B Test Plan

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `tests/unit/test_subagent.py` | 8 | SubagentLoop run, cancel, restricted tools, max iterations, SubagentManager spawn/check/cancel, status summary, max concurrent |
| `tests/unit/test_subagent_tools.py` | 4 | spawn_subagent handler, check_subagent handler, invalid type error, max concurrent error |
| `tests/unit/test_memory.py` | 7 | add/get memory, decay, deduplication, get_context, learn_from_session (mock LLM), touch_memory |
| `tests/unit/test_checkpoint.py` | 5 | save/get/list/delete checkpoint, restore_context |
| **Total** | **24** | |

#### Key Test Cases — SubagentLoop

```
test_subagent_explore_read_only
test_subagent_plan_creates_tasks
test_subagent_max_iterations
test_subagent_cancel
test_subagent_manager_spawn_and_check
test_subagent_manager_cancel_all
test_subagent_manager_max_concurrent
test_subagent_status_summary
```

#### Key Test Cases — MemoryStore

```
test_add_memory_basic
test_get_memories_by_category
test_decay_reduces_relevance
test_decay_deletes_low_relevance
test_deduplicate_similar_content
test_get_context_format
test_learn_from_session_extracts_patterns
```

#### Key Test Cases — CheckpointStore

```
test_save_and_get_checkpoint
test_list_checkpoints_by_session
test_delete_checkpoint
test_restore_context_returns_data
test_checkpoint_with_tasks_snapshot
```

---

## 5. SQLite Schema Additions

All new tables share the same SQLite database as `SessionStore`. DDL additions go in `session/models.py`.

### 5.1 Tasks Table

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed
    priority INTEGER NOT NULL DEFAULT 2,     -- 1=high, 2=medium, 3=low
    assigned_to TEXT NOT NULL DEFAULT 'main', -- 'main' or subagent ID
    parent_id TEXT,                           -- for subtask grouping
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(session_id, status);
```

### 5.2 Task Dependencies Table

```sql
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL REFERENCES tasks(id),
    depends_on TEXT NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (task_id, depends_on)
);

CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_dep ON task_dependencies(depends_on);
```

### 5.3 Memories Table

```sql
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    project_dir TEXT NOT NULL,
    category TEXT NOT NULL,      -- tool_pattern, user_preference, project_fact, error_resolution
    content TEXT NOT NULL,
    relevance REAL NOT NULL DEFAULT 1.0,
    use_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_dir);
CREATE INDEX IF NOT EXISTS idx_memories_relevance ON memories(project_dir, relevance);
```

### 5.4 Checkpoints Table

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    label TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT '',
    tasks_snapshot TEXT NOT NULL DEFAULT '{}',
    context_summary TEXT NOT NULL DEFAULT '',
    active_files TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id);
```

---

## 6. File Inventory

### 6.1 New Files (15)

```
src/hybridcoder/agent/context.py            # ContextEngine
src/hybridcoder/agent/subagent.py            # SubagentLoop, SubagentManager, SubagentResult
src/hybridcoder/agent/subagent_tools.py      # spawn_subagent, check_subagent tool defs + handlers
src/hybridcoder/agent/task_tools.py          # create_task, update_task, list_tasks tool defs + handlers
src/hybridcoder/agent/memory.py              # MemoryStore
src/hybridcoder/session/task_store.py        # TaskStore (CRUD + DAG deps)
src/hybridcoder/session/checkpoint_store.py  # CheckpointStore
src/hybridcoder/tui/widgets/task_panel.py    # TaskPanel widget

tests/unit/test_context_engine.py            # ContextEngine tests
tests/unit/test_task_store.py                # TaskStore tests
tests/unit/test_task_tools.py                # Task tool handler tests
tests/unit/test_subagent.py                  # SubagentLoop + SubagentManager tests
tests/unit/test_subagent_tools.py            # Subagent tool handler tests
tests/unit/test_memory.py                    # MemoryStore tests
tests/unit/test_checkpoint.py                # CheckpointStore tests
```

### 6.2 Modified Files (7)

```
src/hybridcoder/agent/loop.py               # ContextEngine integration, LLM lock, task awareness
src/hybridcoder/agent/prompts.py             # task_summary, memory_context, subagent_status sections
src/hybridcoder/session/models.py            # New DDL for tasks, task_deps, memories, checkpoints + models
src/hybridcoder/session/store.py             # Expose _conn for shared access (or add accessor)
src/hybridcoder/config.py                    # AgentConfig section (context budget, memory settings)
src/hybridcoder/tui/app.py                   # Wire Phase 4 stores, llm_lock, subagent manager
src/hybridcoder/tui/commands.py              # /tasks, /memory, /checkpoint commands
```

---

## 7. Configuration Additions

Add to `config.py`:

```python
class AgentConfig(BaseModel):
    """Agent orchestration configuration (Phase 4)."""

    # Context management
    compaction_threshold: float = Field(
        default=0.75, ge=0.5, le=0.95,
        description="Trigger auto-compaction at this % of context budget",
    )
    compaction_kept_messages: int = Field(
        default=4, ge=2,
        description="Number of recent messages to keep after compaction",
    )
    tool_result_max_tokens: int = Field(
        default=500, ge=100,
        description="Max tokens for a tool result before truncation",
    )

    # Subagents
    max_subagents: int = Field(
        default=3, ge=1, le=10,
        description="Max concurrent subagents",
    )
    subagent_max_iterations: int = Field(
        default=5, ge=1, le=10,
        description="Max iterations per subagent",
    )

    # Memory
    memory_max_entries: int = Field(
        default=50, ge=10, le=200,
        description="Max memory entries per project",
    )
    memory_decay_factor: float = Field(
        default=0.95, ge=0.5, le=1.0,
        description="Memory relevance decay factor per session",
    )
    memory_context_max_tokens: int = Field(
        default=500, ge=100,
        description="Max tokens for memory context in system prompt",
    )
```

Add to `HybridCoderConfig`:

```python
class HybridCoderConfig(BaseModel):
    ...
    agent: AgentConfig = Field(default_factory=AgentConfig)
```

---

## 8. System Prompt Changes

### 8.1 Updated Base Prompt

Add task and subagent instructions to `SYSTEM_PROMPT`:

```python
SYSTEM_PROMPT += (
    "\n\nTask management:\n"
    "- For multi-step work, use create_task to break it into trackable steps\n"
    "- Mark tasks in_progress when starting, completed when done\n"
    "- Check the Active Tasks section for current task state\n"
    "- You don't need tasks for simple questions or single-step work\n"
    "\n"
    "Subagents:\n"
    "- Use spawn_subagent for parallel research or delegated work\n"
    "- Types: explore (read-only), plan (research + tasks), execute (full tools)\n"
    "- Check subagent results with check_subagent\n"
    "- Subagents run in the background — you can continue working while they run\n"
)
```

### 8.2 Dynamic Sections

`build_system_prompt()` gains three new optional sections:

1. **Active Tasks** — compact task list from `TaskStore.get_summary()`
2. **Learned Patterns** — memory context from `MemoryStore.get_context()`
3. **Background Work** — subagent status from `SubagentManager.get_status_summary()`

These are only included when non-empty, saving tokens when not in use.

---

## 9. Testing Strategy

### 9.1 Test Summary

| Sprint | New Tests | Cumulative |
|--------|-----------|------------|
| Existing (Phase 2) | 307 | 307 |
| Sprint 4A | 21 | 328 |
| Sprint 4B | 24 | 352 |
| **Total** | **45** | **352+** |

### 9.2 Testing Patterns

- **SQLite stores** — Use in-memory SQLite (`:memory:`) for fast tests
- **LLM calls** — Mock the provider; return canned responses for compaction/extraction
- **Subagents** — Mock the LLM; test tool restrictions and iteration limits
- **ContextEngine** — Mock token counting with `len(text) // 4`; test budget enforcement
- **TaskStore DAG** — Test dependency chains, cycle detection (if added), ready checks

### 9.3 Integration Points

Phase 4 must not break existing tests. Key integration risks:

| Risk | Mitigation |
|------|-----------|
| AgentLoop signature change | New params have defaults (backward compatible) |
| `build_system_prompt()` signature change | New params have defaults |
| `SessionStore._conn` exposure | Add `get_connection()` accessor method |
| DDL changes | New tables only (no schema changes to existing tables) |
| Config changes | New `agent` section with defaults (no changes to existing sections) |

---

## 10. Exit Criteria

### Sprint 4A

- [ ] ContextEngine correctly counts tokens and enforces budget
- [ ] Auto-compaction triggers at 75% and produces valid summaries
- [ ] Tool results >500 tokens are truncated
- [ ] TaskStore CRUD works with DAG dependencies
- [ ] LLM can create, update, and list tasks via tools
- [ ] Task summary injected into system prompt each iteration
- [ ] `/tasks` command shows task board
- [ ] 21 new tests pass, all 307 existing tests pass
- [ ] `ruff check` and `mypy` pass

### Sprint 4B

- [ ] SubagentLoop runs with restricted tools and max 5 iterations
- [ ] SubagentManager spawns, monitors, and cancels subagents
- [ ] LLM can spawn and check subagents via tools
- [ ] asyncio.Lock prevents concurrent LLM access
- [ ] MemoryStore saves, loads, and decays memories
- [ ] Memory extraction via LLM produces valid entries
- [ ] Memory context injected into system prompt
- [ ] CheckpointStore saves and restores state
- [ ] `/memory` and `/checkpoint` commands work
- [ ] TaskPanel widget displays in TUI
- [ ] 24 new tests pass, all 328 existing tests pass (total 352+)
- [ ] `ruff check` and `mypy` pass

---

## 11. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| **LLM lock contention** — subagents block main agent | High latency during subagent runs | Medium | Max 5 iterations per subagent; cancel on timeout; non-LLM work runs in parallel |
| **Auto-compaction quality** — 7B model produces bad summaries | Lost context, wrong responses | Medium | Test with Qwen3-8B; fallback to sliding window if summary quality is poor |
| **Token counting inaccuracy** — `len // 4` is rough | Context overflow or underflow | Low | Over-estimate by 10%; validate against actual model tokenizer if available |
| **Memory extraction garbage** — LLM extracts useless memories | Wasted tokens in prompts | Low | Limit to 5 extractions per session; human review via `/memory` |
| **SQLite lock contention** — multiple stores sharing connection | Database errors | Low | All stores use same connection (no concurrent writes from different threads); WAL mode |
| **Backward compatibility** — existing tests break | Delayed delivery | Low | All new params have defaults; new tables only |

---

## 12. Dependencies

### 12.1 Sprint Dependencies

```
Sprint 4A: ContextEngine + TaskStore + Task Tools
    ↓
Sprint 4B: SubagentLoop + SubagentManager + MemoryStore + CheckpointStore
           (depends on LLM lock and ContextEngine from 4A)
```

### 12.2 External Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | Available | Already required |
| SQLite 3.35+ | Available | WAL mode, JSON functions |
| Textual >=0.89 | Installed (7.5.0) | For TaskPanel widget |
| pytest-asyncio >=0.24 | Installed | For async tests |
| asyncio.Lock | stdlib | No external dep |

### 12.3 Cross-Phase Dependencies

Phase 4 does NOT depend on:
- Phase 3 (Layer 1 tree-sitter/LSP) — context/tasks work without deterministic analysis
- Sprint 2C (inline mode) — both rendering modes share the same agent backend

Phase 4 IS a prerequisite for:
- Phase 5 (Architect/Editor) — needs task system for multi-step plans
- Phase 5 (LLMLOOP) — needs checkpoint/restore for retry loops

---

*Plan v1.0 — 2026-02-06. Subject to review and revision.*
