# AutoCode — Requirements & Feature Catalog

> Comprehensive catalog of all features built, planned, current UX issues, and architecture decisions.
> Last updated: 2026-04-26

---

## 1. Project Overview

**AutoCode** — Edge-native AI coding assistant CLI. Local-first, deterministic-first, consumer hardware (8GB VRAM). See `CLAUDE.md` for architecture (4-layer model), design principles, and technology stack.

---

## 2. Current Feature Catalog

### 2.1 CLI Commands

| Command | Description | File |
|---------|-------------|------|
| `autocode` | Canonical interactive launch; starts the Rust TUI frontend | `autocode/src/autocode/cli.py` |
| `autocode --mode inline|altscreen` | Override the Rust TUI launch mode for this run | `autocode/src/autocode/cli.py` |
| `autocode --attach HOST:PORT` | Attach the Rust TUI to an already-running backend TCP transport | `autocode/src/autocode/cli.py` |
| `autocode chat` | Back-compatible interactive command; default path also launches the Rust TUI | `autocode/src/autocode/cli.py` |
| `autocode chat --tui` | Fullscreen Textual fallback UI | `autocode/src/autocode/cli.py` |
| `autocode chat --legacy` | Legacy Rich REPL fallback without the agent loop | `autocode/src/autocode/cli.py` |
| `autocode serve --transport stdio|tcp` | Start the backend JSON-RPC server independently | `autocode/src/autocode/cli.py` |
| `autocode ask` | Single question, streamed response | `autocode/src/autocode/cli.py` |
| `autocode edit` | AI-assisted file editing command surface | `autocode/src/autocode/cli.py` |
| `autocode config` | Show/set/check/path for configuration | `autocode/src/autocode/cli.py` |
| `autocode version` | Show version | `autocode/src/autocode/cli.py` |
| `autocode doctor` | Environment and setup diagnostics | `autocode/src/autocode/cli.py` |
| `autocode setup` | Initial setup helper | `autocode/src/autocode/cli.py` |
| `autocode team` | Agent team management/listing surface | `autocode/src/autocode/cli.py` |
| `autocode rename` | Rename the current or selected session | `autocode/src/autocode/cli.py` |

**User-facing launch rule:** prefer bare `autocode`. Use `autocode chat ...` only when documenting a chat-subcommand fallback such as `--tui` or `--legacy`.

### 2.2 LLM Integration (Layer 4)

| Feature | Status | File |
|---------|--------|------|
| Ollama provider (local) | DONE | `src/autocode/layer4/llm.py:103` |
| OpenRouter provider (cloud dev) | DONE | `src/autocode/layer4/llm.py:237` |
| LiteLLM-compatible local gateway path | DONE | `DEFAULT_GATEWAY_API_BASE = "http://localhost:4000/v1"` |
| Streaming text generation | DONE | Both providers |
| Tool calling (function calls) | DONE | `generate_with_tools()` on both |
| Thinking/reasoning token parsing and request gating | DONE | Streaming `<think>` tag parser + OpenRouter native reasoning; `/thinking on|off` gates provider reasoning |
| Conversation history management | DONE | `ConversationHistory` class |
| Token budget trimming | DONE | `trim_to_budget()` |
| JSON structured output | DONE | `generate_json()` on both |

### 2.3 Agent System

| Feature | Status | File |
|---------|--------|------|
| Agent loop (LLM ↔ tool cycle) | DONE | `src/autocode/agent/loop.py` |
| Max 1000 iterations per turn | DONE | `AgentLoop.MAX_ITERATIONS = 1000` |
| Cancellation support | DONE | `AgentLoop.cancel()` |
| System prompt builder | DONE | `src/autocode/agent/prompts.py` |
| Project memory loading (`.autocode/memory.md`) | DONE | Agent factory / backend loop construction via `load_project_memory_content()` |

### 2.4 Tool Registry (38 Tools — 16 Core + 22 Deferred)

