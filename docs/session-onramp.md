# Session Onramp (Current State)

Last updated: 2026-02-17

This is the fastest way to rebuild working context for HybridCoder in a new session.

## 1) Read Order (10-15 minutes)

1. `AGENTS.md` — repo rules, command set, and communication protocol.
2. `CLAUDE.md` — architecture principles, project invariants, session index.
3. `TESTING.md` — how to test, evaluate, and interpret results.
4. `docs/requirements_and_features.md` — what is done vs planned.
5. `docs/plan/phase5-agent-teams.md` — Phase 5 plan (next phase).
6. `docs/plan/phase4-agent-orchestration.md` — Phase 4 plan (complete, reference).
7. `docs/qa/phase3-before-after-benchmark-protocol.md` — required benchmark workflow.

## 2) Authoritative vs Historical Docs

- Authoritative for Phase 5 implementation:
  - `docs/plan/phase5-agent-teams.md`
- Phase 4 (complete, reference only):
  - `docs/plan/phase4-agent-orchestration.md`
- Archived Phase 3 plans (do not treat as source of truth):
  - `docs/archive/plan/phase3-final-implementation.md`
  - `docs/archive/plan/phase3-execution-brief.md`
  - `docs/archive/phase3-code-intelligence.md`
  - `docs/archive/phase3-review-notes.md`
- Deleted (consolidated into plan.md):
  - `docs/spec.md` — MVP checklist now in `docs/plan.md` Section 1.6

## 3) Current System Snapshot

- Language/runtime split:
  - Python backend and CLI under `src/hybridcoder/`
  - Go TUI code under `cmd/hybridcoder-tui/` (JSON-RPC client to Python backend)
- Python UI frontends in repo:
  - Inline: `src/hybridcoder/inline/`
  - Textual: `src/hybridcoder/tui/`
- Agent tool baseline (current, 19 tools):
  - Phase 0-2: `read_file`, `write_file`, `list_files`, `search_text`, `run_command`, `ask_user`
  - Phase 3: `find_references`, `find_definition`, `get_type_info`, `list_symbols`, `search_code`
  - Phase 4 (Sprint 4A): `create_task`, `update_task`, `list_tasks`, `add_task_dependency`
  - Phase 4 (Sprint 4B): `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents`

## 4) Codebase Map (High Value Paths)

- Backend RPC server: `src/hybridcoder/backend/server.py`
- Tool registry: `src/hybridcoder/agent/tools.py`
- Config schema: `src/hybridcoder/config.py`
- Session state: `src/hybridcoder/session/`
- Task store (DAG): `src/hybridcoder/session/task_store.py`
- Context engine: `src/hybridcoder/agent/context.py`
- Task tools: `src/hybridcoder/agent/task_tools.py`
- Structured logging: `src/hybridcoder/core/logging.py`
- Blob store: `src/hybridcoder/core/blob_store.py`
- Episode store: `src/hybridcoder/session/episode_store.py`
- Event recorder: `src/hybridcoder/agent/event_recorder.py`
- Training export: `src/hybridcoder/training/exporter.py`
- Go TUI transport and event loop: `cmd/hybridcoder-tui/backend.go`, `cmd/hybridcoder-tui/update.go`
- Benchmarks: `tests/benchmark/`
- E2E scenario runner: `scripts/e2e/`
- E2E seed fixtures: `scripts/e2e/fixtures/`

## 5) Phase 3 Summary (COMPLETE)

Phase 3 (Code Intelligence) is complete as of 2026-02-13. All 3 gates passed.

- Layer 1 (Deterministic): tree-sitter parser, symbol extraction, request router, query handlers — 0 LLM tokens, <50ms
- Layer 2 (Retrieval): AST chunker, embeddings, LanceDB index, hybrid search (BM25+vector+RRF), repo map, rules loader, context assembler (5000-token budget)
- Integration: 11 tools total, L1 bypass in server, `/index` command, Go TUI layer indicator `[L1]`/`[L2]`/`[L4]`
- Deferred: Sprint 3C (LSP), `get_diagnostics` tool
- Tests: 840 Python + 275 Go = 1115+ passing. Ruff clean. Mypy clean.

