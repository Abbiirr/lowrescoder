# HybridCoder — Requirements & Feature Catalog

> Comprehensive catalog of all features built, planned, current UX issues, and architecture decisions.
> Last updated: 2026-02-08

---

## 1. Project Overview

**HybridCoder** — Edge-native AI coding assistant CLI. Local-first, deterministic-first, consumer hardware (8GB VRAM). See `CLAUDE.md` for architecture (4-layer model), design principles, and technology stack.

---

## 2. Features Built (Phase 0-2) — DONE

### 2.1 CLI Commands

| Command | Description | File |
|---------|-------------|------|
| `hybridcoder chat` | Interactive chat REPL (default: inline parallel mode) | `src/hybridcoder/cli.py:142` |
| `hybridcoder ask` | Single question, streamed response | `src/hybridcoder/cli.py:183` |
| `hybridcoder edit` | AI-assisted file editing (stub) | `src/hybridcoder/cli.py:196` |
| `hybridcoder config` | Show/set/check/path for configuration | `src/hybridcoder/cli.py:205` |
| `hybridcoder version` | Show version | `src/hybridcoder/cli.py:255` |

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
| Ollama provider (local) | DONE | `src/hybridcoder/layer4/llm.py:103` |
| OpenRouter provider (cloud dev) | DONE | `src/hybridcoder/layer4/llm.py:237` |
| Streaming text generation | DONE | Both providers |
| Tool calling (function calls) | DONE | `generate_with_tools()` on both |
| Thinking/reasoning token parsing | DONE | `<think>` tag parsing + OpenRouter native reasoning |
| Conversation history management | DONE | `ConversationHistory` class |
| Token budget trimming | DONE | `trim_to_budget()` |
| JSON structured output | DONE | `generate_json()` on both |

### 2.3 Agent System

| Feature | Status | File |
|---------|--------|------|
| Agent loop (LLM ↔ tool cycle) | DONE | `src/hybridcoder/agent/loop.py` |
| Max 10 iterations per turn | DONE | `AgentLoop.MAX_ITERATIONS = 10` |
| Cancellation support | DONE | `AgentLoop.cancel()` |
| System prompt builder | DONE | `src/hybridcoder/agent/prompts.py` |
| Project memory loading (`.hybridcoder/memory.md`) | DONE | `InlineApp._ensure_agent_loop()` |

### 2.4 Tool Registry (6 Tools)

| Tool | Requires Approval | Description |
|------|-------------------|-------------|
| `read_file` | No | Read file contents with optional line range |
| `write_file` | **Yes** | Write/create files |
| `list_files` | No | List files with glob patterns |
| `search_text` | No | Regex search (ripgrep → grep → Python fallback) |
| `run_command` | **Yes** | Execute shell commands (PowerShell on Windows) |
| `ask_user` | No | Ask the user questions with options or free-text |

All tools defined in `src/hybridcoder/agent/tools.py`.

### 2.5 Approval System

| Feature | Status | File |
|---------|--------|------|
| Three modes: read-only, suggest, auto | DONE | `src/hybridcoder/agent/approval.py` |
| Tool-level approval checking | DONE | `ApprovalManager.needs_approval()` |
| Blocked operation detection | DONE | `is_blocked()`, `is_write_blocked()` |
| Shell enable/disable | DONE | `enable_shell()`, `is_shell_disabled()` |
| Session-level auto-approve tracking | DONE | `InlineApp._session_approved_tools` |
| Arrow-key selector (sequential mode) | DONE | `InlineApp._arrow_select()` |
| Typed y/s/n prompts (parallel mode) | DONE | `_approval_prompt_parallel()` |

### 2.6 Session Management

