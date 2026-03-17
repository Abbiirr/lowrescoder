# AutoCode — Requirements & Feature Catalog

> Comprehensive catalog of all features built, planned, current UX issues, and architecture decisions.
> Last updated: 2026-02-17

---

## 1. Project Overview

**AutoCode** — Edge-native AI coding assistant CLI. Local-first, deterministic-first, consumer hardware (8GB VRAM). See `CLAUDE.md` for architecture (4-layer model), design principles, and technology stack.

---

## 2. Features Built (Phase 0-2) — DONE

### 2.1 CLI Commands

| Command | Description | File |
|---------|-------------|------|
| `autocode chat` | Interactive chat REPL (default: inline parallel mode) | `src/autocode/cli.py:142` |
| `autocode ask` | Single question, streamed response | `src/autocode/cli.py:183` |
| `autocode edit` | AI-assisted file editing (stub) | `src/autocode/cli.py:196` |
| `autocode config` | Show/set/check/path for configuration | `src/autocode/cli.py:205` |
| `autocode version` | Show version | `src/autocode/cli.py:255` |

**CLI flags for `chat`:**
- `--verbose / -v` — Enable verbose output
- `--session / -s ID` — Resume a session by ID
- `--tui` — Use fullscreen Textual TUI
- `--alternate-screen` — Alias for `--tui`
- `--legacy` — Use legacy Rich REPL (no agent loop)
- `--parallel / --sequential` — Inline mode: keep prompt active while streaming (default: parallel)

### 2.2 LLM Integration (Layer 4)

| Feature | Status | File |
|---------|--------|------|
| Ollama provider (local) | DONE | `src/autocode/layer4/llm.py:103` |
| OpenRouter provider (cloud dev) | DONE | `src/autocode/layer4/llm.py:237` |
| Streaming text generation | DONE | Both providers |
| Tool calling (function calls) | DONE | `generate_with_tools()` on both |
| Thinking/reasoning token parsing | DONE | `<think>` tag parsing + OpenRouter native reasoning |
| Conversation history management | DONE | `ConversationHistory` class |
| Token budget trimming | DONE | `trim_to_budget()` |
| JSON structured output | DONE | `generate_json()` on both |

### 2.3 Agent System

| Feature | Status | File |
|---------|--------|------|
| Agent loop (LLM ↔ tool cycle) | DONE | `src/autocode/agent/loop.py` |
| Max 10 iterations per turn | DONE | `AgentLoop.MAX_ITERATIONS = 10` |
| Cancellation support | DONE | `AgentLoop.cancel()` |
| System prompt builder | DONE | `src/autocode/agent/prompts.py` |
| Project memory loading (`.autocode/memory.md`) | DONE | `InlineApp._ensure_agent_loop()` |

### 2.4 Tool Registry (19 Tools)

| Tool | Requires Approval | Description |
|------|-------------------|-------------|
| `read_file` | No | Read file contents with optional line range |
| `write_file` | **Yes** | Write/create files (`mutates_fs=True`) |
| `list_files` | No | List files with glob patterns |
| `search_text` | No | Regex search (ripgrep → grep → Python fallback) |
| `run_command` | **Yes** | Execute shell commands (`executes_shell=True`) |
| `ask_user` | No | Ask the user questions with options or free-text |
| `find_references` | No | Find all usages of a symbol across files (Phase 3) |
| `find_definition` | No | Go to definition of a symbol (Phase 3) |
| `get_type_info` | No | Get type annotation for a symbol (Phase 3) |
| `list_symbols` | No | List functions/classes/methods in a file (Phase 3) |
| `search_code` | No | Hybrid BM25 + vector code search (Phase 3) |
| `create_task` | No | Create a task with title and description (Phase 4) |
| `update_task` | No | Update task status/metadata (Phase 4) |
| `list_tasks` | No | List all tasks with status and dependencies (Phase 4) |
| `add_task_dependency` | No | Add a dependency edge between tasks (Phase 4) |
| `spawn_subagent` | No | Spawn a background subagent (explore/plan/execute) (Phase 4) |
| `check_subagent` | No | Check subagent status and retrieve result (Phase 4) |
| `cancel_subagent` | No | Cancel a running subagent (Phase 4) |
| `list_subagents` | No | List all subagents with status (Phase 4) |

