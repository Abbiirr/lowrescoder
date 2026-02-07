# Phase 2: TUI Prototype

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 3.5 (inline mode addendum) | Date: 2026-02-05
> Replaces: Original Phase 2 ("Edit System + Git Safety") — deferred to Phase 3
> Consensus: Reached via agent comms

---

## 1. Goal

Build a minimal but usable coding assistant that feels like Claude Code in the terminal, while preserving HybridCoder's layered architecture. Two rendering modes: **inline** (Rich + prompt_toolkit, default) outputs directly to the terminal with native scrollback and text selection; **Textual TUI** (opt-in via `--tui`) provides a fullscreen alternate-screen experience. By the end of Phase 2:

- **Inline mode** (default): Rich + prompt_toolkit REPL with streaming markdown, @file references, and slash commands — see Sprint 2C / `docs/plan/sprint-2c-inline-mode.md`
- **Textual TUI** (opt-in `--tui`): Fullscreen alternate-screen app with streaming markdown chat, @file references, and slash commands
- Session persistence (SQLite) with compaction
- 6 tools with approval gating: read_file, write_file, list_files, search_text, run_command, ask_user
- OpenRouter as acceptance target; Ollama non-blocking/experimental
- Project memory file (`.hybridcoder/memory.md`)
- Performance meeting TUI quality checklist budgets
- BENCH sentinel instrumentation

This is a UX and interaction layer milestone. No Layer 1-2 deterministic engines; no full L3/L4 beyond tool-calling. No git integration. Design stays resource-safe and local-first.

**Implementation status:** Phase 2 is complete. Textual TUI (307 tests) and Sprint 2C inline mode (338 tests) are both implemented. Inline mode (Rich + prompt_toolkit) is the canonical default; Textual TUI is opt-in via `--tui`. See Section 20 and `docs/plan/sprint-2c-inline-mode.md`.

---

## 2. Competitor Analysis

### Strengths Adopted

| Feature | Source | Implementation |
|---------|--------|----------------|
| Approval modes | Codex CLI | read-only / suggest (default) / auto |
| Session persistence | OpenCode | SQLite with sessions, messages, tool_calls |
| @file references | Codex CLI + OpenCode | Fuzzy completion, line ranges |
| Slash commands | OpenCode + Claude Code | 14 commands (minimal, discoverable) |
| Project memory file | OpenCode | `.hybridcoder/memory.md` injected into prompts |
| Tool-calling format | Codex CLI | OpenAI function-calling format |
| Session compaction | OpenCode | LLM summarizes history via /compact |
| BENCH instrumentation | TUI quality checklist | BENCH:READY/PONG/EXIT sentinels |

### Weaknesses Exploited

| Weakness | Competitor | HybridCoder Advantage |
|----------|-----------|----------------------|
| Cloud-only | Codex CLI | Ollama support (Phase 1), local-first design |
| No deterministic layer | All | Layer 1-4 architecture preserved for Phase 3+ |
| Heavy runtimes | OpenCode (Go), Codex (TS) | Pure Python, lightweight, hackable |
| No constrained generation | All | Outlines + llama-cpp-python in Phase 3+ |
| Readline-only TUI | Aider | Full Textual TUI with panels, themes |

---

## 3. Scope

### In Scope

- **Inline mode** (default): Rich + prompt_toolkit REPL — streaming markdown, native scrollback, text selection (Sprint 2C)
- **Textual TUI** (opt-in `--tui`): Fullscreen app with header, chat pane, input bar, status bar
- Streaming markdown rendering of assistant messages (both modes)
- 14 slash commands: /help /exit /new /sessions /resume /model /mode (alias: /permissions) /compact /init /shell /copy (alias: /cp) /freeze (alias: /scroll-lock) /thinking (alias: /think) /clear (alias: /cls)
- @file references with fuzzy completion, line ranges, and tab completion
- SQLite session persistence (3 tables: sessions, messages, tool_calls)
- Session compaction (/compact)
- Session auto-naming — timestamp title on create, auto-update from first user message
- 3 approval modes: read-only / suggest / auto
- 6 tools: read_file, write_file, list_files, search_text, run_command, ask_user
- `run_command` defaults to **disabled** (`shell.enabled: false`); user must opt in; toggleable at runtime via `/shell on|off`
- Interactive approval prompt (ApprovalPrompt widget with Y/n/a keys)
- `ask_user` tool — LLM can ask questions via tool call, routes to OptionSelector or free-text input
- Input history — Up/Down arrow to recall previous messages
- Typing indicator — StatusBar shows "You: typing..." when user types during generation
- Copy/scroll support — PageUp/PageDown bindings, `/copy [all]` command
- Thinking toggle — Ctrl+T/Alt+T to show/hide thinking tokens
- Search backends — ripgrep > grep > Python fallback chain
- Tool calling via OpenRouter (acceptance target)
- Ollama tool calling (non-blocking, best-effort)
- Project memory file (`.hybridcoder/memory.md`)
- BENCH sentinel instrumentation
- Diff preview for write_file (inline in chat)

### Out of Scope (Deferred to Phase 3)