| Feature | Status | File |
|---------|--------|------|
| SQLite-backed store (WAL mode) | DONE | `src/hybridcoder/session/store.py` |
| Create/list/get/update sessions | DONE | `SessionStore` class |
| Message persistence (user, assistant, tool, system) | DONE | `add_message()`, `get_messages()` |
| Tool call tracking with duration | DONE | `add_tool_call()`, `update_tool_call()` |
| Session compaction (summarize old messages) | DONE | `compact_session()` |
| Auto-titling from first message | DONE | `InlineApp._run_agent()` |

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
| Rich-formatted streaming output | DONE | `src/hybridcoder/inline/renderer.py` |
| Thinking indicator | DONE | `InlineRenderer.print_thinking_indicator()` |
| Tool call display with diffs | DONE | `InlineRenderer.print_tool_call()` |

### 2.8 Textual TUI (Fullscreen Mode)

| Feature | Status | File |
|---------|--------|------|
| Full-screen Textual app | DONE | `src/hybridcoder/tui/app.py` |
| Chat view widget (scrollable) | DONE | `src/hybridcoder/tui/widgets/chat_view.py` |
| Input bar widget | DONE | `src/hybridcoder/tui/widgets/input_bar.py` |
| Status bar widget | DONE | `src/hybridcoder/tui/widgets/status_bar.py` |
| Approval prompt widget | DONE | `src/hybridcoder/tui/widgets/approval_prompt.py` |

### 2.9 Input Features

| Feature | Status | File |
|---------|--------|------|
| Command history (FileHistory) | DONE | `~/.hybridcoder/history` |
| Hybrid completer (commands + files) | DONE | `src/hybridcoder/inline/completer.py` |
| Auto-suggest (command completion) | DONE | `HybridAutoSuggest` (Python), Go TUI: `textinput.SetSuggestions` |
| Ghost text (grayed-out inline suggestion) | DONE | Go TUI: `textinput.ShowSuggestions` + `CompletionStyle` |
| Tab to accept suggestion | DONE | Go TUI: built-in `textinput.KeyMap.AcceptSuggestion` |
| Autocomplete dropdown (multiple matches) | DONE | Go TUI: `renderCompletionDropdown()` in `view.go` |
| @file reference expansion | DONE | `src/hybridcoder/tui/file_completer.py` |
| Session resume picker (arrow-key) | DONE | Go TUI: `session_picker.go`, reuses `stageAskUser` |
| Slash commands disabled during streaming | DONE | Queued messages treated as plain chat text |

### 2.10 Slash Commands (14 Commands)

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

### 2.11 Configuration

| Feature | Status | File |
|---------|--------|------|
| YAML config (`~/.hybridcoder/config.yaml`) | DONE | `src/hybridcoder/config.py` |
| Pydantic model validation | DONE | `HybridCoderConfig` |
| LLM settings (model, provider, api_base, temperature, max_tokens) | DONE | `LLMConfig` |
| UI settings (approval_mode, theme, session_db_path) | DONE | `UIConfig` |
| Shell settings (enabled, allowed_commands, blocked_patterns) | DONE | `ShellConfig` |
| Config check with warnings | DONE | `check_config()` |

### 2.12 Tests

- **275 Go + 509 Python = 784+ unit tests passing**
- Go test files (15 files): update, protocol, session_picker, backend, completion, view, commands, askuser, history, approval, e2e, markdown, model
- Python test files cover: CLI, agent loop, tools, approval, session store, inline app, inline renderer, inline completer, TUI commands, file tools, config, type-ahead, parallel mode, backend server
- Sprint verification tests: `tests/test_sprint_verify.py`
- Integration tests (skipped by default): `tests/integration/`
- Full test catalog: `docs/tests/test_suite.md`

---

## 3. Features Planned (Phase 3-6)

### 3.1 Phase 3 — Code Intelligence (Layer 1 + Layer 2)

> Phase 3 consolidates both deterministic analysis (L1) and retrieval/context (L2).
> Structured as 3 gated sub-phases — each gate validates independently.
> See `docs/plan/phase3-final-implementation.md` for authoritative plan.
> Historical docs archived to `docs/archive/`.

#### North Star Outcomes

