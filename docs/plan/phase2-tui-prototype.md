# Phase 2: TUI Prototype

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 3.3 | Date: 2026-02-05
> Replaces: Original Phase 2 ("Edit System + Git Safety") — deferred to Phase 3
> Consensus: Reached via agent comms

---

## 1. Goal

Build a minimal but usable TUI coding assistant that feels like Claude Code in the terminal, while preserving HybridCoder's layered architecture. By the end of Phase 2:

- A fast Textual TUI with streaming markdown chat, @file references, and slash commands
- Session persistence (SQLite) with compaction
- 5 tools with approval gating: read_file, write_file, list_files, search_text, run_command
- OpenRouter as acceptance target; Ollama non-blocking/experimental
- Project memory file (`.hybridcoder/memory.md`)
- Performance meeting TUI quality checklist budgets
- BENCH sentinel instrumentation

This is a UX and interaction layer milestone. No Layer 1-2 deterministic engines; no full L3/L4 beyond tool-calling. No git integration. Design stays resource-safe and local-first.

---

## 2. Competitor Analysis

### Strengths Adopted

| Feature | Source | Implementation |
|---------|--------|----------------|
| Approval modes | Codex CLI | suggest (default) / auto / read-only |
| Session persistence | OpenCode | SQLite with sessions, messages, tool_calls |
| @file references | Codex CLI + OpenCode | Fuzzy completion, line ranges |
| Slash commands | OpenCode + Claude Code | 9 commands (minimal, discoverable) |
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

- Textual TUI with header, chat pane, input bar, status bar
- Streaming markdown rendering of assistant messages
- 9 slash commands: /help /exit /new /sessions /resume /model /mode (alias: /permissions) /compact /init
- @file references with fuzzy completion and line ranges
- SQLite session persistence (3 tables: sessions, messages, tool_calls)
- Session compaction (/compact)
- 3 approval modes: read-only / suggest / auto
- 5 tools: read_file, write_file, list_files, search_text, run_command
- `run_command` defaults to **disabled** (`shell.enabled: false`); user must opt in
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
┌─────────────────────────────────────────────────────────┐
│                  Textual TUI (tui/app.py)                │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐             │
│  │ InputBar  │  │ ChatView  │  │StatusBar │             │
│  │ (@file)   │  │ (markdown)│  │(model/   │             │
│  │           │  │           │  │ tokens)  │             │
│  └─────┬─────┘  └─────▲─────┘  └──────────┘             │
│        │              │                                   │
│        ▼              │                                   │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Slash Command Router (tui/commands.py)    │  │
│  └──────────────────┬─────────────────────────────────┘  │
└─────────────────────┼────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│                 AgentLoop (agent/loop.py)                  │
│  User Message ──► LLM ──► text ──► stream to ChatView    │
│                    └──► tool_call ──► ToolRegistry        │
│                                         │                 │
│                         ┌───────────────┼──────────┐     │
│                         ▼               ▼          ▼     │
│                    read_file      write_file  run_command │
│                    list_files     search_text             │
│                         │               │          │     │
│                         ▼               ▼          ▼     │
│                    ApprovalManager (agent/approval.py)    │
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

- TUI is presentation only — no business logic in widgets
- AgentLoop is the single source of truth for message flow
- Tools are declarative (JSON Schema) and approval-gated
- Session store writes after every message (crash-safe)
- Everything async — Textual event loop, async LLM streaming

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

### 5 Built-in Tools

| Tool | Category | Approval | Description |
|------|----------|----------|-------------|
| `read_file` | file | Never | Read file contents (optional line range) |
| `write_file` | file | suggest: Y/n, auto: auto | Write full file content (shows diff) |
| `list_files` | file | Never | List files matching glob pattern |
| `search_text` | file | Never | Regex search in files |
| `run_command` | shell | suggest: Y/n, auto: Y/n | Shell command (disabled by default) |

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
| `read-only` | Auto | Denied | Denied |
| `suggest` | Auto | Y/n prompt | Y/n prompt |
| `auto` | Auto | Auto | Y/n prompt (always) |

**Note:** Shell tools (`run_command`) are disabled entirely unless `shell.enabled=true` in config, regardless of approval mode.

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

### Slash Commands (9)

| Command | Aliases | Description |
|---------|---------|-------------|
| `/help` | `/h`, `/?` | Show command list |
| `/exit` | `/quit`, `/q` | Quit TUI |
| `/new` | | Start new session |
| `/sessions` | `/s` | List past sessions |
| `/resume <id>` | | Resume a session |
| `/model <name>` | `/m` | Show or switch model |
| `/mode <mode>` | `/permissions` | Switch approval mode |
| `/compact` | | Summarize history |
| `/init` | | Create/update project memory file |

### @file References

- `@path/to/file.py` — insert full file content
- `@file.py:10-40` — insert lines 10-40
- Fuzzy completion on `@` keystroke

### Project Memory

- File: `.hybridcoder/memory.md`
- `/init` creates a short project summary from current directory
- Injected into system prompt (bounded by token budget)

### Cancel / Interrupt

- **Escape** — Cancel current LLM generation or tool execution. Preserves context.
- **Ctrl+C** — If generation is running, same as Escape. If idle, no-op (TUI stays open).
- **Ctrl+D** — Exit TUI (same as `/exit`).
- In-progress tool calls are cancelled via `asyncio.Task.cancel()`.

### Display Decisions