| Tool | Requires Approval | Description |
|------|-------------------|-------------|
| `read_file` | No | Read file contents with optional line range |
| `write_file` | **Yes** | Write/create files (`mutates_fs=True`) |
| `edit_file` | **Yes** | Apply targeted text edits (`mutates_fs=True`) |
| `list_files` | No | List files with glob patterns |
| `search_text` | No | Regex search (ripgrep → grep → Python fallback) |
| `run_command` | **Yes** | Execute shell commands (`executes_shell=True`, `interruptible=True`) |
| `tool_search` | No | Discover deferred tool schemas on demand |
| `git_status` | No | Typed read-only git status |
| `git_diff` | No | Typed read-only git diff |
| `git_log` | No | Typed read-only git log |
| `web_fetch` | No | Fetch web content without shelling out to curl/wget |
| `apply_patch` | **Yes** | Transactional multi-file patch application (`mutates_fs=True`) |
| `list_tool_results` | No | List cached tool-call results with IDs and sizes |
| `clear_tool_result` | No | Selectively clear cached tool-call results by ID, tool, age, or all |
| `todo_write` | No | Write/update the session todo list |
| `todo_read` | No | Read the session todo list |
| `ask_user` | No | Ask the user questions with options or free-text |
| `find_references` | No | Find all usages of a symbol across files (Phase 3) |
| `find_definition` | No | Go to definition of a symbol (Phase 3) |
| `get_type_info` | No | Get type annotation for a symbol (Phase 3) |
| `list_symbols` | No | List functions/classes/methods in a file (Phase 3) |
| `lsp_goto_definition` | No | Native LSP go-to-definition |
| `lsp_find_references` | No | Native LSP reference lookup |
| `lsp_get_type` | No | Native LSP type lookup |
| `lsp_symbols` | No | Native LSP symbol listing |
| `search_code` | No | Hybrid BM25 + vector code search (Phase 3) |
| `semantic_search` | No | Vector-only semantic search |
| `clear_tool_results` | No | Bulk/legacy cache-management interface |
| `glob_files` | No | Glob expansion helper |
| `grep_content` | No | Content grep helper |
| `create_task` | No | Create a task with title and description (Phase 4) |
| `update_task` | No | Update task status/metadata; supports `pending`, `in_progress`, and `completed` lifecycle states with backward-transition rejection (Phase 4) |
| `list_tasks` | No | List all tasks with status and dependencies (Phase 4) |
| `add_task_dependency` | No | Add a dependency edge between tasks (Phase 4) |
| `spawn_subagent` | No | Spawn a background subagent (explore/plan/execute) (Phase 4) |
| `check_subagent` | No | Check subagent status and retrieve result (Phase 4) |
| `cancel_subagent` | No | Cancel a running subagent (Phase 4) |
| `list_subagents` | No | List all subagents with status (Phase 4) |

Core tools are listed in `CORE_TOOL_NAMES` and sent to the model by default. Deferred tools are discoverable through `tool_search`. Base tools are defined in `autocode/src/autocode/agent/tools.py`, task tools in `autocode/src/autocode/agent/task_tools.py`, and subagent tools in `autocode/src/autocode/agent/subagent_tools.py`.

### 2.5 Approval System

| Feature | Status | File |
|---------|--------|------|
| Four modes: read-only, suggest, auto, autonomous | DONE | `src/autocode/agent/approval.py` |
| Tool-level approval checking | DONE | `ApprovalManager.needs_approval()` plus hard-block checks for dangerous shell commands and write-tool paths/content |
| Blocked operation detection | DONE | `is_blocked()`, `is_write_blocked()` |
| Shell enable/disable | DONE | `enable_shell()`, `is_shell_disabled()` |
| Backend approval callbacks | DONE | `BackendServer` / `_ServerAppContext` approval callback wiring |
| Frontend approval UI | DONE | Rust TUI approval modal over backend JSON-RPC requests |
| Session-level approval state | DONE | Backend app context and frontend transport session state |

### 2.6 Session Management

| Feature | Status | File |
|---------|--------|------|
| SQLite-backed store (WAL mode) | DONE | `src/autocode/session/store.py` |
| Create/list/get/update sessions | DONE | `SessionStore` class |
| Message persistence (user, assistant, tool, system) | DONE | `add_message()`, `get_messages()` |
| Tool call tracking with duration | DONE | `add_tool_call()`, `update_tool_call()` |
| Session compaction (summarize old messages) | DONE | `compact_session()` |
| Auto-titling from first message | DONE | Backend chat execution / Rust TUI session bootstrap |

### 2.6b Structured Logging & Training Data