| Outcome | How Phase 3 Achieves It |
|---------|------------------------|
| **Reduced token cost** | 60-80% of queries answered with 0 LLM tokens via L1 deterministic routing |
| **Reduced latency** | Structural queries in <50ms (vs 2-5s through LLM) |
| **Fewer tool calls** | Router pre-answers "list symbols", "find definition", etc. — LLM never invoked |
| **Better codebase understanding** | Tree-sitter extracts full symbol graph; repo map gives LLM structural context |
| **Better search / RAG** | AST-aware chunking + hybrid BM25/vector search replaces naive grep |
| **Better intellisense** | Deterministic symbol extraction, scope chains, type annotations, import analysis |
| **Improved accuracy** | LLM receives curated context (repo map + search results + rules) instead of raw prompts |

#### Phase 3-Alpha: Deterministic Intelligence (Gate 1)

Sprints 3A + 3B. **This alone is a shippable demo of the core differentiator.**

| Feature | Priority | Description |
|---------|----------|-------------|
| Tree-sitter parser | P0 | Python parsing with mtime cache, <10ms per file, LRU 500 entries |
| Symbol extraction | P0 | Functions, classes, methods, imports, variables with scope chains via QueryCursor API (0.25.x) |
| Request router | P0 | 3-stage classification (regex → feature extraction → weighted scoring), no LLM. Routes 60-80% of queries to L1 |
| Deterministic query handlers | P0 | `list_symbols`, `find_references` (grep), `find_definition`, `get_imports`, `get_signature`, `get_type_info` (AST annotation) |
| Syntax/import validation | P1 | Validate Python syntax and imports via tree-sitter |

**Gate 1 exit:** "list functions in X.py" returns correct results in <50ms with 0 tokens. Router classifies 90%+ of 25 test queries correctly.

#### Phase 3-Beta: Retrieval Intelligence (Gate 2)

Sprints 3D + 3E + 3F. Gives the LLM curated context instead of raw prompts.

| Feature | Priority | Description |
|---------|----------|-------------|
| AST-aware code chunker | P0 | Splits at function/class boundaries, 500-1500 token chunks, scope-aware |
| Embedding engine | P0 | jina-v2-base-code (768-dim), CPU-only, lazy-loaded (~300MB, one-time download) |
| LanceDB code index | P0 | Pydantic `LanceModel` schema, file-hash invalidation, incremental updates, gitignore-aware |
| Hybrid search (BM25 + vector + RRF) | P0 | LanceDB built-in Tantivy FTS + vector search + Reciprocal Rank Fusion. BM25-only fallback when embeddings unavailable |
| Repository map generator | P0 | Ranked symbol summary (query-aware boosting, recency, centrality), 800-token budget |
| Rules loader | P1 | Loads CLAUDE.md, AGENTS.md, `.rules/*.md`, `.cursorrules`, `.hybridcoder/memory.md` |
| Context assembler | P0 | Priority-based 5000-token budget: rules (300) + repo map (600) + chunks (2200) + file (800) + history (800) + buffer (300) |

**Gate 2 exit:** Hybrid search returns relevant results (precision@3 > 60%). Context assembler stays within token budget. Index builds in <30s.

#### Phase 3-Gamma: Integration + Polish (Gate 3)

Sprint 3G. Wires everything into the product.

| Feature | Priority | Description |
|---------|----------|-------------|
| 5 new agent tools | P0 | `find_references`, `find_definition`, `get_type_info`, `list_symbols`, `search_code` (11 total) |
| `/index` slash command | P0 | Manual index rebuild with `--force` option |
| L1 bypass in backend server | P0 | Router intercepts queries before agent loop — deterministic answers never touch LLM |
| Layer indicator in Go TUI | P1 | Status bar shows `[L1]`, `[L2]`, or `[L4]` per response |
| Context injection in system prompt | P0 | Repo map + rules + grounding instruction added to LLM prompts |
| Layer1Config / Layer2Config | P1 | Configurable cache TTL, search top_k, chunk size, token budgets, relevance threshold |

**Gate 3 exit:** All Phase 3 exit criteria pass. 11 tools registered. `make lint` passes.

#### Deferred (Post-Phase 3)

