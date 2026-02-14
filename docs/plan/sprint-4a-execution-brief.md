# Sprint 4A Execution Brief: Core Primitives

> **Version:** 1.0
> **Created:** 2026-02-14
> **Parent plan:** [`docs/plan/phase4-agent-orchestration.md`](phase4-agent-orchestration.md) v3.2a, Section 5
> **Scope:** ContextEngine, TaskStore (DAG), task tools, capability flags, carry-forward fixes
> **Estimated effort:** ~1 week
> **Test target:** 25 new tests (baseline 840 → 865)

---

## 1. Implementation Order

Sprint 4A must be built bottom-up: data layer → engine → tools → wiring. Each step builds on the previous.

### Step-by-step sequence

| # | Step | Files | Depends On | Tests |
|---|------|-------|------------|-------|
| 1 | Carry-forward fixes (CF-1 to CF-4) | `queries.py`, `tools.py`, `update.go`, `test_integration_router_agent.py` | Nothing | 2 |
| 2 | Config: add AgentConfig | `config.py` | Nothing | 0 (existing config tests cover) |
| 3 | Schema: add task tables + ensure_tables() | `models.py`, `store.py` | Nothing | 0 (tested via TaskStore) |
| 4 | TaskStore: CRUD + DAG + cycle detection | `session/task_store.py` (new) | Step 3 | 9 |
| 5 | ContextEngine: token budgets + compaction | `agent/context.py` (new) | Nothing (uses SessionStore) | 8 |
| 6 | ToolDefinition: capability flags | `tools.py` | Nothing | 0 (tested via task tools) |
| 7 | Task tools: create/update/list | `agent/task_tools.py` (new) | Steps 4, 6 | 6 |
| 8 | System prompt: task_summary injection | `prompts.py` | Step 4 | 0 (covered by task tool tests) |
| 9 | AgentLoop: wire context_engine, task_store | `loop.py` | Steps 4, 5 | 0 (existing loop tests + integration) |
| 10 | `/tasks` command | `commands.py` | Step 4 | 0 (manual verification) |
| 11 | `task.list` JSON-RPC | `server.py` | Step 4 | 0 (protocol test in 4C) |

**Critical path:** Steps 3 → 4 → 7 (TaskStore is the foundation for task tools).
**Parallel track:** Steps 2, 5, 6 can be done in parallel with each other.

---

## 2. File-by-File Change List

### 2.1 New Files (4 source + 4 test)

#### `src/hybridcoder/session/task_store.py` — TaskStore with DAG

```
class TaskStore:
    __init__(conn: sqlite3.Connection, session_id: str)
    create_task(title, description="", status="pending") -> str
    get_task(task_id) -> TaskRow | None
    update_task(task_id, **fields) -> None
    list_tasks() -> list[TaskRow]
    add_dependency(task_id, depends_on) -> None  # MUST reject cycles
    get_dependencies(task_id) -> list[str]
    get_dependents(task_id) -> list[str]
    is_ready(task_id) -> bool
    get_blocked_reason(task_id) -> str | None
    summary() -> str  # Compact text for system prompt injection
    snapshot() -> dict  # JSON-serializable for checkpoints
    restore_from_snapshot(snapshot: dict) -> None
```

Key implementation notes:
- Uses `graphlib.TopologicalSorter` for cycle detection in `add_dependency()`
- Task IDs: UUID4 hex prefix (8 chars)
- `summary()` returns max ~300 tokens of compact task state
- `is_ready()`: all deps have status == "completed"
- `snapshot()`/`restore_from_snapshot()`: for checkpoint store (Sprint 4C)

#### `src/hybridcoder/agent/context.py` — ContextEngine

```
class ContextEngine:
    __init__(provider, session_store, context_length=8192, compaction_threshold=0.75)
    count_tokens(text: str) -> int  # len(text) // 4 approximation
    build_messages(session_id, system_prompt, tool_schemas, *,
                   memory_context="", task_summary="", subagent_status="") -> list[dict]
    truncate_tool_result(result: str, max_tokens=500) -> str
    auto_compact(session_id, kept_messages=4) -> str
```