See `docs/archive/plan/phase3-execution-brief.md` for completion summary.

## 5b) Phase 4 Sprint 4A Summary (COMPLETE)

Sprint 4A (Core Primitives) is complete as of 2026-02-14. All exit criteria passed.

- ContextEngine: token budgets (`len//4` heuristic), auto-compaction at 75%, tool result truncation (200+100 head/tail)
- TaskStore: SQLite-backed CRUD, DAG dependencies, mandatory cycle detection via `graphlib.TopologicalSorter`, snapshot/restore
- Task tools: `create_task`, `update_task`, `list_tasks`, `add_task_dependency` registered via factory pattern (15 tools total)
- ToolDefinition capability flags: `mutates_fs`, `executes_shell` (ready for Sprint 4B plan mode gating)
- AgentConfig: compaction/subagent/memory settings in `HybridCoderConfig`
- `/tasks` command (16 slash commands total), `task.list` JSON-RPC handler
- Carry-forward fixes: Go badge reset, islice bounded iteration, CodeIndex caching, layer_used assertion
- Tests: 868 collected, 755 passed, 113 skipped (tree-sitter dependent), 0 failed. Ruff clean.
- Sprint 4B/4C entry-point cues left in codebase

See `docs/plan/sprint-4a-execution-brief.md` and `docs/qa/test-results/sprint-4a-summary.md`.

## 5c) Post-Sprint 4A Logging Infrastructure (COMPLETE)

Implemented 2026-02-14 alongside Sprint 4A.

- **Timestamped session log directories:** Logs now land in `logs/<YYYY>/<MM>/<DD>/<HH>/<session[:8]>/` instead of flat `logs/`. Two-phase setup: `setup_logging()` for pre-session, `setup_session_logging()` after session creation.
- **`latest` pointer:** Symlink (or `.txt` fallback on Windows) at `logs/latest` for quick access to most recent session logs.
- **Training-grade event recorder (opt-in):** `EventRecorder` wraps episode/event/blob capture with fail-open guarantees. Disabled by default (`TrainingLogConfig.enabled = False`).
- **Episode/event store:** SQLite-backed with `UNIQUE(session_id, sequence_num)`, retention enforcement, deterministic replay ordering.
- **Content-addressed blob store:** SHA-256 dedup for large payloads (tool results, prompt/response dumps).
- **DPO provenance:** `human_edit` events with draft/edited text for training data.
- Tests: `test_logging.py` (19), `test_blob_store.py` (5), `test_episode_store.py` (7), `test_event_recorder.py` (4) — all passing.

## 5d) Post-Sprint 4A Bug Fix Batch (COMPLETE)

Implemented 2026-02-14. Resolved 9 bugs from `bugs.md`, 2 deferred (BUG-14 to 4B, BUG-20 to 4C).

- **Session safety (BUG-21/22):** `_task_store` reset on session new/resume/chat-switch. `_session_approved_tools` cleared on chat session switch.
- **Inline completion UX (BUG-15/17):** `ConditionalCompleter` activates dropdown only for `/` and `@` triggers. Ghost text for `@` file paths with prefix-match guard.
- **Task lifecycle logging (BUG-19):** `log_event()` calls for `task_created`, `task_updated`, `task_dependency_added`. `TaskStore.session_id` public property.
- **Task tool truncation bypass (BUG-23):** Task tools exempted from `ContextEngine.truncate_tool_result()`.
- **Path-scoped write intent (BUG-24):** Prompt policy rule (model-dependent, no deterministic guard).
- **Verified (BUG-16/18):** Go TUI `@` completion and task board visibility confirmed via tests.
- Tests: 903 collected, 790 passed, 113 skipped, 0 failed.
- Test artifact: `docs/qa/test-results/20260214-103203-bug-fixes.md`