| Feature | Status | File |
|---------|--------|------|
| JSON Lines file logging (INFO + DEBUG) | DONE | `src/autocode/core/logging.py` |
| Timestamped session log directories (`YYYY/MM/DD/HH/<session[:8]>/`) | DONE | `session_log_dir()`, `setup_session_logging()` |
| Two-phase logging setup (pre-session → session-specific) | DONE | `setup_logging()` then `setup_session_logging()` |
| `latest` symlink (`.txt` fallback on Windows) | DONE | `_update_latest_pointer()` |
| Training-grade event recorder (opt-in, fail-open) | DONE | `src/autocode/agent/event_recorder.py` |
| Episode/event store (SQLite, retention enforcement) | DONE | `src/autocode/session/episode_store.py` |
| Content-addressed blob store (SHA-256 dedup) | DONE | `src/autocode/core/blob_store.py` |
| TrainingLogConfig (default disabled, explicit opt-in) | DONE | `src/autocode/config.py` |
| SFT/DPO/Eval JSONL export stubs | DONE | `src/autocode/training/exporter.py` |
| DPO provenance events (`human_edit` with draft/edited text) | DONE | `EventRecorder.on_human_edit()` |

### 2.7 Rust TUI (Primary UI)

| Feature | Status | File |
|---------|--------|------|
| Rust Ratatui frontend | DONE | `autocode/rtui/` |
| Bare `autocode` launch | DONE | `autocode/src/autocode/cli.py` |
| Inline default and altscreen opt-in | DONE | `autocode --mode inline|altscreen` and `/tui` |
| Spawn-managed backend mode | DONE | Rust TUI launches a stdio backend server |
| Attach frontend mode | DONE | Rust TUI connects to `autocode serve --transport tcp` via `--attach HOST:PORT` |
| Streaming transcript and status bar | DONE | Rust reducer/rendering pipeline |
| Slash palette and picker overlays | DONE | Rust TUI command/picker surfaces |
| Recovery and approval surfaces | DONE | Rust TUI modal/recovery states |

Historical note: the Python prompt-toolkit inline REPL and the Go Bubble Tea TUI were removed at the Rust M11 cutover on 2026-04-19. The supported interactive frontend is now the Rust TUI.

### 2.8 Textual TUI (Fallback Fullscreen Mode)

| Feature | Status | File |
|---------|--------|------|
| Full-screen Textual app | FALLBACK | `src/autocode/tui/app.py` |
| Chat view widget (scrollable) | DONE | `src/autocode/tui/widgets/chat_view.py` |
| Input bar widget | DONE | `src/autocode/tui/widgets/input_bar.py` |
| Status bar widget | DONE | `src/autocode/tui/widgets/status_bar.py` |
| Approval prompt widget | DONE | `src/autocode/tui/widgets/approval_prompt.py` |

Use `autocode chat --tui` only as a fallback path. New frontend behavior should target the Rust TUI first.

### 2.9 Rust TUI Input Features

| Feature | Status | File |
|---------|--------|------|
| Frecency command history | DONE | `~/.autocode/history.json` |
| Multi-line composer | DONE | Rust TUI composer |
| Bracketed paste handling | DONE | Rust TUI input pipeline |
| Slash autocomplete and command palette | DONE | `/` suggestions and `Ctrl+Shift+P` / palette |
| Model/provider/session pickers | DONE | Rust TUI picker overlays |
| External editor round-trip | DONE | `Ctrl+E` editor flow |
| Approval and ask-user modals | DONE | Rust TUI modal state |
| Native scrollback preservation | DONE | Inline launch mode preserves terminal scrollback |
| Launch-mode preference | DONE | `/tui` / `/screen` command and CLI `--mode` |

### 2.10 Slash Commands (29 Commands)