- Git auto-commit, undo, and rollback
- `apply_diff` tool and fuzzy matching
- Layer 1-2 deterministic engines (tree-sitter, LSP, retrieval)
- Multi-step planner and architect/editor split
- Full Ollama tool-calling parity

### Checklist Alignment

The TUI quality checklist (`docs/plan/tui-quality-checklist.md`) includes a "Best-of-Three Target Feature Set" section with aspirational items. The following are explicitly **deferred to Phase 3+** and are NOT part of Phase 2 scope:

- Right-side context panel (plan/to-do, tool calls, diffs)
- Inline plan/to-do list with live progress
- Subagent/task panel
- Transcript export (`/export`)
- File change tracking panel
- `/agents` command (subagent delegation)
- External editor integration (`$EDITOR`)
- UI settings for animations, tooltips, notifications

Phase 2 delivers the core checklist items: performance budgets, BENCH sentinels, approval modes, session persistence, slash commands, and @file references.

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Textual TUI (tui/app.py)                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐                  │
│  │ InputBar  │  │ ChatView  │  │StatusBar │                  │
│  │ (@file,   │  │ (markdown)│  │(model/   │                  │
│  │  history, │  │           │  │ tokens/  │                  │
│  │  tab comp)│  │           │  │ typing)  │                  │
│  └─────┬─────┘  └─────▲─────┘  └──────────┘                  │
│        │              │                                        │
│        │        ┌─────┴──────────┐                            │
│        │        │ ApprovalPrompt │  (Y/n/a keys)              │
│        │        │ OptionSelector │  (ask_user multi/single)   │
│        │        └────────────────┘                            │
│        ▼                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │       Slash Command Router (tui/commands.py, 11 cmds)  │  │
│  └──────────────────┬─────────────────────────────────────┘  │
└─────────────────────┼────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│                 AgentLoop (agent/loop.py)                  │
│  User Message ──► LLM ──► text ──► stream to ChatView    │
│                    └──► tool_call ──► ToolRegistry        │
│                                         │                 │
│                    ┌────────────────────┼──────────┐     │
│                    ▼         ▼          ▼          ▼     │
│               read_file  write_file  run_command  ask_user│
│               list_files search_text                      │
│                    │         │          │          │      │
│                    ▼         ▼          ▼          ▼      │
│               ApprovalManager (agent/approval.py)         │
│               (async approval callbacks via isawaitable)  │
└──────────────────────────────────────────────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  SessionStore    │
            │  (session/)      │
            │  SQLite, 3 tables│
            └──────────────────┘
```

### Design Principles

- TUI is presentation only — no business logic in widgets (except ApprovalPrompt/OptionSelector which handle user interaction)
- AgentLoop is the single source of truth for message flow
- Tools are declarative (JSON Schema) and approval-gated
- Session store writes after every message (crash-safe)
- Everything async — Textual event loop, async LLM streaming
- Async approval callbacks — agent loop supports both sync and async callbacks via `inspect.isawaitable()`

---

## 5. SQLite Session Schema

**Location:** `~/.hybridcoder/sessions.db` (configurable via `tui.session_db_path`)

```sql
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    model       TEXT NOT NULL,
    provider    TEXT NOT NULL,
    project_dir TEXT,
    summary     TEXT,
    token_count INTEGER DEFAULT 0
);

CREATE TABLE messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK(role IN ('system','user','assistant','tool')),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    token_count INTEGER DEFAULT 0
);

CREATE TABLE tool_calls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id    INTEGER REFERENCES messages(id),
    tool_call_id  TEXT,                -- provider-assigned ID for correlating tool results
    tool_name     TEXT NOT NULL,
    arguments     TEXT NOT NULL,
    result        TEXT,
    status        TEXT NOT NULL CHECK(status IN ('pending','approved','denied','completed','error')),
    created_at    TEXT NOT NULL,
    duration_ms   INTEGER
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_tool_calls_session ON tool_calls(session_id, created_at);
CREATE INDEX idx_tool_calls_message ON tool_calls(message_id);
```

---

## 6. Provider Evolution

The existing `LLMProvider` protocol is **extended, not replaced**.

### New Types

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"          # "stop" | "tool_calls"
    usage: dict[str, int] = field(default_factory=dict)
```

### New Method

```python
async def generate_with_tools(
    self,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    stream: bool = True,
) -> AsyncIterator[str | LLMResponse]:
    """Yields str chunks for streaming text; final LLMResponse if tool_calls."""
    ...
```

- **OpenRouterProvider**: Native OpenAI function-calling. Acceptance target. Streams text chunks, yields final `LLMResponse` with tool_calls.
- **OllamaProvider**: Ollama 0.4+ tool API. Non-blocking — if tool-calling fails, fall back to text-only. Prompt-based fallback as last resort. **Important:** When tools are provided, buffer the full response (non-streaming) before yielding `LLMResponse` to avoid partial tool-call payloads. Only stream text-only responses.

---

## 7. Tool System

### 6 Built-in Tools