## 5e) Sprint 4B: Subagents + Scheduling + Plan Mode (COMPLETE)

Implemented 2026-02-14. All tests passing, ruff clean.

- **LLMScheduler:** Single-worker asyncio PriorityQueue. Foreground (priority=0) before background (priority=1). FIFO within tier. `submit()` returns result via Future.
- **SubagentLoop:** Isolated mini agent loop — stateless, fresh context, filtered tool registry by SubagentType (explore=read-only, plan=read-only+tasks, execute=all minus subagent tools). Background LLM priority. Circuit breaker (2 consecutive errors). Cannot spawn sub-subagents.
- **SubagentManager:** Lifecycle manager — spawn/cancel/cancel_all, max concurrent (default 3), status summary for system prompt injection.
- **Subagent tools (4):** `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents` — registered via factory pattern with structured logging.
- **Plan mode:** `AgentMode` enum (NORMAL/PLANNING), capability-based gating (`mutates_fs`/`executes_shell` blocked in PLANNING), `/plan` slash command (on/off/approve).
- **Backend wiring:** LLMScheduler + SubagentManager created in `_ensure_agent_loop()`, 4 new RPC handlers (`subagent.list`, `subagent.cancel`, `plan.status`, `plan.set`), cancel propagation to subagents, session reset on new/resume/switch.
- **Prompt updates:** Subagent delegation guidance, subagent status injection, plan mode indicator.
- Agent tool baseline: **19 tools** (15 base + 4 subagent tools).
- Slash commands: **17** (16 base + `/plan`).
- Tests: 942 collected, 819 passed, 113 skipped, 0 failed. 30 Sprint 4B tests across 4 files.
- Test artifacts: `docs/qa/test-results/20260214-132120-sprint-4b-rereview-fixes.md`

### 5f) Sprint 4C — Memory + Checkpoints + L2/L3 + Plan Artifact + Go Task Panel

- **MemoryStore:** Episodic memory scoped to project_id. Save/retrieve, Jaccard dedup (0.7 threshold), relevance decay (0.95x per session), context budget for prompt injection, LLM-powered learning via scheduler.
- **CheckpointStore:** Save/restore task state snapshots with transactional rollback. `autocommit=False` params added to `SessionStore.add_message()` and `TaskStore.restore_from_snapshot()` for BEGIN IMMEDIATE transaction boundary.
- **L3Provider:** llama-cpp-python + Outlines wrapper with lazy model loading, generate/generate_structured, graceful ImportError degradation, VRAM cleanup.
- **PlanArtifact:** Export task state as `.hybridcoder/plans/<session-id>.md` with checkboxes, sync checkbox changes back to TaskStore.
- **L2/L3 routing in server:** SEMANTIC_SEARCH → L2 (ContextAssembler + HybridSearch + cache reuse), SIMPLE_EDIT → L3 (constrained gen), fallback to L4.
- **BUG-20 fixed:** `on_task_state` notification emitted from task tool completions AND subagent lifecycle events (spawn/done) via `on_state_change` callback on SubagentManager.
- **Go TUI task panel:** `backendTaskStateMsg`, `TaskStateParams`, `dispatchNotification` handler, `taskpanel.go` renderer, task panel in view between thinking and tool calls. L3 layer indicator added.
- **New commands:** `/memory` (alias: `mem`), `/checkpoint` (alias: `ckpt`). `/plan` extended with `export`/`sync` subcommands.
- Slash commands: **19** (17 + `/memory` + `/checkpoint`).
- Tests: 987 collected, 978 passed, 9 skipped (8 Ollama + 1 OpenRouter rate limit), 0 failed. tree-sitter mandatory in test env, integration tests included by default.
- Test artifacts: `docs/qa/test-results/20260214-164900-phase4-refix-final-clean.md`