| Command | Aliases | Description |
|---------|---------|-------------|
| `/exit` | `/quit`, `/q` | Quit the application |
| `/new` | — | Start a new session |
| `/sessions` | `/s` | List sessions |
| `/resume` | — | Resume a session by ID or picker |
| `/help` | `/h`, `/?` | Show available commands |
| `/model` | `/m` | Show or switch the LLM model |
| `/provider` | — | Show, list, or switch the LLM provider |
| `/mode` | `/permissions` | Show or switch approval mode |
| `/tui` | `/screen` | Show or save the default Rust TUI launch mode |
| `/compact` | — | Compact session history |
| `/init` | — | Create project memory file |
| `/shell` | — | Enable or disable shell execution |
| `/copy` | `/cp` | Copy last response, a specific response, or all responses |
| `/freeze` | `/scroll-lock` | Toggle auto-scroll for text selection |
| `/thinking` | `/think` | Toggle thinking token visibility and provider reasoning request gating |
| `/clear` | `/cls` | Clear the terminal screen |
| `/loop` | — | Recurring jobs: `/loop <interval> <payload>`, `/loop list`, `/loop cancel <id>` |
| `/index` | — | Build or rebuild the code search index |
| `/tasks` | `/t` | Show task board |
| `/plan` | — | Plan mode: `/plan on`, `/plan approve`, `/plan off`, `/plan export`, `/plan sync` |
| `/research` | `/comprehend` | Research mode: `/research on`, `/research off`, `/research status` |
| `/build` | — | Build mode: `/build on` (verification required), `/build off` |
| `/review` | — | Review mode: `/review on` (read-only review), `/review off` |
| `/memory` | `/mem` | Show learned patterns |
| `/checkpoint` | `/ckpt` | List or save checkpoints |
| `/undo` | — | Undo by restoring the most recent checkpoint |
| `/diff` | — | Show git diff of changes in the current session |
| `/cost` | `/tokens`, `/usage` | Show token usage and estimated cost for this session |
| `/export` | — | Export conversation to markdown file |

### 2.11 Configuration

| Feature | Status | File |
|---------|--------|------|
| YAML config (`~/.autocode/config.yaml`) | DONE | `src/autocode/config.py` |
| Pydantic model validation | DONE | `AutoCodeConfig` |
| LLM settings (model, provider, api_base, temperature, max_tokens) | DONE | `LLMConfig` |
| UI settings (approval_mode, theme, session_db_path) | DONE | `UIConfig` |
| Shell settings (enabled, allowed_commands, blocked_patterns) | DONE | `ShellConfig` |
| Config check with warnings | DONE | `check_config()` |

### 2.12 Tests

- **Python unit baseline:** `1961 passed` in the latest full unit sweep for this backend tranche.
- **Rust TUI baseline:** `181` Rust tests passing across the Ratatui frontend test suite.
- **Benchmark suite:** maintained separately under `benchmarks/`; do not combine file counts with unit-test totals.
- **Go tests:** no longer applicable because the Go TUI was deleted at the Rust M11 cutover.
- Python coverage includes CLI, backend server/transports, agent loop, tools, approval, sessions, context/search, task tools, subagents, cost, checkpoints, memory, logging, blob store, episode store, event recorder, and LLM scheduling.
- Integration tests under `autocode/tests/integration/` self-skip when required services or credentials are unavailable.
- Full testing and evaluation guide: `autocode/TESTING.md`.

### 2.13 E2E Evaluation System — DONE

Multi-scenario benchmark framework that drives AutoCode autonomously and produces verdicts.

| Component | Status | File |
|-----------|--------|------|
| Calculator benchmark engine | DONE | `benchmarks/run_calculator_benchmark.py` |
| Generic scenario runner | DONE | `benchmarks/e2e/run_scenario.py` |
| Scenario manifest contract | DONE | `benchmarks/e2e/scenario_contract.py` |
| Acceptance check runner + scoring | DONE | `benchmarks/e2e/scoring.py` |
| E2E-BugFix scenario (fix bugs in seeded project) | DONE | `benchmarks/e2e/scenarios/bugfix.py` |
| E2E-CLI scenario (build CLI tool from scratch) | DONE | `benchmarks/e2e/scenarios/cli_tool.py` |
| Seed fixture (3 intentional bugs, 5 tests) | DONE | `benchmarks/e2e/fixtures/bugfix-seed/` |
| Budget enforcement (wall time, tool calls, turns) | DONE | Inline in runner |
| Manifest validation (fail-fast at startup) | DONE | `validate_manifest()` |
| Verdict system (PASS/FAIL/INFRA_FAIL) | DONE | Exit codes 0/1/2 |
| Multi-run, replay, matrix, flake triage modes | DONE | Calculator benchmark |
| Markdown + JSON report generation | DONE | Saved to `docs/qa/test-results/` |

**PR Core baseline:** E2E-Calculator + E2E-BugFix + E2E-CLI.

### 2.14 Phase 3: Code Intelligence (Layer 1 + Layer 2) — DONE

Phase 3 implemented 2026-02-13. All gates passed. 840 Python tests, all Go tests passing, ruff clean, mypy clean.