| Tool | Category | Approval | Description |
|------|----------|----------|-------------|
| `read_file` | file | Never | Read file contents (optional line range) |
| `write_file` | file | suggest: Y/n, auto: auto | Write full file content (shows diff) |
| `list_files` | file | Never | List files matching glob pattern |
| `search_text` | file | Never | Regex search in files (ripgrep > grep > Python fallback) |
| `run_command` | shell | suggest: Y/n, auto: Y/n | Shell command (disabled by default, toggleable via `/shell on\|off`) |
| `ask_user` | interaction | Never | LLM asks user a question; routes to OptionSelector (multi/single select) or free-text input |

### Tool Registration

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]          # JSON Schema
    handler: Callable[..., Awaitable[str]]
    requires_approval: bool = True
    category: str = "file"              # "file" | "shell"

class ToolRegistry:
    def register(self, tool: ToolDefinition) -> None: ...
    def get(self, name: str) -> ToolDefinition | None: ...
    def get_schemas(self) -> list[dict[str, Any]]: ...
    async def execute(self, name: str, arguments: dict) -> str: ...
```

### run_command Safety

- `shell.enabled` defaults to `false` in config
- When enabled: strict allowlist (`ShellConfig.allowed_commands`)
- Blocklist always enforced: `rm -rf`, `sudo`, `curl`, `wget`, `mkfs`, `dd`
- Timeout: default 30s, max 300s
- Output truncated at 10,000 chars

---

## 8. Approval Model

| Mode | Reads | File Writes | Shell |
|------|-------|-------------|-------|
| `read-only` | Auto | Blocked | Blocked |
| `suggest` | Auto | Y/n prompt (ApprovalPrompt widget) | Y/n prompt |
| `auto` | Auto | Auto | Y/n prompt |

**Note:** Shell tools (`run_command`) are disabled entirely unless `shell.enabled=true` in config (or toggled on via `/shell on`), regardless of approval mode. The `ask_user` tool never requires approval — it always routes to the user.

**Approval UI:** The `ApprovalPrompt` widget presents Y/n/a keys inline in the chat. Pressing `a` (accept all) switches the session to auto mode for the remaining tool calls.

```python
class ApprovalMode(Enum):
    READ_ONLY = "read-only"
    SUGGEST = "suggest"
    AUTO = "auto"

class ApprovalManager:
    def __init__(self, mode: ApprovalMode) -> None: ...
    def needs_approval(self, tool: ToolDefinition) -> bool: ...
    def is_blocked(self, tool_name: str, arguments: dict) -> tuple[bool, str]: ...