Base tools defined in `src/autocode/agent/tools.py`. Task tools in `src/autocode/agent/task_tools.py`. Subagent tools in `src/autocode/agent/subagent_tools.py`.

### 2.5 Approval System

| Feature | Status | File |
|---------|--------|------|
| Three modes: read-only, suggest, auto | DONE | `src/autocode/agent/approval.py` |
| Tool-level approval checking | DONE | `ApprovalManager.needs_approval()` |
| Blocked operation detection | DONE | `is_blocked()`, `is_write_blocked()` |
| Shell enable/disable | DONE | `enable_shell()`, `is_shell_disabled()` |
| Session-level auto-approve tracking | DONE | `InlineApp._session_approved_tools` |
| Arrow-key selector (sequential mode) | DONE | `InlineApp._arrow_select()` |
| Typed y/s/n prompts (parallel mode) | DONE | `_approval_prompt_parallel()` |

### 2.6 Session Management

| Feature | Status | File |
|---------|--------|------|
| SQLite-backed store (WAL mode) | DONE | `src/autocode/session/store.py` |
| Create/list/get/update sessions | DONE | `SessionStore` class |
| Message persistence (user, assistant, tool, system) | DONE | `add_message()`, `get_messages()` |
| Tool call tracking with duration | DONE | `add_tool_call()`, `update_tool_call()` |
| Session compaction (summarize old messages) | DONE | `compact_session()` |
| Auto-titling from first message | DONE | `InlineApp._run_agent()` |

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

### 2.7 Inline REPL (Primary UI)

| Feature | Status | File |
|---------|--------|------|
| Sequential mode (prompt → response → prompt) | DONE | `InlineApp._run_sequential()` |
| Parallel mode (always-on prompt, `patch_stdout(raw=True)`) | DONE | `InlineApp._run_parallel()` |
| Type-ahead buffer (sequential mode) | DONE | `_typeahead_buffer`, `_listen_for_escape()` |
| Message queue (parallel: FIFO, max 10) | DONE | `_parallel_queue` |
| Queue count in status bar | DONE | `_get_status_text()`, `_get_status_rprompt_text()` |
| Cancel generation (Escape / Ctrl+C) | DONE | `_cancel_generation()` |
| Bottom toolbar (model/provider/mode/tokens/edits/files) | DONE | `_get_status_toolbar()` |
| Right prompt (compact status) | DONE | `_get_status_rprompt()` |
| Shift+Tab cycles approval modes | DONE | Key binding in `_create_key_bindings()` |
| Draft stash/restore during approvals | DONE | `_stash_prompt_draft()`, `_restore_prompt_draft()` |
| Pending prompt requests (parallel approvals/ask_user) | DONE | `_PendingPromptRequest` dataclass |
| Rich-formatted streaming output | DONE | `src/autocode/inline/renderer.py` |
| Thinking indicator | DONE | `InlineRenderer.print_thinking_indicator()` |
| Tool call display with diffs | DONE | `InlineRenderer.print_tool_call()` |

### 2.8 Textual TUI (Fullscreen Mode)

| Feature | Status | File |
|---------|--------|------|
| Full-screen Textual app | DONE | `src/autocode/tui/app.py` |
| Chat view widget (scrollable) | DONE | `src/autocode/tui/widgets/chat_view.py` |
| Input bar widget | DONE | `src/autocode/tui/widgets/input_bar.py` |
| Status bar widget | DONE | `src/autocode/tui/widgets/status_bar.py` |
| Approval prompt widget | DONE | `src/autocode/tui/widgets/approval_prompt.py` |

### 2.9 Input Features