#### Layer 1: Deterministic Intelligence

| Feature | Status | Files |
|---------|--------|-------|
| Tree-sitter Python parser (mtime LRU cache, 500 entries) | DONE | `src/autocode/layer1/parser.py` |
| Symbol extraction (functions, classes, methods, imports, variables) | DONE | `src/autocode/layer1/symbols.py` |
| Request router (3-stage: regex → features → weighted scoring) | DONE | `src/autocode/core/router.py` |
| Deterministic query handlers (list_symbols, find_def, find_refs, get_imports, show_signature) | DONE | `src/autocode/layer1/queries.py` |
| Syntax/import validation via tree-sitter | DONE | `src/autocode/layer1/validators.py` |

#### Layer 2: Retrieval Intelligence

| Feature | Status | Files |
|---------|--------|-------|
| AST-aware code chunker (function/class boundaries, 200-800 token chunks) | DONE | `src/autocode/layer2/chunker.py` |
| Embedding engine (jina-v2-base-code, 768-dim, lazy-loaded, CPU-only) | DONE | `src/autocode/layer2/embeddings.py` |
| BM25 keyword search with TF-IDF scoring | DONE | `src/autocode/layer2/embeddings.py` |
| LanceDB code index (file-hash invalidation, incremental, gitignore-aware) | DONE | `src/autocode/layer2/index.py` |
| Hybrid search (BM25 + vector + RRF fusion, k=60) | DONE | `src/autocode/layer2/search.py` |
| Repository map generator (ranked symbols, 600-token budget) | DONE | `src/autocode/layer2/repomap.py` |
| Rules loader (CLAUDE.md, .rules/, .cursorrules) | DONE | `src/autocode/layer2/rules.py` |
| Context assembler (5000-token budget, priority-based) | DONE | `src/autocode/core/context.py` |

#### Integration

| Feature | Status | Files |
|---------|--------|-------|
| 5 new agent tools (11 total) | DONE | `src/autocode/agent/tools.py` |
| `/index` slash command | DONE | `autocode/src/autocode/app/commands.py` |
| L1 bypass in backend server (0 tokens, <50ms) | DONE | `src/autocode/backend/server.py` |
| `layer_used` metadata consumed by Rust TUI reducer | DONE | `autocode/src/autocode/backend/schema.py`, `autocode/rtui/src/rpc/protocol.rs`, `autocode/rtui/src/state/reducer.rs` |
| Context injection in system prompt | DONE | `src/autocode/agent/prompts.py` |
| `layer_used` in `on_done` notification | DONE | `autocode/src/autocode/backend/chat.py`, `autocode/src/autocode/backend/schema.py`, `autocode/rtui/src/rpc/protocol.rs` |

#### Gate Results

| Gate | Criteria | Result |
|------|----------|--------|
| Gate 1 | Router accuracy >= 90%, L1 latency < 50ms, 0 tokens | PASS |
| Gate 2 | Search precision@3 > 60%, context <= 5000 tokens, BM25 fallback | PASS |
| Gate 3 | 11 tools, layer indicator, `/index`, 840 tests pass, lint clean, mypy clean | PASS |

#### Deferred (Not Phase 3)

| Feature | Reason |
|---------|--------|
| LSP integration (Sprint 3C) | multilspy early-stage; tree-sitter + grep covers 80%+ |
| `get_diagnostics` tool | Requires LSP |
| Multi-language support | Python-first approach validated |

---

## 3. Features Built & Planned (Phase 4-6)

### 3.1 Phase 4 — Agent Orchestration & Context Intelligence

> Plan: `docs/plan/archive/phase4-agent-orchestration.md` (v3.2a)

#### Sprint 4A: Core Primitives — DONE (2026-02-14)