```

---

## 9. Commands and UX

### Slash Commands (14)

| Command | Aliases | Description |
|---------|---------|-------------|
| `/help` | `/h`, `/?` | Show command list |
| `/exit` | `/quit`, `/q` | Quit the application |
| `/new` | | Start new session |
| `/sessions` | `/s` | List sessions |
| `/resume <id>` | | Resume a session |
| `/model <name>` | `/m` | Show or switch model |
| `/mode <mode>` | `/permissions` | Switch approval mode |
| `/compact` | | Summarize history |
| `/init` | | Create project memory file |
| `/shell on\|off` | | Toggle shell execution at runtime |
| `/copy [N\|all\|last N]` | `/cp` | Copy assistant output to clipboard |
| `/freeze` | `/scroll-lock` | Toggle auto-scroll (TUI) |
| `/thinking` | `/think` | Toggle thinking token visibility |
| `/clear` | `/cls` | Clear the terminal screen |

### @file References

- `@path/to/file.py` — insert full file content
- `@file.py:10-40` — insert lines 10-40
- Tab completion for slash commands and @file references with inline suggestions
- Fuzzy completion on `@` keystroke

### Project Memory

- File: `.hybridcoder/memory.md`
- `/init` creates a short project summary from current directory
- Injected into system prompt (bounded by token budget)

### Keyboard Shortcuts

- **Escape** — Cancel current LLM generation or tool execution. Preserves context.
- **Ctrl+C** — If generation is running, same as Escape. If idle, no-op (TUI stays open).
- **Ctrl+D** — Exit TUI (same as `/exit`).
- **Ctrl+T / Alt+T** — Toggle display of thinking tokens.
- **Up/Down arrows** — Recall previous input messages (input history).
- **PageUp/PageDown** — Scroll chat view.
- In-progress tool calls are cancelled via `asyncio.Task.cancel()`.

### Display Decisions

- **Rendering mode**: Two modes available (see Section 20 for full analysis):
  - **Inline mode (default)**: Rich + prompt_toolkit REPL. Output goes to terminal scrollback, native text selection, no mouse capture. Matches Claude Code/Aider experience.
  - **TUI mode (`--tui`)**: Textual fullscreen app with all widgets. Opt-in via `--tui` flag or `tui.alternate_screen: true` in config.
- **Tool call display**: Collapsible in TUI mode; prefixed status lines in inline mode. Controlled by `show_tool_calls` config.
- **Error surfaces**: Errors display inline in chat with red styling and recovery hints (e.g., "File not found: foo.py — check the path and try again").
- **Diff preview**: Inline in chat flow using syntax-highlighted unified diff (Rich Syntax).

---

## 10. Sprint Breakdown

### Sprint 2A: TUI + Sessions (~1 week)

**Goal:** Replace Rich REPL with Textual TUI. Stream responses. Persist sessions.

| ID | Deliverable | Acceptance |
|----|-------------|------------|
| D2A.1 | Textual app skeleton | Header, chat, input, status bar render |
| D2A.2 | Streaming chat | LLM responses stream with markdown |
| D2A.3 | SQLite session store | Create/list/resume/persist |
| D2A.4 | Basic commands | /exit, /new, /sessions, /resume |
| D2A.5 | BENCH sentinels | READY/PONG/EXIT |

**Exit criteria:**
- [x] `hybridcoder chat` opens Textual TUI
- [x] Responses stream from OpenRouter
- [x] Sessions persist to SQLite and resume
- [x] Startup cold <300ms
- [x] BENCH:READY emitted

### Sprint 2B: Tools + Commands + Polish (~1 week)

**Goal:** Agentic tool loop. Approval gating. @file refs. Remaining commands.

| ID | Deliverable | Acceptance |
|----|-------------|------------|
| D2B.1 | AgentLoop | LLM <-> tool cycle, max 10 iterations, async approval callbacks |
| D2B.2 | 6 tools | read/write/list/search/run_command/ask_user |
| D2B.3 | Approval modes | 3 modes (read-only/suggest/auto), blocked commands rejected |
| D2B.4 | `generate_with_tools()` | Added to both providers |
| D2B.5 | @file references | Fuzzy completion, line ranges, tab completion |
| D2B.6 | Remaining commands | /help /model /mode /compact /init /shell /copy |
| D2B.7 | Diff preview | Inline diff for write_file |
| D2B.8 | Project memory | .hybridcoder/memory.md + /init |
| D2B.9 | ApprovalPrompt + OptionSelector | Interactive approval widget (Y/n/a), multi/single select for ask_user |
| D2B.10 | Session auto-naming | Timestamp on create, auto-update from first user message |
| D2B.11 | Input history + typing indicator | Up/Down recall, "You: typing..." in StatusBar |
| D2B.12 | Thinking toggle | Ctrl+T/Alt+T to show/hide thinking tokens |

**Exit criteria:**
- [x] LLM calls tools, results feed back (including ask_user)
- [x] write_file shows diff preview
- [x] suggest mode blocks unapproved writes (ApprovalPrompt widget)
- [x] run_command disabled by default, works when enabled, toggleable via /shell
- [x] @file references resolve correctly with tab completion
- [x] /compact reduces token count by >50%
- [x] All tests pass (`make test` + `make lint`) — 252 tests at Sprint 2B completion; 307 after v3.5 polish (added /freeze, /copy enhancements, interactive widget tests, thinking token tests); 338 after Sprint 2C (inline mode: renderer, completer, app, protocol tests)

---

## 11. File-by-File Guide

### New Source Files (18)

```
src/hybridcoder/
  tui/                              # Textual TUI
    __init__.py
    app.py                          # HybridCoderApp (main Textual app)
    commands.py                     # SlashCommand registry + 11 handlers
    file_completer.py               # @file fuzzy completion + tab completion
    styles.tcss                     # Textual CSS layout
    widgets/
      __init__.py
      chat_view.py                  # Scrollable markdown chat (PageUp/PageDown)
      input_bar.py                  # Multi-line input + @completion + input history
      status_bar.py                 # Model/mode/tokens/typing indicator display
      approval_prompt.py            # ApprovalPrompt (Y/n/a) + OptionSelector widgets

  session/                          # SQLite persistence
    __init__.py
    store.py                        # SessionStore (3 tables, CRUD, compact, auto-naming)
    models.py                       # DDL + Pydantic row models

  agent/                            # Agentic loop
    __init__.py
    loop.py                         # AgentLoop (LLM <-> tool cycle, async callbacks)
    tools.py                        # ToolRegistry + 6 built-in tools (incl. ask_user)
    prompts.py                      # System prompt, tool descriptions
    approval.py                     # ApprovalManager (3 modes: read-only/suggest/auto)
```

### Files to Modify (4)

| File | Changes |
|------|---------|
| `cli.py` | `chat` command launches Textual TUI; add `--session`, `--shell` options |
| `config.py` | Add `TUIConfig` (approval_mode, session_db_path, etc.) |
| `layer4/llm.py` | Add `generate_with_tools()`, `ToolCall`, `LLMResponse` |
| `pyproject.toml` | Add `textual>=0.89`, `pytest-asyncio>=0.24` to deps |

### Config Extension

```python
class TUIConfig(BaseModel):
    approval_mode: Literal["read-only", "suggest", "auto"] = "suggest"
    session_db_path: str = "~/.hybridcoder/sessions.db"
    max_iterations: int = 10
    show_tool_calls: bool = True

class ShellConfig(BaseModel):
    enabled: bool = False            # NEW: defaults disabled per consensus
    # ... existing fields unchanged
