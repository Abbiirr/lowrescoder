# HybridCoder — Requirements & Feature Catalog

> Comprehensive catalog of all features built, planned, current UX issues, and architecture decisions.
> Last updated: 2026-02-07

---

## 1. Project Overview

**HybridCoder** is an edge-native AI coding assistant CLI that achieves Claude Code-level UX while running on consumer hardware (7-11B parameter models, 8GB VRAM, 16GB RAM).

### Core Differentiators

| Aspect | Cloud AI Coders | HybridCoder |
|--------|----------------|-------------|
| LLM Usage | First resort | **Last resort** |
| Resource Requirement | Cloud API / 70B+ models | Local 7B model, 8GB VRAM |
| Latency (simple queries) | 2-5 seconds | <100ms target |
| Privacy | Data sent to cloud | **Fully local** |
| Cost per task | $0.01-$0.50 | $0 after setup |

### 4-Layer Intelligence Architecture

1. **Layer 1 — Deterministic Analysis** (no LLM): Tree-sitter, LSP, static analysis, pattern matching. Target: <50ms, 0 tokens.
2. **Layer 2 — Retrieval & Context** (no generative LLM): AST-aware chunking, BM25 + vector search, project rules. Target: 100-500ms, 0 tokens.
3. **Layer 3 — Constrained Generation** (efficient LLM): Grammar-constrained decoding, small model (1.5B-3B). Target: 500ms-2s, 500-2000 tokens.
4. **Layer 4 — Full Reasoning** (targeted LLM): 7B model for complex edits, architect/editor pattern. Target: 5-30s, 2000-8000 tokens.

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

- **509+ unit tests passing** (as of last Codex run)
- Test files cover: CLI, agent loop, tools, approval, session store, inline app, inline renderer, inline completer, TUI commands, file tools, config, type-ahead, parallel mode
- Sprint verification tests: `tests/test_sprint_verify.py`
- Integration tests (skipped by default): `tests/integration/`

---

## 3. Features Planned (Phase 3-6)

### 3.1 Phase 3 — Code Intelligence (Layer 1)

| Feature | Priority | Description |
|---------|----------|-------------|
| Tree-sitter parsing | P0 | Syntax analysis for Python, JS, Go, Java |
| LSP integration (multilspy) | P0 | Types, references, definitions via Pyright/JDT-LS |
| Static analysis (Semgrep) | P1 | Linting rules, known patterns |
| Pattern matching | P1 | Known refactoring patterns (deterministic) |

### 3.2 Phase 4 — Context & Retrieval (Layer 2)

| Feature | Priority | Description |
|---------|----------|-------------|
| AST-aware code chunking | P0 | Intelligent code splitting for embedding |
| Hybrid search (BM25 + vector) | P0 | LanceDB with jina-v2-base-code embeddings |
| Project rules loading | P1 | `.rules/`, AGENTS.md, CLAUDE.md |
| Repository map generation | P1 | Codebase structure overview |

### 3.3 Phase 5 — Agentic Workflow (Layer 4)

| Feature | Priority | Description |
|---------|----------|-------------|
| Edit system (whole-file + search/replace) | P0 | Reliable code editing |
| Git integration (auto-commit, undo) | P0 | Safety net for edits |
| Shell sandbox | P1 | Secure command execution |
| Compiler feedback loops (LLMLOOP) | P1 | Edit → compile → fix cycle |
| Multi-file planning | P2 | Architect/editor pattern |

### 3.4 Phase 6 — Polish & Benchmarking

| Feature | Priority | Description |
|---------|----------|-------------|
| Custom benchmark suite | P0 | Test agentic task completion |
| Performance profiling | P1 | Memory, latency, token usage |
| Documentation | P2 | User guide, API docs |

### 3.5 Constrained Generation (Layer 3) — Cross-Phase

| Feature | Priority | Description |
|---------|----------|-------------|
| llama-cpp-python + Outlines integration | P1 | Grammar-constrained decoding |
| Qwen2.5-Coder-1.5B model | P1 | 72% HumanEval at 1GB VRAM |
| Structured output (JSON, tool calls) | P1 | Valid syntax guaranteed |

---

## 4. Current UX Issues

### 4.1 Arrow-key selects removed in parallel mode

**Status:** Known regression
**Root cause:** Nested prompt_toolkit Applications are unsafe while a `PromptSession` is active. Parallel mode replaced arrow-select with typed `y/s/n` responses.
**Impact:** UX downgrade for approval prompts — less discoverable, more error-prone.

### 4.2 Input not visually fixed during streaming

**Status:** Known limitation of `patch_stdout`
**Root cause:** `patch_stdout` is line-buffered. Token streaming causes frequent flushes that trigger prompt re-rendering mid-line, producing interleaving (e.g., `Hello❯ who a`).
**Impact:** Input area doesn't feel "pinned" like Claude Code.

### 4.3 Cancel and message queue

**Status:** Fixed
**Resolution:** `_cancel_generation()` now calls `self._parallel_queue.clear()` (lines 446, 518, 581 in `app.py`). Cancel cancels current generation and clears the queue.

### 4.4 Streaming smoothness

**Status:** Known limitation
**Root cause:** `patch_stdout`'s `StdoutProxy` line-buffering means tokens appear bursty without explicit flush, but flushing causes prompt interleaving.
**Impact:** Less smooth streaming compared to Claude Code's differential renderer.

### 4.5 `/resume` copy-paste issue

**Status:** Fixed
**Root cause:** `/resume` without args dumped a plain-text session list requiring copy-paste of UUIDs.
**Resolution:** Arrow-key session picker added (Go TUI). `/resume` without args shows an interactive picker via `stageAskUser` with sentinel `askRequestID == -1`. User navigates with Up/Down, selects with Enter, cancels with Escape. Full session ID sent via `session.resume` RPC.

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
| Unit tests | 500+ passing | **272 Go + 509 Python = 781+ passing** |

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