## 6) Commands You Actually Need

- Setup:
  - `uv sync --all-extras`
- Main test run:
  - `uv run pytest tests/ -v`
- Lint/typecheck:
  - `uv run ruff check src/ tests/`
  - `uv run mypy src/hybridcoder/`
- **E2E benchmarks:**
  - `uv run python scripts/run_calculator_benchmark.py` — Calculator benchmark
  - `uv run python scripts/e2e/run_scenario.py E2E-BugFix` — BugFix scenario
  - `uv run python scripts/e2e/run_scenario.py E2E-CLI` — CLI scenario
  - `uv run python scripts/e2e/run_scenario.py --list` — Show all scenarios
  - `.\scripts\run_e2e_benchmark.ps1` — PowerShell wrapper (calculator default)
  - `.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-BugFix` — PS wrapper for BugFix
  - `.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-CLI` — PS wrapper for CLI
  - See `TESTING.md` for full guide, or `docs/qa/e2e-benchmark-guide.md` for deep details
- **External benchmarks (requires Docker + Harbor):**
  - `uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite swebench` — SWE-bench pilot
  - `uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench` — Terminal-Bench pilot
  - `uv run python scripts/e2e/external/run_external_pilot.py --help` — All options
  - See `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` for full setup
- Before/after Phase 3 benchmark snapshots:
  - `./scripts/run_phase3_benchmark_snapshot.sh before`
  - `./scripts/run_phase3_benchmark_snapshot.sh after`
- Persist any run output:
  - `./scripts/store_test_results.sh <label> -- <command>`

## 7) Artifact Locations

- Stored run artifacts: `docs/qa/test-results/`
- Phase 3 before/after snapshots: `docs/qa/phase3-benchmarks/`
- Real-life benchmark standards: `docs/qa/real-life-benchmark-standards.md`
- **E2E benchmark guide: `docs/qa/e2e-benchmark-guide.md`**
- **External benchmark runbook: `docs/plan/agentic-benchmarks/external-benchmark-runbook.md`**
- E2E UI reference images: `docs/qa/e2e-tests/calculator-app/`
- E2E sandbox outputs: `sandboxes/`
- Session logs: `logs/<YYYY>/<MM>/<DD>/<HH>/<session[:8]>/` (latest: `logs/latest`)
- Training blobs: `<session-log-dir>/blobs/` (when training logging enabled)

## 8) Known Baseline QA State (as of 2026-02-14, post-Sprint 4C re-review)

- pytest suite: **987 collected**, 978 passed, 9 skipped (8 Ollama + 1 OpenRouter rate limit), 0 failed
- ruff: **0 errors**
- Go tests: all passing
- E2E scenarios: E2E-BugFix, E2E-CLI, E2E-Calculator defined and runnable
- E2E verdict system: PASS (exit 0), FAIL (exit 1), INFRA_FAIL (exit 2)
- Sprint 4A test artifacts: `docs/qa/test-results/sprint-4a-summary.md`
- Bug fix batch artifact: `docs/qa/test-results/20260214-103203-bug-fixes.md` (Codex-approved, Entry 365)
- Sprint 4B test artifact: `docs/qa/test-results/20260214-132120-sprint-4b-rereview-fixes.md`
- Sprint 4C final artifact: `docs/qa/test-results/20260214-164900-phase4-refix-final-clean.md` (978 passed, 0 failed)
- Go build artifact: `docs/qa/test-results/20260214-164329-phase4-go-build.md`
- E2E-Calculator artifact: `docs/qa/test-results/20260214-220725-e2e-react-calculator.md` (86/100)

## 9) Session Start Checklist

1. Read this file and `AGENTS.md`.
2. Check active thread state in `AGENTS_CONVERSATION.MD`.
3. Confirm whether task is plan/doc only or implementation.
4. If implementation: run baseline tests and store artifacts before changes.
5. If Phase 3 work: use the before/after snapshot protocol.