| Feature | Status | File |
|---------|--------|------|
| Command history (FileHistory) | DONE | `~/.autocode/history` |
| Hybrid completer (commands + files) | DONE | `src/autocode/inline/completer.py` |
| Conditional completer (`/` and `@` only) | DONE | `ConditionalCompleter` in `app.py` (no dropdown for prose) |
| Auto-suggest (commands + `@` file paths) | DONE | `HybridAutoSuggest` (Python), Go TUI: `textinput.SetSuggestions` |
| Ghost text (grayed-out inline suggestion) | DONE | Go TUI: `textinput.ShowSuggestions` + `CompletionStyle` |
| Tab to accept suggestion | DONE | Go TUI: built-in `textinput.KeyMap.AcceptSuggestion` |
| Autocomplete dropdown (multiple matches) | DONE | Go TUI: `renderCompletionDropdown()` in `view.go` |
| @file reference expansion | DONE | `src/autocode/tui/file_completer.py` |
| Session resume picker (arrow-key) | DONE | Go TUI: `session_picker.go`, reuses `stageAskUser` |
| Slash commands disabled during streaming | DONE | Queued messages treated as plain chat text |

### 2.10 Slash Commands (19 Commands)

| Command | Aliases | Description |
|---------|---------|-------------|
| `/exit` | `/quit`, `/q` | Quit the application |
| `/new` | — | Start a new session |
| `/sessions` | `/s` | List sessions |
| `/resume` | — | Resume a session; shows arrow-key picker when no ID given |
| `/help` | `/h`, `/?` | Show available commands |
| `/model` | `/m` | Show or switch the LLM model |
| `/mode` | `/permissions` | Show or switch approval mode |
| `/compact` | — | Compact session history |
| `/init` | — | Create project memory file |
| `/shell` | — | Enable or disable shell execution |
| `/copy` | `/cp` | Copy response to clipboard |
| `/freeze` | `/scroll-lock` | Toggle auto-scroll |
| `/thinking` | `/think` | Toggle thinking token visibility |
| `/clear` | `/cls` | Clear terminal screen |
| `/index` | — | Rebuild code search index (Phase 3) |
| `/tasks` | `/t` | Show task board (Phase 4) |
| `/plan` | — | Toggle plan mode: on/off/approve (Phase 4) |
| `/memory` | `/mem` | Show learned patterns (Phase 4) |
| `/checkpoint` | `/ckpt` | List/save/restore checkpoints (Phase 4) |

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

- **275 Go + 1022 Python (collected) = 1297+ tests**
- Python: 1015 passed, 7 skipped (integration self-skip), 0 failed
- Go test files (16 files): update, protocol, session_picker, backend, completion, view, commands, askuser, history, approval, e2e, markdown, model, statusbar
- Python test files cover: CLI, agent loop, tools, approval, session store, inline app, inline renderer, inline completer, TUI commands, file tools, config, type-ahead, parallel mode, backend server, parser, router, chunker, embeddings, index, search, repomap, context, new tools, integration router-agent, task store, context engine, task tools, carry-forward fixes, logging, blob store, episode store, event recorder, LLM scheduler, subagent loop/manager, subagent tools, plan mode
- Benchmark tests: deterministic routing (50 queries), L1 latency, search relevance (precision@3), context budget compliance
- Sprint verification tests: `tests/test_sprint_verify.py`
- Integration tests (included by default, self-skip when requirements not met): `tests/integration/`
- Full test catalog: `docs/tests/test_suite.md`
- **Full testing & evaluation guide: `TESTING.md`**

### 2.13 E2E Evaluation System — DONE

Multi-scenario benchmark framework that drives AutoCode autonomously and produces verdicts.