| Feature | Status | Description |
|---------|--------|-------------|
| ContextEngine (auto-compaction) | DONE | Provider-backed token counting when available, auto-compaction at 75%, adaptive tool-result truncation that preserves code/error/list signals and honors per-tool output budgets |
| Iteration-zero symbol preview | DONE | Workspace bootstrap includes bounded cached Layer 1 symbols for active working-set files only; no cold parse, scan, or repomap generation |
| ToolResultCache management tools | DONE | `list_tool_results` and `clear_tool_result` expose large tool-output cache inspection/clearing to the agent; enabled by `agent.tool_result_cache_enabled` |
| TaskStore (DAG dependencies) | DONE | SQLite-backed CRUD, DAG deps, cycle detection via `graphlib.TopologicalSorter`, snapshot/restore |
| Task LLM tools (create/update/list/dep) | DONE | 4 tools registered via factory pattern with closures over TaskStore |
| `/tasks` slash command | DONE | Shows task board |
| ToolDefinition capability flags | DONE | `mutates_fs`, `executes_shell` on dataclass (ready for 4B plan mode) |
| AgentConfig | DONE | Compaction/subagent/memory settings in `AutoCodeConfig` |
| `ensure_tables()` | DONE | Idempotent Phase 4 table creation |
| `task.list` JSON-RPC | DONE | Backend RPC handler for task listing |
| Carry-forward fixes (CF-1 to CF-4) | DONE | Go badge reset, islice, CodeIndex cache, layer_used assertion |

#### Sprint 4B: Subagents + Scheduling + Plan Mode — DONE (2026-02-14)

| Feature | Status | Description |
|---------|--------|-------------|
| LLMScheduler | DONE | Single-worker asyncio PriorityQueue, foreground/background priority, FIFO within tier |
| SubagentLoop (explore/plan/execute) | DONE | Isolated loops with capability-filtered tool registries, circuit breaker, max iterations |
| SubagentManager | DONE | Spawn/monitor/cancel subagents, max 3 concurrent, status summary for prompt injection |
| Subagent LLM tools (4 tools) | DONE | `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents` via factory pattern |
| Plan mode with capability gating | DONE | `AgentMode` enum, `/plan on/off/approve`, blocks `mutates_fs`/`executes_shell` tools |
| Backend wiring | DONE | LLMScheduler + SubagentManager lifecycle, 4 RPC handlers, cancel propagation, session reset |
| Prompt updates | DONE | Delegation guidance, subagent status injection, plan mode indicator |

#### Sprint 4C: Memory + Checkpoints + L2/L3 + Go Panel — DONE

| Feature | Priority | Sprint | Description |
|---------|----------|--------|-------------|
| MemoryStore (episodic) | P1 | 4C | Relevance-decaying memories extracted from sessions |
| Session consolidation persistence | DONE | 4C/Backend-tightening | Deterministic `SessionConsolidator` learnings can persist through `MemoryStore.save()` with durable filtering and dedup |
| CheckpointStore | P1 | 4C/Backend-tightening | Save/restore task state plus bounded recent messages and assistant tool-call rows with transactional guarantees |
| L2 runtime wiring | P0 | 4C | SEMANTIC_SEARCH → ContextAssembler → layer_used=2 |
| L3 minimal wiring | P1 | 4C | SIMPLE_EDIT → L3Provider → layer_used=3 (L4 fallback) |
| Markdown plan artifact | P1 | 4C | Export/import `.autocode/plans/<session-id>.md` |
| Rust TUI task/subagent surfaces | P2 | 4C | JSON-RPC backed task/subagent display |
| `/memory` and `/checkpoint` commands | P2 | 4C | View/save/restore memories and checkpoints |

### 3.2 Historical Phase 5 — Universal Orchestrator: Agent Teams & Multi-Model — COMPLETE / LEGACY ROADMAP

> **Scope note:** this is the older agent-teams Phase 5 roadmap. It is not the Modular Migration Phase 5 swapability proof.
> **Legacy plan:** `docs/plan/archive/phase5-agent-teams.md`
> **Lock checklist:** `docs/plan/archive/phase5-roadmap-lock-checklist.md`
> **Strategy:** **"Standalone first, then interact."**
> **Current state:** the 5A0-5D agent-teams/delegation substrate is complete as historical product work; remaining active architecture cleanup lives in `modular_migration_todo.md`.
> **Modular Phase 5:** swapability proof is complete separately via `autocode/docs/qa/test-results/20260423-210037-modular-phase5-closeout.md`, with attach/spawn benchmark artifacts `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json` and `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`.

| Sprint | Feature | Priority | Description |
|--------|---------|----------|-------------|
| 5A0 | Quick Wins (diff preview, doctor, token counting, shell hardening) | P0 | Immediate user-facing value before architecture work |
| 5A | Agent Identity + Eval Skeleton (AgentCard, ProviderRegistry) | P0 | First-class agent identity, multi-model routing, eval harness |
| 5B | LLMLOOP — Architect/Editor Pattern | P0 | Edit → compile → fix cycle, tree-sitter + Jedi verification |
| 5C | Evals + AgentBus + Policy Router + Cost Dashboard | P0 | Context quality metrics, reliability soak gates, cost tracking |
| 5D | MCP Server + External Integration (after MVP gate) | P1 | MCP server, config generator, adapter compat matrix |