| Feature | Reason | Alternative |
|---------|--------|-------------|
| LSP integration (Sprint 3C) | multilspy v0.0.15 is early-stage; Python backend is Jedi not Pyright (weaker type inference) | Tree-sitter + grep covers 80%+ of use cases |
| `get_diagnostics` tool | Requires LSP (no tree-sitter equivalent) | Deferred with Sprint 3C |
| Multi-language support | Reduce scope risk; validate Python-first | Planned for post-Phase 3 |
| Static analysis (Semgrep) | Not needed for core differentiator | Planned for Phase 5+ |
| Pattern matching (refactoring) | Not needed for core differentiator | Planned for Phase 5+ |

#### Phase 3 Test Targets

| Metric | Target |
|--------|--------|
| New Python tests | ~157 |
| New Go tests | ~5 |
| Total tests (post-Phase 3) | ~671 (509 Python + 157 new + 202 Go + 5 new) |
| Sprint verify tests | `tests/test_sprint_verify.py` Phase 3 section |
| Coverage target | >70% |

### 3.2 Phase 4 — Agentic Workflow (Layer 4)

> L2 features (chunking, search, retrieval, context) moved to Phase 3.
> Phase 4 is now the agentic workflow phase (previously numbered Phase 5).

| Feature | Priority | Description |
|---------|----------|-------------|
| Edit system (whole-file + search/replace) | P0 | Reliable code editing |
| Git integration (auto-commit, undo) | P0 | Safety net for edits |
| Shell sandbox | P1 | Secure command execution |
| Compiler feedback loops (LLMLOOP) | P1 | Edit → compile → fix cycle |
| Multi-file planning | P2 | Architect/editor pattern |

### 3.3 Phase 5 — Polish & Benchmarking

| Feature | Priority | Description |
|---------|----------|-------------|
| Custom benchmark suite | P0 | Test agentic task completion |
| Performance profiling | P1 | Memory, latency, token usage |
| Documentation | P2 | User guide, API docs |

### 3.4 Constrained Generation (Layer 3) — Cross-Phase

| Feature | Priority | Description |
|---------|----------|-------------|
| llama-cpp-python + Outlines integration | P1 | Grammar-constrained decoding |
| Qwen2.5-Coder-1.5B model | P1 | 72% HumanEval at 1GB VRAM |
| Structured output (JSON, tool calls) | P1 | Valid syntax guaranteed |

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

See `docs/plan/go-bubble-tea-migration.md` for the full migration plan.

---

## 6. Target Metrics (MVP)

| Metric | Target | Current |
|--------|--------|---------|
| LLM call reduction | 60-80% vs naive approach | Not measured (Layer 1-2 not built) |
| Edit success rate (first attempt) | >40% | N/A (edit system not built) |
| Edit success rate (with retry) | >75% | N/A |
| Simple query latency | <500ms | Depends on LLM provider |
| Agentic task completion | >50% on custom test suite | N/A (benchmark not built) |
| Memory usage (idle) | <2GB RAM (stretch: <500MB) | Not profiled |
| Memory usage (inference) | <8GB VRAM | Not profiled |
| Unit tests | 500+ passing | **275 Go + 509 Python = 784+ passing** |

---

## 7. Technology Stack

| Component | Choice | Status |
|-----------|--------|--------|
| Language | Python 3.11+ | Active |
| Package Manager | uv | Active |
| CLI Framework | Typer + Rich | Active |
| TUI Frontend | **Go + Bubble Tea** | Active |
| Parsing | tree-sitter 0.25.2 | Planned |
| LSP Client | multilspy (Microsoft) | Planned |
| Vector DB | LanceDB | Planned |
| Embeddings | jina-v2-base-code | Planned |
| L4 LLM Runtime | Ollama | Active |
| L4 Model | Qwen3-8B Q4_K_M | Active |
| L3 LLM Runtime | llama-cpp-python + Outlines | Planned |
| L3 Model | Qwen2.5-Coder-1.5B Q4_K_M | Planned |