```

---

## 12. Key Implementation Details

### AgentLoop

```python
class AgentLoop:
    MAX_ITERATIONS = 10

    async def run(self, user_message: str, *, on_chunk=None, on_tool_call=None,
                  approval_callback=None, ask_user_callback=None) -> str:
        """One turn: send message, stream response or execute tools, repeat.

        approval_callback and ask_user_callback can be sync or async —
        the loop checks via inspect.isawaitable() and awaits if needed.
        """
        self.session_store.add_message(self.session_id, "user", user_message)
        messages = self._build_messages()

        for _ in range(self.MAX_ITERATIONS):
            tool_calls = []
            full_text = ""
            async for item in self.provider.generate_with_tools(messages, self.tools.get_schemas()):
                if isinstance(item, str):
                    full_text += item
                    if on_chunk: on_chunk(item)
                elif isinstance(item, LLMResponse):
                    tool_calls = item.tool_calls

            if not tool_calls:
                self.session_store.add_message(self.session_id, "assistant", full_text)
                return full_text

            # Execute tools (ask_user routes to OptionSelector/free-text)
            for tc in tool_calls:
                result = await self._execute_tool(tc, on_tool_call)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return full_text
```

### ShellExecutor

```python
class ShellExecutor:
    async def execute(self, command: str, timeout: int | None = None) -> str:
        if not self.config.enabled:
            raise PermissionError("Shell execution is disabled. Set shell.enabled=true in config.")
        # Check blocklist, then allowlist, then execute with timeout
        ...
```

### Diff Preview

```python
def generate_diff(file_path: str, original: str, new: str) -> str:
    """Unified diff for write_file preview."""
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
    ))