> Sprint 5E (A2A) has been **dropped** from Phase 5 scope. A2A is not a Phase 5 dependency; reclassified as WATCHLIST for Phase 6+ re-evaluation. See Entry 465-Claude for evidence.

---

## 4. Resolved UX Issues (Phase 2)

All 8 Phase 2 UX issues have been resolved. Summary:

| # | Issue | Resolution |
|---|-------|-----------|
| 4.1 | Arrow-key selects in parallel mode | Rust TUI modal/picker stages for approval, ask-user, and session selection |
| 4.2 | Input not fixed during streaming | Rust TUI fixed composer/footer in inline mode |
| 4.3 | Cancel and message queue | `_cancel_generation()` clears queue |
| 4.4 | Streaming smoothness | Rust reducer/render loop batches streaming and commits completed turns to transcript/scrollback |
| 4.5 | `/resume` copy-paste | Arrow-key session picker in Rust TUI |
| 4.6 | Shell enablement safety | Scoped to `run_command` tool only |
| 4.7 | Backend shutdown race | Timeout-based wait: 5s grace, fallback kill, 2s drain |
| 4.8 | Malformed JSON-RPC frames | Per-line unmarshal, invalid frames dropped not fatal |

<details>
<summary>Click for detailed root causes and resolutions</summary>

**4.1 Arrow-key selects removed in parallel mode**
Root cause: Nested prompt_toolkit Applications are unsafe while a `PromptSession` is active. Parallel mode replaced arrow-select with typed `y/s/n` responses.
Resolution: the Rust TUI uses explicit modal/picker state for approval, ask-user, and session selection. Arrow-key navigation works in dialogs while the composer remains owned by the TUI event loop.

**4.2 Input not visually fixed during streaming**
Root cause: `patch_stdout` is line-buffered. Token streaming causes frequent flushes that trigger prompt re-rendering mid-line, producing interleaving.
Resolution: the Rust TUI renders a fixed composer/footer at the bottom of the terminal in inline mode. Streaming content displays above it without taking over the input area.

**4.3 Cancel and message queue**
Resolution: `_cancel_generation()` now calls `self._parallel_queue.clear()`. Cancel cancels current generation and clears the queue.

**4.4 Streaming smoothness**
Root cause: `patch_stdout`'s `StdoutProxy` line-buffering means tokens appear bursty without explicit flush, but flushing causes prompt interleaving.
Resolution: the Rust reducer/render loop batches streaming into the live transcript state, then `on_done` finalizes the turn for stable transcript/scrollback behavior.

**4.5 `/resume` copy-paste issue**
Root cause: `/resume` without args dumped a plain-text session list requiring copy-paste of UUIDs.
Resolution: Arrow-key session picker added. `/resume` without args shows an interactive picker; user navigates with Up/Down, selects with Enter, and cancels with Escape.

**4.6 Shell enablement safety**
Root cause: `_approval_callback()` called `enable_shell()` for any "Yes, this session" approval regardless of tool type.
Resolution: Shell enablement now scoped to `tool_name == "run_command"` only (Codex Entry 165).

**4.7 Backend shutdown race**
Root cause: Shutdown path used non-blocking `select`, immediately force-killing the process.
Resolution: Real timeout-based wait: orderly shutdown request, 5s grace, fallback process-group kill, 2s goroutine drain (Codex Entry 165).

**4.8 Malformed JSON-RPC frame resilience**
Root cause: A single invalid JSON frame from the backend could terminate the entire TUI session.
Resolution: Newline-framed reads with per-line unmarshal. Invalid frames are dropped with error surfaced to user, not session abort (Codex Entry 170).

</details>

---

## 5. Historical Architecture Decisions

This section preserves earlier architectural decisions that have been superseded.
Keep it for design provenance, not as guidance for current behavior.

### 5.1 Go Bubble Tea TUI Rewrite — SUPERSEDED 2026-04-19