- **Alternate screen**: Off by default (inline mode) to preserve terminal scrollback. Opt-in via `--alternate-screen` flag or `tui.alternate_screen: true` in config. Aligns with TUI quality checklist.
- **Tool call display**: Use Textual `Collapsible` widget — tool name and status visible, expand to see arguments/result. Controlled by `show_tool_calls` config.
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
- [ ] `hybridcoder chat` opens Textual TUI
- [ ] Responses stream from OpenRouter
- [ ] Sessions persist to SQLite and resume
- [ ] Startup cold <300ms
- [ ] BENCH:READY emitted

### Sprint 2B: Tools + Commands + Polish (~1 week)

**Goal:** Agentic tool loop. Approval gating. @file refs. Remaining commands.

| ID | Deliverable | Acceptance |
|----|-------------|------------|
| D2B.1 | AgentLoop | LLM <-> tool cycle, max 10 iterations |
| D2B.2 | 5 tools | read/write/list/search/run_command |
| D2B.3 | Approval modes | 3 modes, blocked commands rejected |
| D2B.4 | `generate_with_tools()` | Added to both providers |
| D2B.5 | @file references | Fuzzy completion, line ranges |
| D2B.6 | Remaining commands | /help /model /mode /compact /init |
| D2B.7 | Diff preview | Inline diff for write_file |
| D2B.8 | Project memory | .hybridcoder/memory.md + /init |

**Exit criteria:**
- [ ] LLM calls tools, results feed back
- [ ] write_file shows diff preview
- [ ] suggest mode blocks unapproved writes
- [ ] run_command disabled by default, works when enabled
- [ ] @file references resolve correctly
- [ ] /compact reduces token count by >50%
- [ ] All tests pass (`make test` + `make lint`)

---

## 11. File-by-File Guide

### New Source Files (16)

```
src/hybridcoder/
  tui/                              # Textual TUI
    __init__.py
    app.py                          # HybridCoderApp (main Textual app)
    commands.py                     # SlashCommand registry + 9 handlers
    file_completer.py               # @file fuzzy completion
    styles.tcss                     # Textual CSS layout
    widgets/
      __init__.py
      chat_view.py                  # Scrollable markdown chat
      input_bar.py                  # Multi-line input + @completion
      status_bar.py                 # Model/mode/tokens reactive display

  session/                          # SQLite persistence
    __init__.py
    store.py                        # SessionStore (3 tables, CRUD, compact)
    models.py                       # DDL + Pydantic row models

  agent/                            # Agentic loop
    __init__.py
    loop.py                         # AgentLoop (LLM <-> tool cycle)
    tools.py                        # ToolRegistry + 5 built-in tools
    prompts.py                      # System prompt, tool descriptions
    approval.py                     # ApprovalManager (3 modes)
```

### Files to Modify (4)

| File | Changes |
|------|---------|
| `cli.py` | `chat` command launches Textual TUI; add `--session` option |
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

    async def run(self, user_message: str, *, on_chunk=None, on_tool_call=None) -> str:
        """One turn: send message, stream response or execute tools, repeat."""
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

            # Execute tools, append results, continue loop
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

### Test Files (~42 tests across 8 files)

| File | Tests | Description |
|------|-------|-------------|
| `tests/unit/test_session_store.py` | 6 | CRUD: sessions, messages, tool_calls, compact |
| `tests/unit/test_tui_app.py` | 4 | Textual pilot: mount, send, stream, BENCH |
| `tests/unit/test_tools.py` | 6 | Registration, schemas, 5 tool handlers |
| `tests/unit/test_agent_loop.py` | 6 | Text response, tool calls, max iter, errors |
| `tests/unit/test_approval.py` | 6 | 3 modes, blocked commands, shell disabled, shell.enabled=false |
| `tests/unit/test_commands.py` | 5 | Dispatch /help /mode /compact, unknown cmd |
| `tests/unit/test_file_completer.py` | 5 | Fuzzy match, resolve, line ranges, invalid path |
| `tests/unit/test_tui_integration.py` | 4 | E2E with mock provider |

### Testing Patterns

- Textual: `app.run_test()` with pilot
- SQLite: `tmp_path` fixture for isolated DB
- Agent loop: mock provider yielding canned responses
- Shell: safe commands only (`echo`, `python --version`)

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
| Small model tool-call quality | High | Medium | Good system prompts, limit to 5 tools |
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

- [ ] `hybridcoder chat` launches Textual TUI with streaming markdown
- [ ] OpenRouter tool calling works end-to-end (acceptance target)
- [ ] 5 tools available: read_file, write_file, list_files, search_text, run_command
- [ ] run_command disabled by default, works when shell.enabled=true
- [ ] 3 approval modes function correctly (read-only / suggest / auto)
- [ ] Sessions persist to SQLite and are resumable
- [ ] /compact reduces token count by >50%
- [ ] @file references work with fuzzy completion and line ranges
- [ ] Project memory file (.hybridcoder/memory.md) created by /init
- [ ] Startup cold <300ms, keystroke <16ms
- [ ] BENCH sentinels work (READY/PONG/EXIT)
- [ ] Ollama text streaming works (tool-calling best-effort, not blocking)
- [ ] All tests pass (`make test` + `make lint`)

---

## 18. References

- `docs/plan/tui-quality-checklist.md` — Performance budgets
- `docs/codex/openai-codex-cli.md` — Codex CLI research
- `docs/codex/opencode.md` — OpenCode research
- `docs/codex/claude-code.md` — Claude Code research
- `docs/codex/aider.md` — Aider research
- `docs/communication/old/2026-02-05-phase2-scope-negotiation.md` — Scope consensus