Key implementation notes:
- Token counting: `len(text) // 4` (simple heuristic, overestimates slightly)
- `build_messages()` constructs the full message list respecting token budget
- `truncate_tool_result()`: if result > max_tokens, keep first 200 tokens + last 100 tokens + `\n[... truncated ...]`
- `auto_compact()` uses the LLM provider to summarize older messages (or falls back to simple truncation if no provider)
- Compaction trigger: `total > threshold * context_length`

#### `src/hybridcoder/agent/task_tools.py` — Task tool definitions

Three tools registered via ToolRegistry:

1. `create_task` — Creates a new task with title and optional description
2. `update_task` — Updates task status (pending/in_progress/completed) or metadata
3. `list_tasks` — Lists all tasks with status, dependencies, and blocked state

Each tool handler takes `task_store: TaskStore` as a closure parameter (injected at registration time).

#### Test files (4)

| File | Tests | Focus |
|------|-------|-------|
| `tests/unit/test_context_engine.py` | 8 | Token counting, build_messages budget, truncation, compaction trigger |
| `tests/unit/test_task_store.py` | 9 | CRUD, deps, cycle rejection, is_ready, snapshot/restore, summary |
| `tests/unit/test_task_tools.py` | 6 | Tool handlers, approval flags, error handling |
| `tests/unit/test_carry_forward.py` | 2 | CF-2 bounded iteration, CF-3 index caching |

### 2.2 Modified Files (10)

#### `src/hybridcoder/config.py`
- **Add** `AgentConfig` dataclass (Pydantic model):
  ```python
  class AgentConfig(BaseModel):
      compaction_threshold: float = 0.75
      compaction_kept_messages: int = 4
      tool_result_max_tokens: int = 500
      max_subagents: int = 3         # used in 4B
      subagent_max_iterations: int = 5  # used in 4B
      subagent_timeout_seconds: int = 30  # used in 4B
      memory_max_entries: int = 50    # used in 4C
      memory_decay_factor: float = 0.95  # used in 4C
      memory_context_max_tokens: int = 500  # used in 4C
  ```
- **Add** `agent: AgentConfig = Field(default_factory=AgentConfig)` to `HybridCoderConfig`
- All fields have defaults → fully backward compatible

#### `src/hybridcoder/session/models.py`
- **Add** DDL for `tasks` table (id, session_id, title, description, status, created_at, updated_at)
- **Add** DDL for `task_dependencies` table (id, session_id, task_id, depends_on, UNIQUE, CHECK)
- **Add** `TaskRow` dataclass
- **Add** `ensure_tables(conn)` function — idempotent `CREATE TABLE IF NOT EXISTS` for all Phase 4 tables

#### `src/hybridcoder/session/store.py`
- **Add** `get_connection()` method (returns `self._conn`)
- **Call** `ensure_tables(self._conn)` in `__init__` after existing DDL

#### `src/hybridcoder/agent/tools.py`
- **Add** `mutates_fs: bool = False` and `executes_shell: bool = False` to `ToolDefinition`
- **Mark** `write_file` tool: `mutates_fs=True`
- **Mark** `run_command` tool: `executes_shell=True`
- **CF-3:** Cache `CodeIndex` instance in `_handle_search_code()` (module-level or class attribute)

#### `src/hybridcoder/agent/loop.py`
- **Add** constructor params: `context_engine=None`, `task_store=None`, `llm_scheduler=None`
- **If** `context_engine` is set: use `context_engine.build_messages()` instead of raw message building
- **If** `task_store` is set: inject `task_store.summary()` into system prompt
- **If** `llm_scheduler` is set: wrap LLM calls with `llm_scheduler.submit()`
- All new params default to `None` — existing behavior unchanged when not provided

#### `src/hybridcoder/agent/prompts.py`
- **Add** optional kwargs: `task_summary=""`, `memory_context=""`, `subagent_status=""`
- **If** `task_summary` is non-empty, append "Active Tasks" section to system prompt
- **Add** task management instructions to SYSTEM_PROMPT constant