| Component | Status | File |
|-----------|--------|------|
| Calculator benchmark engine (1,888 lines) | DONE | `scripts/run_calculator_benchmark.py` |
| Generic scenario runner | DONE | `scripts/e2e/run_scenario.py` |
| Scenario manifest contract | DONE | `scripts/e2e/scenario_contract.py` |
| Acceptance check runner + scoring | DONE | `scripts/e2e/scoring.py` |
| E2E-BugFix scenario (fix bugs in seeded project) | DONE | `scripts/e2e/scenarios/bugfix.py` |
| E2E-CLI scenario (build CLI tool from scratch) | DONE | `scripts/e2e/scenarios/cli_tool.py` |
| Seed fixture (3 intentional bugs, 5 tests) | DONE | `scripts/e2e/fixtures/bugfix-seed/` |
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
| `/index` slash command | DONE | `src/autocode/tui/commands.py` |
| L1 bypass in backend server (0 tokens, <50ms) | DONE | `src/autocode/backend/server.py` |
| Layer indicator in Go TUI (`[L1]`/`[L2]`/`[L4]`) | DONE | `cmd/autocode-tui/statusbar.go` |
| Context injection in system prompt | DONE | `src/autocode/agent/prompts.py` |
| `layer_used` in `on_done` notification | DONE | `cmd/autocode-tui/protocol.go`, `messages.go`, `backend.go`, `update.go` |

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

> Plan: `docs/plan/phase4-agent-orchestration.md` (v3.2a)

#### Sprint 4A: Core Primitives — DONE (2026-02-14)

| Feature | Status | Description |
|---------|--------|-------------|
| ContextEngine (auto-compaction) | DONE | Token budget (`len//4`), auto-compaction at 75%, tool result truncation (200+100 head/tail) |
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
| CheckpointStore | P1 | 4C | Save/restore agent state with transactional guarantees |
| L2 runtime wiring | P0 | 4C | SEMANTIC_SEARCH → ContextAssembler → layer_used=2 |
| L3 minimal wiring | P1 | 4C | SIMPLE_EDIT → L3Provider → layer_used=3 (L4 fallback) |
| Markdown plan artifact | P1 | 4C | Export/import `.autocode/plans/<session-id>.md` |
| Go TUI task panel | P2 | 4C | JSON-RPC backed task/subagent display |
| `/memory` and `/checkpoint` commands | P2 | 4C | View/save/restore memories and checkpoints |

### 3.2 Phase 5 — Universal Orchestrator: Agent Teams & Multi-Model — PROVISIONAL_LOCKED

> Plan: `docs/plan/phase5-agent-teams.md` (authoritative)
> Lock checklist: `docs/plan/phase5-roadmap-lock-checklist.md`
> Strategy: **"Standalone first, then interact."**

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
| 4.1 | Arrow-key selects in parallel mode | Go TUI stage-based model with `stageApproval`/`stageAskUser` |
| 4.2 | Input not fixed during streaming | Go Bubble Tea fixed input area via inline mode |
| 4.3 | Cancel and message queue | `_cancel_generation()` clears queue |
| 4.4 | Streaming smoothness | Go Bubble Tea 16ms tick batching, `tea.Println()` scrollback |
| 4.5 | `/resume` copy-paste | Arrow-key session picker in Go TUI |
| 4.6 | Shell enablement safety | Scoped to `run_command` tool only |
| 4.7 | Backend shutdown race | Timeout-based wait: 5s grace, fallback kill, 2s drain |
| 4.8 | Malformed JSON-RPC frames | Per-line unmarshal, invalid frames dropped not fatal |

<details>
<summary>Click for detailed root causes and resolutions</summary>

**4.1 Arrow-key selects removed in parallel mode**
Root cause: Nested prompt_toolkit Applications are unsafe while a `PromptSession` is active. Parallel mode replaced arrow-select with typed `y/s/n` responses.
Resolution: Go Bubble Tea TUI uses stage-based model with dedicated `stageApproval` and `stageAskUser` stages. Arrow-key navigation works in all dialogs (approval, ask-user, session picker). 275 tests cover all interaction paths.