> **Status:** SUPERSEDED by the Rust + Ratatui TUI migration (§1h M11, 2026-04-19).
> Original design rationale preserved below; the Go TUI codebase was deleted at M11.

#### Why

After extensive research (web search, Claude Code internals analysis, Ink/Bubble Tea/Textual/ANSI scroll region evaluation, and three research documents), the Python inline REPL has fundamental architectural limitations:

1. `patch_stdout` is line-buffered — token streaming interleaves with the prompt
2. Nested prompt_toolkit Applications are unsafe — arrow-key selects can't coexist with an active prompt
3. No true fixed areas — `patch_stdout` simulates a bottom-pinned prompt but flickers during streaming

#### How Claude Code Actually Renders

- Uses React + Ink with a **custom differential renderer**
- **Cursor-up-and-redraw** technique (NOT ANSI scroll regions, NOT alternate screen)
- `<Static>` component makes completed messages permanent scrollback
- Only the "live area" (current response + input) gets redrawn per frame
- **Synchronized Output (DEC 2026)** optionally prevents flicker (feature-detected, not required)
- Codex CLI rewrote from Ink to Rust + Ratatui for performance

#### Why Go Bubble Tea

- Elm Architecture (Model-Update-View) — clean state management
- **Inline mode is the default** (no alternate screen) — preserves native terminal scrollback (per Entry 146 consensus)
- Scrollback preservation: completed turns committed via `tea.Println()` into native terminal scrollback; Bubble Tea only manages the "live area" (current streaming response + input + status)
- Goroutines make concurrent streaming + input trivial
- Single binary (~10-15MB), zero runtime dependencies
- Cross-platform Windows 10+ support (fixed flickering in v0.26+)
- Proven by OpenCode (production AI coding agent)
- Lip Gloss for styling, Glamour for Markdown rendering, Huh for forms

#### Migration Strategy

- Go TUI is the **frontend only** — handles rendering, input, and interactive prompts
- Python remains the **backend** — agent loop, tools, LLM providers, session store
- Communication via **JSON-RPC over stdin/stdout** (like LSP)
- Python inline mode stays as `--legacy` fallback

See `docs/archive/plan/go-bubble-tea-migration.md` for the full migration plan.

---

## 6. Target Metrics (MVP)

| Metric | Target | Current |
|--------|--------|---------|
| LLM call reduction | 60-80% vs naive approach | Layer 1-2 built; router + deterministic handlers active |
| Edit success rate (first attempt) | >40% | N/A (edit system not built) |
| Edit success rate (with retry) | >75% | N/A |
| Simple query latency | <500ms | Depends on LLM provider |
| Agentic task completion | >50% on custom test suite | E2E eval system built (3 scenarios: Calculator, BugFix, CLI) |
| Memory usage (idle) | <2GB RAM (stretch: <500MB) | Not profiled |
| Memory usage (inference) | <8GB VRAM | Not profiled |
| Unit tests | 500+ passing | Python unit `1961 passed`; Rust TUI `181`; benchmark suite separate |

---

## 7. Technology Stack

| Component | Choice | Status |
|-----------|--------|--------|
| Language (backend) | Python 3.11+ | Active |
| Package Manager | uv | Active |
| CLI Framework | Typer + Rich | Active |
| TUI Frontend | **Rust + Ratatui 0.29** | Active |
| TUI Terminal Layer | crossterm 0.28 (`event-stream`) | Active |
| TUI PTY Layer | portable-pty 0.8 | Active |
| TUI Async Runtime | tokio 1.x (`full`) | Active |
| TUI Serialization | serde 1.x + serde_json 1.x | Active |
| TUI Logging | tracing 0.1 + tracing-subscriber 0.3 (`env-filter`) | Active |
| Parsing | tree-sitter 0.25.2 | Active |
| Python Semantics | Jedi 0.19.2+ (cross-file goto, refs, types) | Active |
| LSP-style Tools | Jedi-backed `lsp_*` tools, no persistent LSP server required | Active |
| Vector DB | LanceDB | Active |
| Embeddings | jina-v2-base-code | Active |
| L4 LLM Runtime | LLM Gateway (`http://localhost:4000/v1`) | Active |
| L4 Model | `coding` alias (auto-routed) | Active |
| L3 LLM Runtime | llama-cpp-python + Outlines | Optional extra (`autocode[layer3]`) |
| L3 Model | Qwen2.5-Coder-1.5B Q4_K_M | Optional extra |