```

### Timeouts and Error Handling

- **LLM call timeout**: 120s per `generate_with_tools()` call (configurable). Enforced via `asyncio.wait_for()`.
- **Tool execution timeout**: 30s default for shell, 10s for file operations.
- **Retry strategy**: Exponential backoff for transient provider errors (429, 500, 502, 503). Max 3 retries, base delay 1s.
- **Error display**: Inline in chat — red-styled message with error type and recovery suggestion. No silent failures.
- **Cancellation**: Escape key triggers `asyncio.Task.cancel()` on the active AgentLoop iteration.

---

## 13. Test Strategy

### Test Summary: 475 Total Tests

Tests span unit, benchmark, and sprint verification across all Phase 2 modules. Key test areas:

| Area | Description |
|------|-------------|
| Session store | CRUD: sessions, messages, tool_calls, compact, auto-naming |
| TUI app | Textual pilot: mount, send, stream, BENCH, keyboard shortcuts |
| Inline app | InlineApp REPL, renderer, completer, AppContext protocol |
| Tools | Registration, schemas, 6 tool handlers (incl. ask_user) |
| Agent loop | Text response, tool calls, max iter, errors, async callbacks |
| Approval | 3 modes (read-only/suggest/auto), blocked commands, shell toggle |
| Commands | Dispatch all 14 commands, unknown cmd handling |
| File completer | Fuzzy match, resolve, line ranges, tab completion, invalid path |
| Approval prompt | ApprovalPrompt widget (Y/n/a), OptionSelector (multi/single) |
| Search backends | ripgrep > grep > Python fallback chain |
| Benchmarks | Startup time, idle RSS, keystroke latency |
| Sprint verify | `tests/test_sprint_verify.py` — phase boundary checks |

### Testing Patterns

- Textual: `app.run_test()` with pilot
- SQLite: `tmp_path` fixture for isolated DB
- Agent loop: mock provider yielding canned responses; async approval/ask_user callbacks
- Shell: safe commands only (`echo`, `python --version`)
- Approval prompt: simulated keypress events for Y/n/a

---

## 14. Performance Budgets

From `docs/plan/tui-quality-checklist.md`:

| Metric | Target | Strategy |
|--------|--------|----------|
| Startup cold | <300ms | Lazy imports (defer textual, ollama, openai) |
| Startup warm | <150ms | SQLite WAL mode, cached file list |
| Keystroke echo | <16ms | Textual native event loop |
| UI frame update | <16ms | Textual compositor handles this natively |
| Non-LLM command | <150ms | Slash commands are pure local |
| Local LLM first token | <2s | Ollama direct (non-blocking) |
| Remote LLM first token | <3s | OpenRouter direct |
| Streaming stability | No pauses >250ms | Async I/O, no blocking on UI thread |

### Lightweight + Low-End Benchmarking

**Lightweight constraints (Phase 2):**
- Avoid importing heavy ML stacks (torch/transformers/llama-cpp) in the TUI path.
- Lazy-import provider SDKs (`openai`, `ollama`) only when a chat session starts.
- Keep default install minimal: Textual + core deps; advanced layers remain optional extras.
- No background daemons, indexers, or watchers in Phase 2.

**Low-end baseline definition (for benchmarking):**
- CPU: 2–4 cores (no AVX required), 8 GB RAM, no GPU.
- OS: Windows/macOS/Linux on commodity laptop hardware.
- LLM: OpenRouter only (remote), with local LLM disabled.
- Screen: 1366x768 or similar (ensure layout adapts to small terminals).

**Benchmark matrix (mandatory each sprint):**
- `scripts/bench_tui.py` (startup, ping latency).
- Idle RSS + CPU% captured for 60s after startup.
- Typing latency (keystroke echo) using Textual test pilot.
- Long-session stability: 30-minute idle + 30-minute active typing.

**Profiling toolkit (use as needed):**
- **py-spy** for low-overhead CPU sampling without code changes.
- **Scalene** for combined CPU/memory profiling and hotspots.
- **Memray** for allocation-level memory profiling and leak detection.
- **psutil** for cross-platform RSS/CPU telemetry during benchmarks.

**Regular profiling cadence:**
- Per-sprint: run `bench_tui.py` and record results in `docs/benchmarks/tui/`.
- Monthly or before release: run Scalene + Memray on the TUI startup path.
- Regression gate: if startup or idle RSS regresses >20% from last baseline, open a perf issue.

### BENCH Contract

When `HYBRIDCODER_BENCH=1`:
- `BENCH:READY` — UI ready for input
- `BENCH:PONG` — after `:bench-ping`
- `BENCH:EXIT` — on exit

---

## 15. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| TUI startup too slow | Medium | Medium | Lazy imports, defer DB, profile early |
| OpenRouter tool-calling errors | Medium | High | Strict schema validation, retry, clear errors |
| Ollama tool-calling unreliable | High | Low | Non-blocking; fall back to text-only |
| Session DB lock | Low | Medium | WAL mode, single-writer |
| Small model tool-call quality | High | Medium | Good system prompts, limit to 6 tools |
| Memory bloat | Medium | Medium | /compact, max history, token budget |
| Windows path handling | Medium | Low | pathlib everywhere, test on Windows |

---

## 16. Migration Strategy

### Reused from Phase 1

| Component | File | Status |
|-----------|------|--------|
| `LLMProvider` protocol | `layer4/llm.py` | Extended (add `generate_with_tools`) |
| `OllamaProvider` | `layer4/llm.py` | Extended |
| `OpenRouterProvider` | `layer4/llm.py` | Extended |
| Config system | `config.py` | Extended (add `TUIConfig`) |
| `read_file/write_file/list_files` | `utils/file_tools.py` | Unchanged |
| `EditResult` | `core/types.py` | Unchanged |
| `ShellConfig` | `config.py` | Add `enabled: bool = False` |

### Replaced

| Phase 1 | Phase 2 |
|---------|---------|
| Rich REPL (`_chat_loop`) | Textual TUI (`tui/app.py`) |
| In-memory `ConversationHistory` | SQLite `SessionStore` |
| `console.input()` | Textual `InputBar` |
| Rich `Live` streaming | Textual `ChatView` |

---

## 17. Phase 2 Exit Criteria

All exit criteria have been met. Phase 2 implementation is complete.

- [x] `hybridcoder chat` launches Textual TUI with streaming markdown
- [x] OpenRouter tool calling works end-to-end (acceptance target)
- [x] 6 tools available: read_file, write_file, list_files, search_text, run_command, ask_user
- [x] run_command disabled by default, works when shell.enabled=true, toggleable via /shell on|off
- [x] 3 approval modes function correctly (read-only / suggest / auto)
- [x] Sessions persist to SQLite and are resumable
- [x] Session auto-naming from first user message
- [x] /compact reduces token count by >50%
- [x] @file references work with fuzzy completion, line ranges, and tab completion
- [x] Project memory file (.hybridcoder/memory.md) created by /init
- [x] Startup cold <300ms, keystroke <16ms
- [x] BENCH sentinels work (READY/PONG/EXIT)
- [x] Ollama text streaming works (tool-calling best-effort, not blocking)
- [x] Interactive approval (ApprovalPrompt Y/n/a, OptionSelector for ask_user)
- [x] Input history, typing indicator, copy/scroll, thinking toggle
- [x] 14 slash commands implemented
- [x] 475 total tests pass

---

## 18. Post-Implementation Additions

The following features were added during implementation beyond the original v3.3 plan scope. They are documented here for completeness.

### ask_user Tool

The LLM can ask the user questions via a tool call rather than embedding questions in prose. The tool accepts a `question` string and optional `options` list. When options are provided, the `OptionSelector` widget renders single-select or multi-select UI. Without options, the user gets free-text input. This enables structured decision-making without leaving the chat flow.

### ApprovalPrompt and OptionSelector Widgets

`approval_prompt.py` contains two widgets:
- **ApprovalPrompt** — Renders inline in the chat for tool approval. Accepts Y (approve), n (deny), a (approve all remaining). Pressing `a` upgrades the session to auto mode for subsequent calls.
- **OptionSelector** — Used by `ask_user` tool. Supports single-select and multi-select modes with keyboard navigation.

### Session Auto-Naming

Sessions are created with a timestamp-based title (e.g., "Session 2026-02-05 14:30"). After the first user message, the title is automatically updated to a truncated version of that message, matching Claude Code's behavior. This makes `/sessions` output immediately meaningful.

### Runtime Shell Toggle

`/shell on|off` allows toggling `shell.enabled` at runtime without editing the config file. This complements the `--shell` CLI flag for quick enablement during a session.

### Clipboard and Scroll

`/copy` copies the last assistant response to the clipboard. `/copy all` copies the entire conversation. PageUp/PageDown keybindings enable scrolling through long chat histories.

### Input History

Up/Down arrow keys in the InputBar recall previously sent messages, similar to shell history. History is per-session and not persisted across sessions.

### Typing Indicator

When the user types while the LLM is generating, the StatusBar shows "You: typing..." to acknowledge input is being received without interrupting the stream.

### Thinking Token Toggle

Ctrl+T / Alt+T toggles visibility of thinking/reasoning tokens from models that support them (e.g., Qwen3 thinking mode). Inline mode hides thinking by default; Textual TUI shows it by default (toggleable).

### Search Backend Fallback Chain

The `search_text` tool uses a three-tier fallback: ripgrep (fastest, if installed) > grep (POSIX fallback) > pure Python regex search. This ensures the tool works on any platform without requiring external dependencies.

### Async Approval Callbacks

The AgentLoop accepts `approval_callback` and `ask_user_callback` as always-async callables (`Callable[..., Awaitable[T]]`). Both are always awaited. This simplifies the code (no `inspect.isawaitable()` branching). Tests provide `async` lambdas/functions.

### Shell Enable-on-Approve

When `shell.enabled=False` and the LLM calls `run_command`, the system routes through the approval prompt instead of hard-blocking. The prompt shows "Enable shell and execute: <cmd>". If approved, shell is enabled at runtime and the command executes. This avoids double-prompting and matches user expectations.

### Dynamic System Prompt

The system prompt is rebuilt at the start of each `AgentLoop.run()` call, reflecting current runtime state (shell enabled/disabled, approval mode). This prevents stale refusals after runtime changes.

### Enhanced /copy Command

`/copy` supports multiple forms: `/copy` (last assistant message), `/copy N` (Nth-last assistant message), `/copy all` (all messages), `/copy last N` (last N messages). Uses platform-native clipboard (`clip.exe` on Windows, `pbcopy` on macOS, `xclip`/`xsel` on Linux).

### /freeze Command

`/freeze` (alias `/scroll-lock`) toggles auto-scroll in ChatView. When frozen, new content is mounted but scroll position is not changed, allowing the user to select text with the mouse. `/freeze` again resumes auto-scroll and jumps to bottom. Total: 14 slash commands.

---

## 20. Inline Mode — Rich + prompt_toolkit (Complete)

### User Requirements

> "If it works, if I can keep selecting while scrolling back then it works."
> "2 rendering modes is okay if not too resource heavy."
> "We can include it in 2C."

**Hard requirements:**
- Native mouse text selection must work while scrolling back through terminal history
- Two rendering modes (inline + TUI) are acceptable if the inline mode is lightweight
- Inline mode is the default; Textual TUI is opt-in via `--tui`
- Implementation is Sprint 2C scope (complete — 338 tests passing)

### Problem

Textual's `inline=True` mode does NOT achieve true inline behavior:
- On Windows, inline mode is **not supported** (relies on `termios`, Unix-only)
- Content does not enter terminal scrollback — it's a fixed-height box managed by Textual
- Mouse events are captured by Textual, preventing native text selection
- This differs fundamentally from Claude Code and Aider, where output becomes normal scrollback

### Research Findings

| Tool | UI Stack | Alternate Screen | Mouse Capture | Scrollback | Text Selection |
|------|----------|-----------------|---------------|------------|---------------|
| Claude Code | Custom React/Ink renderer | No | No | Yes | Native |
| Codex CLI | Ratatui + Crossterm (Rust) | Yes | Yes | No | No |
| Aider | Rich + prompt_toolkit | No | No | Yes | Native |
| HybridCoder (current) | Textual inline | No | Yes | No | Via `/copy` |

### Recommended Architecture: Rich + prompt_toolkit

Adopt the **Aider pattern** for the default interaction mode:

```
┌─────────────────────────────────────────────┐
│ Terminal scrollback (native selection works) │
│                                             │
│ > user message                              │
│ [tool] read_file: src/foo.py ✓              │
│ Assistant response (Rich Markdown)          │
│ > another message                           │
│ ...                                         │
├─────────────────────────────────────────────┤
│ prompt_toolkit input (with completion)    > │
└─────────────────────────────────────────────┘
```

**Components:**
- `prompt_toolkit.PromptSession` — async input with completion, history, key bindings
- `prompt_toolkit.patch_stdout()` — streaming output appears above prompt line
- `rich.Console.print(Markdown(...))` — formatted assistant output
- `rich.Live` — streaming chunks during generation
- `rich.Syntax` — diff preview, code blocks
- `rich.Prompt.ask()` or prompt_toolkit input — approval prompts (Y/n/a)

### Feature Mapping

| Feature | Textual TUI | Rich + prompt_toolkit Inline |
|---------|------------|------------------------------|
| Streaming output | `Static.update()` | `rich.Live` or `print()` chunks |
| Approval prompt | `ApprovalPrompt` widget | `rich.Prompt.ask("Allow? [Y/n/a]")` |
| Option selector | `OptionSelector` widget | `prompt_toolkit` radio list or numbered choices |
| @file completion | `InputBar` suggestion | `prompt_toolkit.Completer` |
| Slash commands | `CommandRouter.dispatch()` | Same (reuse) |
| Thinking tokens | `Collapsible` widget | `rich.Console.print()` with dim style, or hidden |
| Diff preview | `Static` + Rich Syntax | `rich.Syntax` directly |
| Copy/scroll | `/copy`, PageUp/PageDown | Native terminal selection + `/copy` |
| Tool call display | `Collapsible` in chat | Prefixed status line: `[tool] name ✓/✗` |
| Session store | SQLite (reuse) | Same (reuse) |
| Agent loop | `AgentLoop` (reuse) | Same (reuse) |

### Implementation Plan

**New files:**
- `src/hybridcoder/inline/__init__.py`
- `src/hybridcoder/inline/app.py` — `InlineApp` class (main REPL loop)
- `src/hybridcoder/inline/completer.py` — prompt_toolkit Completer for / and @
- `src/hybridcoder/inline/renderer.py` — Rich-based output formatting

**Modified files:**
- `src/hybridcoder/cli.py` — Default `chat` command uses `InlineApp`, `--tui` flag for Textual
- `pyproject.toml` — Add `prompt_toolkit>=3.0` dependency

**Reused without changes:**
- `agent/loop.py`, `agent/tools.py`, `agent/approval.py`, `agent/prompts.py`
- `session/store.py`
- `tui/commands.py` (CommandRouter, SlashCommand — refactored with AppContext protocol in Sprint 2C)
- `tui/file_completer.py` (detection + resolution logic)
- `config.py`

### Sprint Plan

**Sprint 2C: Inline Mode (Complete)**

| ID | Deliverable | Acceptance | Status |
|----|------------|------------|--------|
| 2C.1 | `inline/app.py` — REPL loop with `PromptSession` | User can type, get streaming responses | Done |
| 2C.2 | `inline/completer.py` — `/` and `@` completion | Tab-complete works for commands and files | Done |
| 2C.3 | `inline/renderer.py` — Rich output formatting | Messages render as Markdown, tools as status lines | Done |
| 2C.4 | Approval via prompt_toolkit `prompt_async()` | Y/n/a approval works for tool calls | Done |
| 2C.5 | CLI integration — default inline, `--tui` for Textual | Both modes work from `hybridcoder chat` | Done |
| 2C.6 | Tests + AppContext protocol | 31 new tests, AppContext protocol compliance | Done |

**Key implementation details:**
- `AppContext` protocol in `tui/commands.py` decouples all 12 handlers from Textual
- `PromptSession` is lazy-initialized (avoids terminal detection in tests)
- `tui/app.py` gained 8 new AppContext methods (additive, no breaking changes)
- 338 total tests (307 existing + 31 new), ruff clean

**Exit criteria (all met):**
- [x] `hybridcoder chat` opens inline REPL (Rich + prompt_toolkit)
- [x] `hybridcoder chat --tui` opens Textual TUI (existing behavior)
- [x] All existing tests still pass (307+)
- [x] New inline tests pass (31 new)
- [x] Native text selection works in inline mode
- [x] Works on Windows
- [ ] QA matrix P0 items verified manually (pending)

**QA matrix (inline mode validation):**

| OS | Terminal | Priority |
|----|---------|----------|
| Windows | Windows Terminal | P0 |
| Windows | PowerShell (conhost) | P1 |
| macOS | Terminal.app | P0 |
| macOS | iTerm2 | P1 |
| Linux | gnome-terminal | P0 |
| Linux | tmux | P1 |
| Linux | zellij | P2 |

See `docs/plan/sprint-2c-inline-mode.md` for the comprehensive standalone plan.

### Risks

| Risk | Mitigation |
|------|-----------|
| prompt_toolkit async integration complexity | Aider proves it works; follow their pattern |
| Feature parity between two modes | Share AgentLoop, CommandRouter, SessionStore |
| Maintenance burden of two UIs | Inline is simpler (less code); Textual becomes optional power mode |

### References

- `docs/plan/inline-tui-research.md` — Full research document
- Aider `io.py`: Rich + prompt_toolkit pattern reference
- prompt_toolkit docs: https://python-prompt-toolkit.readthedocs.io/
- Claude Code terminal UI: custom React renderer (not replicable, but goals align)

---

## 19. References

- `docs/plan/tui-quality-checklist.md` — Performance budgets
- `docs/codex/openai-codex-cli.md` — Codex CLI research
- `docs/codex/opencode.md` — OpenCode research
- `docs/codex/claude-code.md` — Claude Code research
- `docs/codex/aider.md` — Aider research
- `docs/communication/old/2026-02-05-phase2-scope-negotiation.md` — Scope consensus
- https://github.com/benfred/py-spy — py-spy profiler
- https://github.com/plasma-umass/scalene — Scalene profiler
- https://github.com/bloomberg/memray — Memray profiler
- https://pypi.org/project/psutil/ — psutil telemetry