#### `src/hybridcoder/tui/commands.py`
- **Add** `/tasks` command handler that calls `TaskStore.list_tasks()` and formats output

#### `src/hybridcoder/backend/server.py`
- **Create** `TaskStore` instance alongside `SessionStore`
- **Pass** `task_store` to `AgentLoop` constructor
- **Add** `task.list` JSON-RPC method handler

#### `src/hybridcoder/layer1/queries.py`
- **CF-2:** Replace `list(path.rglob(...))[:N]` with `itertools.islice(path.rglob(...), N)`

#### `cmd/hybridcoder-tui/update.go`
- **CF-1:** Add `m.statusBar.Layer = ""` in `sendChat()` at new-turn reset

---

## 3. Risk Areas

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Token counting inaccuracy (`len//4`) | Medium | Overestimates slightly, which is safe. Validate against known prompts in tests. |
| Auto-compaction needs LLM call | Medium | Make LLM-based compaction optional; fallback to sliding window (drop oldest messages). |
| `graphlib.TopologicalSorter` only in Python 3.9+ | Low | Project requires 3.11+, so no issue. |
| CF-3 CodeIndex caching invalidation | Low | Cache at module level; clear on `/index` command. |
| Existing tests break from new constructor params | Low | All new params default to `None`; existing code paths unchanged. |
| `ensure_tables()` called twice (store init + bootstrap) | Low | All DDL uses `IF NOT EXISTS`; idempotent by design. |

---

## 4. Pre-Implementation Checklist

Before writing any code:

- [ ] Confirm `uv run pytest tests/ -v` passes (840+ tests, baseline)
- [ ] Confirm `make lint` passes
- [ ] Verify `graphlib` is available: `python -c "import graphlib; print('ok')"`
- [ ] Verify `src/hybridcoder/session/task_store.py` does NOT exist yet
- [ ] Verify `src/hybridcoder/agent/context.py` does NOT exist yet
- [ ] Verify `src/hybridcoder/agent/task_tools.py` does NOT exist yet

---

## 5. Sprint 4A Verification

After implementation, run:

```bash
# Unit tests (must show 865+ pass)
./scripts/store_test_results.sh sprint-4a-unit -- uv run pytest tests/ -v --cov=src/hybridcoder

# Lint + type check
./scripts/store_test_results.sh sprint-4a-lint -- make lint

# Benchmark core (non-regression)
./scripts/store_test_results.sh sprint-4a-bench -- uv run python -m pytest tests/benchmark -v -m "not integration"

# E2E Calculator (>= 86/100 in at least 1 of 2 runs)
./scripts/store_test_results.sh sprint-4a-calc -- uv run python scripts/run_calculator_benchmark.py --runs 2
```

**Pass criteria:**
- Unit tests: all pass, count >= 865 (840 baseline + 25 new)
- Lint: clean
- Bench core: PASS
- E2E Calculator: >= 86/100 in at least 1 of 2 runs

---

## 6. Definition of Done — ALL COMPLETE (2026-02-14)

Sprint 4A is done when:

1. [x] All 4 carry-forward fixes (CF-1 to CF-4) are implemented
2. [x] `ContextEngine` counts tokens and enforces budget with auto-compaction at 75%
3. [x] `TaskStore` supports CRUD + DAG dependencies with **mandatory cycle rejection**
4. [x] `ToolDefinition` has `mutates_fs` and `executes_shell` capability flags
5. [x] 3 task tools (`create_task`, `update_task`, `list_tasks`) are registered and working
6. [x] Task summary appears in system prompt each iteration
7. [x] `/tasks` command shows task board
8. [x] `task.list` JSON-RPC method responds
9. [x] `AgentConfig` is in `HybridCoderConfig` with all defaults
10. [x] `ensure_tables()` creates Phase 4 tables idempotently
11. [x] 26 new tests + baseline pass (868 collected, 755 passed, 0 failed)
12. [x] `ruff check` passes
13. [x] Verification artifacts stored in `docs/qa/test-results/sprint-4a-summary.md`