**4.2 Input not visually fixed during streaming**
Root cause: `patch_stdout` is line-buffered. Token streaming causes frequent flushes that trigger prompt re-rendering mid-line, producing interleaving.
Resolution: Go Bubble Tea renders a fixed input area at the bottom of the terminal via inline mode. `View()` always includes the input bar. Streaming content displays above it.

**4.3 Cancel and message queue**
Resolution: `_cancel_generation()` now calls `self._parallel_queue.clear()`. Cancel cancels current generation and clears the queue.

**4.4 Streaming smoothness**
Root cause: `patch_stdout`'s `StdoutProxy` line-buffering means tokens appear bursty without explicit flush, but flushing causes prompt interleaving.
Resolution: Go Bubble Tea batches tokens at 16ms tick rate. Plain text streamed in `View()` live area, Glamour renders once on `on_done`, then `tea.Println()` commits to scrollback.

**4.5 `/resume` copy-paste issue**
Root cause: `/resume` without args dumped a plain-text session list requiring copy-paste of UUIDs.
Resolution: Arrow-key session picker added. `/resume` without args shows interactive picker via `stageAskUser`. User navigates with Up/Down, selects with Enter, cancels with Escape.

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

## 5. Architecture Decision: Go Bubble Tea TUI Rewrite

### Why

After extensive research (web search, Claude Code internals analysis, Ink/Bubble Tea/Textual/ANSI scroll region evaluation, and three research documents), the Python inline REPL has fundamental architectural limitations:

1. `patch_stdout` is line-buffered — token streaming interleaves with the prompt
2. Nested prompt_toolkit Applications are unsafe — arrow-key selects can't coexist with an active prompt
3. No true fixed areas — `patch_stdout` simulates a bottom-pinned prompt but flickers during streaming

### How Claude Code Actually Renders

- Uses React + Ink with a **custom differential renderer**
- **Cursor-up-and-redraw** technique (NOT ANSI scroll regions, NOT alternate screen)
- `<Static>` component makes completed messages permanent scrollback
- Only the "live area" (current response + input) gets redrawn per frame
- **Synchronized Output (DEC 2026)** optionally prevents flicker (feature-detected, not required)
- Codex CLI rewrote from Ink to Rust + Ratatui for performance

### Why Go Bubble Tea

- Elm Architecture (Model-Update-View) — clean state management
- **Inline mode is the default** (no alternate screen) — preserves native terminal scrollback (per Entry 146 consensus)
- Scrollback preservation: completed turns committed via `tea.Println()` into native terminal scrollback; Bubble Tea only manages the "live area" (current streaming response + input + status)
- Goroutines make concurrent streaming + input trivial
- Single binary (~10-15MB), zero runtime dependencies
- Cross-platform Windows 10+ support (fixed flickering in v0.26+)
- Proven by OpenCode (production AI coding agent)
- Lip Gloss for styling, Glamour for Markdown rendering, Huh for forms

### Migration Strategy

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
| Unit tests | 500+ passing | **275 Go + 942 Python (collected) = 1217+** |

---

## 7. Technology Stack

| Component | Choice | Status |
|-----------|--------|--------|
| Language | Python 3.11+ | Active |
| Package Manager | uv | Active |
| CLI Framework | Typer + Rich | Active |
| TUI Frontend | **Go + Bubble Tea** | Active |
| Parsing | tree-sitter 0.25.2 | Active |
| Python Semantics | Jedi (cross-file goto, refs, types) | Planned (Phase 5) |
| LSP Client | Deferred (Jedi preferred over multilspy) | Evaluating |
| Vector DB | LanceDB | Active |
| Embeddings | jina-v2-base-code | Active |
| L4 LLM Runtime | LLM Gateway (`http://localhost:4000/v1`) | Active |
| L4 Model | `coding` alias (auto-routed across 9 providers) | Active |
| L3 LLM Runtime | llama-cpp-python + native grammar | Planned (Phase 5) |
| L3 Model | Qwen2.5-Coder-1.5B Q4_K_M | Planned |
