# Sprint 2C: Inline Mode (Rich + prompt_toolkit)

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 1.1 | Date: 2026-02-06
> Parent: Phase 2 TUI Prototype (`docs/plan/phase2-tui-prototype.md` v3.5, Section 20)
> Status: APPROVED (Codex Entry 55, User confirmed, Codex Entry 61 acknowledged)
> Research: `docs/plan/inline-tui-research.md`, `docs/claude/08-inline-tui-research.md`

---

## Table of Contents

1. [Goal](#1-goal)
2. [Background & Problem](#2-background--problem)
3. [Solution: Rich + prompt_toolkit](#3-solution-rich--prompt_toolkit)
4. [Architecture](#4-architecture)
5. [New Files (Detailed)](#5-new-files-detailed)
6. [Modified Files (Detailed)](#6-modified-files-detailed)
7. [Feature Matrix](#7-feature-matrix)
8. [Implementation Steps (Detailed)](#8-implementation-steps-detailed)
9. [QA Matrix](#9-qa-matrix)
10. [Tests (Detailed)](#10-tests-detailed)
11. [Performance Budgets](#11-performance-budgets)
12. [Dual-UI Guardrails](#12-dual-ui-guardrails)
13. [Risks and Mitigations](#13-risks-and-mitigations)
14. [Exit Criteria](#14-exit-criteria)
15. [Implementation Order](#15-implementation-order)
16. [Dependencies on Existing Code](#16-dependencies-on-existing-code)
17. [References](#17-references)

---

## 1. Goal

Build a Rich + prompt_toolkit inline REPL as the **canonical** (default) rendering mode for `hybridcoder chat`. The existing Textual TUI becomes opt-in via `--tui`.

**Outcome:** Users get native terminal text selection, scrollback, and search while retaining all Phase 2 features (agent loop, tools, approval, sessions, slash commands).

**Scope:** 4 new source files, 4 new test files, 3 modified source files, 1 modified test file. ~31 new tests. Target: ~338 total tests.

---

## 2. Background & Problem

### What We Have Now

HybridCoder Phase 2 built a Textual-based TUI (`src/hybridcoder/tui/app.py`) with:
- 12 slash commands (`/exit`, `/new`, `/sessions`, `/resume`, `/help`, `/model`, `/mode`, `/compact`, `/init`, `/shell`, `/copy`, `/freeze`)
- 6 tools (read_file, write_file, list_files, search_text, run_command, ask_user) with approval gating
- SQLite session persistence with WAL mode
- Agent loop (LLM ↔ tool execution cycle, max 10 iterations)
- @file references with fuzzy completion
- Streaming markdown output, thinking tokens, diff previews
- 307 tests passing

### The Problem

The Textual TUI runs in an **alternate screen buffer** by default. Even with `inline=True`, Textual has 3 blocking issues:

| Issue | Impact | Why It Matters |
|-------|--------|---------------|
| **No Windows support** | `inline=True` relies on `termios` (Unix-only) | ~40% of developers use Windows |
| **Content stays in fixed-height box** | Output does NOT enter terminal scrollback | Users can't scroll back through conversation history after it leaves the viewport |
| **Mouse events captured by Textual** | No native text selection | Users can't select/copy text with mouse — must use `/copy` command |

The user's primary requirement: **"If I can keep selecting while scrolling back then it works."**

### What Competitors Do

| Tool | Approach | Scrollback | Text Selection |
|------|----------|-----------|----------------|
| **Claude Code** | Custom React renderer, no alternate screen | Yes (native) | Yes (native) |
| **Aider** | Rich + prompt_toolkit, no alternate screen | Yes (native) | Yes (native) |
| **Codex CLI** (Rust) | Ratatui fullscreen with `--no-alt-screen` toggle | Configurable | Configurable |
| **OpenCode** | Bubble Tea fullscreen | No | Via clipboard |
| **HybridCoder** (current) | Textual fullscreen | No | Via `/copy` only |

Claude Code and Aider both render to stdout — content becomes terminal scrollback naturally. This is the UX users expect.

### Why Not Just Config Toggles?

Codex CLI's approach (`tui.alternate_screen = auto|always|never`) was considered but doesn't work for Textual because the underlying framework always captures the terminal. Even `inline=True` uses a fixed-height box, not real scrollback. The problem is at the framework level, not the config level.

---

## 3. Solution: Rich + prompt_toolkit

### The Aider Pattern

Aider (the most popular open-source AI coding assistant, ~100K+ stars) uses a proven pattern:

1. **`prompt_toolkit.PromptSession`** — Handles all input: async readline, tab completion, history, multi-line editing, key bindings
2. **`prompt_toolkit.patch_stdout()`** — Ensures output printed during input doesn't corrupt the prompt line
3. **`rich.Console.print()`** — All output goes through Rich for formatting: Markdown, syntax highlighting, tables, panels
4. **`rich.Live`** (optional) — For live-updating sections during streaming

Everything prints to stdout → enters terminal scrollback → native text selection works → terminal search (Ctrl+F) works → scrollback persists.

### How prompt_toolkit Works

prompt_toolkit is a Python library for building interactive command-line applications. Key concepts:

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory

# Create a session (persistent across prompts)
session = PromptSession(
    history=FileHistory("~/.hybridcoder/history"),
    completer=my_completer,          # Tab completion
    multiline=False,                  # Enter submits (not newline)
    enable_history_search=True,       # Ctrl+R searches history
)

# Async REPL loop
async def main():
    while True:
        text = await session.prompt_async(">>> ")
        await handle(text)
```

**Note on `patch_stdout()`:** prompt_toolkit provides a `patch_stdout()` context manager that protects the prompt line from concurrent output. HybridCoder intentionally omits it because: (a) the REPL is sequential — it awaits the agent response, then awaits the next prompt, so there is no concurrent output during the prompt; and (b) `patch_stdout()` was found to corrupt Rich's ANSI escape sequences on Windows, producing garbled output. Since there is no concurrency to guard against, removing it is both correct and necessary for cross-platform compatibility.

### How Rich Works

Rich is already a dependency (used by Typer). Key features we'll use:

```python
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel

console = Console()

# Markdown rendering
console.print(Markdown("# Hello\n\nThis is **bold** and `code`."))

# Syntax-highlighted diff
diff_text = "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,3 @@\n-old line\n+new line"
console.print(Syntax(diff_text, "diff", theme="monokai"))

# Tables
table = Table(title="Sessions")
table.add_column("ID")
table.add_column("Title")
table.add_row("abc123", "Fix login bug")
console.print(table)

# Styled text
console.print("[bold green]Tool:[/] read_file [green]✓[/]")
console.print("[dim italic]Thinking...[/]")
```

### Visual Layout

```
Terminal window (normal scrollback buffer)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│ HybridCoder v0.3.0 | Model: qwen3-8b | Mode: suggest       │
│ Type /help for commands, Ctrl+D to exit                     │
│                                                             │
│ > Tell me about this project                                │  ← user message
│                                                             │
│ [tool] read_file: README.md ✓                               │  ← tool status
│ [tool] list_files: src/ ✓                                   │  ← tool status
│                                                             │
│ # HybridCoder                                               │  ← Rich Markdown
│                                                             │
│ This is a local-first AI coding assistant...                │
│                                                             │
│ > /sessions                                                 │  ← slash command
│                                                             │
│ ┌────┬───────────────────┬─────────────────────┐           │  ← Rich Table
│ │ ID │ Title             │ Updated             │           │
│ ├────┼───────────────────┼─────────────────────┤           │
│ │ 1  │ Fix login bug     │ 2026-02-06 10:30    │           │
│ └────┴───────────────────┴─────────────────────┘           │
│                                                             │
│ > ▌                                                         │  ← prompt_toolkit input
└─────────────────────────────────────────────────────────────┘
  ↑ All of this is in terminal scrollback — scroll up with mouse/keyboard
  ↑ Select text with mouse — it works natively
  ↑ Ctrl+F terminal search — it works natively
```

---

## 4. Architecture

### Rendering Mode Decision

| Mode | Invocation | Framework | Use Case |
|------|-----------|-----------|----------|
| **Inline** (canonical) | `hybridcoder chat` | Rich + prompt_toolkit | Default. Native terminal behavior. |
| **Textual TUI** (opt-in) | `hybridcoder chat --tui` | Textual | Power mode. Interactive widgets. |

**Inline is canonical.** New user-visible features land in inline first. Textual gets features only when parity is explicitly required.

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI (cli.py)                            │
│           Default → InlineApp      --tui → HybridCoderApp       │
└──────────┬────────────────────────────────────┬─────────────────┘
           │                                    │
┌──────────▼───────────┐              ┌─────────▼──────────┐
│   inline/app.py      │              │   tui/app.py       │
│   InlineApp          │              │   HybridCoderApp   │
│   (async REPL loop)  │              │   (Textual App)    │
│                      │              │                    │
│   Uses:              │              │   Uses:            │
│   - prompt_toolkit   │              │   - Textual        │
│   - InlineRenderer   │              │   - ChatView       │
│   - HybridCompleter  │              │   - InputBar       │
└──────────┬───────────┘              └─────────┬──────────┘
           │                                    │
           │  Both implement AppContext protocol │
           │                                    │
           │  ┌─────────────────────────────┐   │
           └──►     Shared Backend          ◄───┘
              │                             │
              │  agent/loop.py     — AgentLoop (LLM ↔ tool cycle)      │
              │  agent/tools.py    — ToolRegistry + 6 tool handlers    │
              │  agent/approval.py — ApprovalManager (3 modes)         │
              │  agent/prompts.py  — System prompt builder             │
              │  session/store.py  — SQLite with WAL mode              │
              │  tui/commands.py   — CommandRouter + 12 slash commands  │
              │  tui/file_completer.py — @file detection + expansion   │
              │  config.py         — HybridCoderConfig (Pydantic)      │
              │  layer4/llm.py     — Ollama + OpenRouter providers     │
              └─────────────────────────────┘
```

### Shared Backend — Already Decoupled

These components have **zero Textual imports** and work with any frontend:

| Component | File | Key Interface | Notes |
|-----------|------|---------------|-------|
| **AgentLoop** | `agent/loop.py` | `async run(msg, *, on_chunk, on_thinking_chunk, on_tool_call, approval_callback, ask_user_callback) -> str` | Accepts callbacks for all I/O — the inline app provides Rich-based callbacks |
| **ToolRegistry** | `agent/tools.py` | `register(tool)`, `get(name)`, `get_schemas_openai_format()` | Holds 6 tools with JSON Schema parameters |
| **ApprovalManager** | `agent/approval.py` | `needs_approval(tool)`, `is_blocked(name, args)`, `enable_shell()` | 3 modes: read-only, suggest, auto |
| **SessionStore** | `session/store.py` | `create_session()`, `add_message()`, `get_messages()`, `compact_session()` | SQLite with WAL, 3 tables |
| **file_completer** | `tui/file_completer.py` | `detect_at_references(text)`, `expand_references(text, root)`, `fuzzy_complete(partial, root)` | Pure utility functions |
| **CommandRouter** | `tui/commands.py` | `register(cmd)`, `dispatch(text)`, `get_all()` | Framework-agnostic routing |
| **LLM Providers** | `layer4/llm.py` | `generate_with_tools(messages, tools, *, on_chunk, on_thinking_chunk)` | Ollama + OpenRouter |
| **Config** | `config.py` | `load_config()` → `HybridCoderConfig` | Pydantic models, YAML config |

### The Only Coupling Point: Command Handlers

The slash command handlers in `tui/commands.py` currently take `HybridCoderApp` as their first argument:

```python
# Current — coupled to Textual
async def _handle_help(app: HybridCoderApp, args: str) -> None:
    chat = app.query_one("#chat-view", ChatView)  # Textual-specific!
    chat.add_message("system", help_text)
```

Sprint 2C introduces an `AppContext` protocol so handlers work with both apps:

```python
# New — framework-agnostic
async def _handle_help(app: AppContext, args: str) -> None:
    app.add_system_message(help_text)  # Works for both InlineApp and HybridCoderApp
```

---

## 5. New Files (Detailed)

### 5.1 `src/hybridcoder/inline/__init__.py`

```python
"""Inline mode: Rich + prompt_toolkit REPL."""

from hybridcoder.inline.app import InlineApp

__all__ = ["InlineApp"]
```

### 5.2 `src/hybridcoder/inline/renderer.py` — InlineRenderer

**Purpose:** Encapsulate all terminal output. Makes the inline app testable (capture console output to a string buffer in tests).

**Full interface:**

```python
from __future__ import annotations

import difflib
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table


class InlineRenderer:
    """Rich-based terminal output for inline mode."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._stream_buffer: list[str] = []

    # --- Startup/shutdown ---

    def print_welcome(self, model: str, provider: str, mode: str) -> None:
        """Print startup banner with model, provider, approval mode."""
        self.console.print(
            f"[bold]HybridCoder[/bold] | Model: {model} | Provider: {provider} | Mode: {mode}"
        )
        self.console.print("[dim]Type /help for commands, Ctrl+D to exit[/dim]")
        self.console.print()

    def print_goodbye(self) -> None:
        """Print exit message."""
        self.console.print("[dim]Goodbye.[/dim]")

    # --- Messages ---

    def print_user_message(self, text: str) -> None:
        """Print user message with "> " prefix."""
        self.console.print(f"[bold green]>[/bold green] {text}")
        self.console.print()

    def print_assistant_message(self, content: str) -> None:
        """Print completed assistant response as Rich Markdown."""
        self.console.print(Markdown(content))
        self.console.print()

    def print_system(self, message: str) -> None:
        """Print system message (command output, errors, info)."""
        self.console.print(f"[yellow]{message}[/yellow]")

    # --- Tool calls ---

    def print_tool_call(self, tool_name: str, status: str, result: str = "") -> None:
        """Print tool call status line.

        Examples:
            [tool] read_file: src/main.py ✓
            [tool] run_command ✗ Permission denied
        """
        if status in ("completed", "success"):
            icon = "[green]✓[/green]"
        elif status in ("error", "blocked"):
            icon = "[red]✗[/red]"
        else:
            icon = "[yellow]…[/yellow]"

        line = f"[dim]\\[tool][/dim] {tool_name} {icon}"
        if result:
            line += f" [dim]{result[:100]}[/dim]"
        self.console.print(line)

    # --- Thinking tokens ---

    def print_thinking(self, content: str) -> None:
        """Print thinking/reasoning tokens in dim italic style."""
        self.console.print(f"[dim italic]{content}[/dim italic]")

    # --- Diffs ---

    def print_diff(self, old_content: str, new_content: str, file_path: str) -> None:
        """Print unified diff with syntax highlighting."""
        diff_lines = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        diff_text = "".join(diff_lines)
        if diff_text:
            self.console.print(Syntax(diff_text, "diff", theme="monokai"))
        else:
            self.console.print("[dim]No changes.[/dim]")

    # --- Approval context ---

    def print_approval_context(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Print tool details before showing approval prompt."""
        import json
        self.console.print(f"[bold yellow]Tool:[/bold yellow] {tool_name}")
        self.console.print(f"[dim]{json.dumps(arguments, indent=2)}[/dim]")

    # --- Sessions table ---

    def print_sessions_table(self, sessions: list[Any]) -> None:
        """Print sessions list as Rich Table."""
        table = Table(title="Sessions")
        table.add_column("#", style="dim")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Updated")
        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i),
                s.id[:8],
                s.title or "(untitled)",
                s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "",
            )
        self.console.print(table)

    # --- Streaming ---

    def start_streaming(self) -> None:
        """Begin streaming mode. Call stream_chunk() for each token."""
        self._stream_buffer = []

    def stream_chunk(self, chunk: str) -> None:
        """Print a streaming chunk (raw text, no formatting)."""
        self._stream_buffer.append(chunk)
        self.console.print(chunk, end="", highlight=False)

    def end_streaming(self) -> str:
        """End streaming. Returns full accumulated content."""
        content = "".join(self._stream_buffer)
        self.console.print()  # Final newline
        self.console.print()  # Blank line separator
        self._stream_buffer = []
        return content
```

**Streaming strategy:** We use incremental `print(end="")` for streaming tokens. This means mid-stream text is unformatted, but it's fast and reliable on all terminals. The final content gets stored in the session DB (via AgentLoop) and can be re-rendered as Markdown if needed (e.g., for `/copy`).

### 5.3 `src/hybridcoder/inline/completer.py` — HybridCompleter

**Purpose:** Tab-completion for slash commands and @file references in the prompt_toolkit input.

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from hybridcoder.tui.commands import CommandRouter
from hybridcoder.tui.file_completer import fuzzy_complete


class HybridCompleter(Completer):
    """prompt_toolkit completer for / commands and @ file paths."""

    def __init__(self, command_router: CommandRouter, project_root: Path) -> None:
        self.command_router = command_router
        self.project_root = project_root

    def get_completions(
        self, document: Document, complete_event: object
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        # Slash command completion: /he → /help, /hel → /help
        if text.startswith("/"):
            partial = text[1:]  # Remove leading /
            for cmd in self.command_router.get_all():
                if cmd.name.startswith(partial):
                    yield Completion(
                        cmd.name,
                        start_position=-len(partial),
                        display_meta=cmd.description,
                    )
                for alias in cmd.aliases:
                    if alias.startswith(partial):
                        yield Completion(
                            alias,
                            start_position=-len(partial),
                            display_meta=f"→ /{cmd.name}",
                        )

        # @file completion: @src/hy → @src/hybridcoder/...
        elif "@" in text:
            at_pos = text.rfind("@")
            partial = text[at_pos + 1 :]
            if partial:  # Don't complete bare @
                matches = fuzzy_complete(partial, self.project_root, max_results=10)
                for match in matches:
                    yield Completion(
                        match,
                        start_position=-len(partial),
                        display_meta="file",
                    )
```

### 5.4 `src/hybridcoder/inline/app.py` — InlineApp

**Purpose:** The main REPL loop. This is the heart of inline mode.

```python
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode
from hybridcoder.agent.loop import AgentLoop
from hybridcoder.agent.prompts import build_system_prompt
from hybridcoder.agent.tools import ToolRegistry, create_default_tools
from hybridcoder.config import HybridCoderConfig, load_config
from hybridcoder.inline.completer import HybridCompleter
from hybridcoder.inline.renderer import InlineRenderer
from hybridcoder.layer4.llm import create_provider
from hybridcoder.session.store import SessionStore
from hybridcoder.tui.commands import CommandRouter, create_default_router
from hybridcoder.tui.file_completer import expand_references


class InlineApp:
    """Inline REPL using Rich + prompt_toolkit.

    This is the canonical rendering mode for HybridCoder.
    Output goes to stdout (becomes terminal scrollback).
    Input handled by prompt_toolkit (async readline with completion).
    """

    def __init__(
        self,
        config: HybridCoderConfig | None = None,
        session_id: str | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.config = config or load_config()
        self.project_root = project_root or Path.cwd()

        # Output
        self.console = Console()
        self.renderer = InlineRenderer(self.console)

        # Session
        db_path = Path(self.config.tui.session_db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_store = SessionStore(str(db_path))

        if session_id:
            self.session_id = session_id
        else:
            self.session_id = self.session_store.create_session(
                title="New session",
                model=self.config.model.default_model,
                provider=self.config.model.default_provider,
                project_dir=str(self.project_root),
            )

        # Commands
        self.command_router: CommandRouter = create_default_router()

        # Input (prompt_toolkit)
        history_path = Path("~/.hybridcoder/history").expanduser()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.completer = HybridCompleter(self.command_router, self.project_root)
        self.session = PromptSession(
            history=FileHistory(str(history_path)),
            completer=self.completer,
            multiline=False,
            enable_history_search=True,
        )

        # Agent (lazy init)
        self._provider: Any = None
        self._tool_registry: ToolRegistry | None = None
        self._approval_manager: ApprovalManager | None = None
        self._agent_loop: AgentLoop | None = None
        self._session_titled: bool = False

    # --- AppContext protocol methods ---

    def add_system_message(self, content: str) -> None:
        """Print a system message via renderer."""
        self.renderer.print_system(content)

    def get_assistant_messages(self) -> list[str]:
        """Get assistant messages from session store."""
        messages = self.session_store.get_messages(self.session_id)
        return [m.content for m in messages if m.role == "assistant"]

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard."""
        from hybridcoder.tui.commands import _copy_to_clipboard
        return _copy_to_clipboard(text)

    @property
    def approval_mode(self) -> str:
        if self._approval_manager:
            return self._approval_manager.mode.value
        return self.config.tui.approval_mode

    @approval_mode.setter
    def approval_mode(self, value: str) -> None:
        mode = ApprovalMode(value)
        if self._approval_manager:
            self._approval_manager.mode = mode

    @property
    def shell_enabled(self) -> bool:
        if self._approval_manager:
            return not self._approval_manager.is_shell_disabled()
        return self.config.shell.enabled

    @shell_enabled.setter
    def shell_enabled(self, value: bool) -> None:
        if self._approval_manager and value:
            self._approval_manager.enable_shell()

    # --- Lifecycle ---

    async def run(self) -> None:
        """Main REPL loop. Blocks until /exit or Ctrl+D."""
        self.renderer.print_welcome(
            model=self.config.model.default_model,
            provider=self.config.model.default_provider,
            mode=self.config.tui.approval_mode,
        )

        while True:
            try:
                text = await self.session.prompt_async("> ")
                if not text.strip():
                    continue
                await self._handle_input(text.strip())
            except EOFError:
                break
            except KeyboardInterrupt:
                self.console.print("[dim]^C[/dim]")
                continue

        self.renderer.print_goodbye()

    async def _handle_input(self, text: str) -> None:
        """Route input to slash command or agent loop."""
        # Try slash command first
        result = self.command_router.dispatch(text)
        if result is not None:
            cmd, args = result
            if cmd.name == "exit":
                raise EOFError  # Break the REPL loop
            await cmd.handler(self, args)
            return

        # Expand @file references
        expanded = expand_references(text, self.project_root)

        # Run agent
        await self._run_agent(expanded)

    # --- Agent ---

    def _ensure_agent_loop(self) -> AgentLoop:
        """Lazy-initialize agent loop with all dependencies."""
        if self._agent_loop is None:
            self._provider = create_provider(self.config)
            self._tool_registry = create_default_tools(self.project_root)
            self._approval_manager = ApprovalManager(
                mode=ApprovalMode(self.config.tui.approval_mode),
                shell_config=self.config.shell,
            )

            # Load project memory if available
            memory_path = self.project_root / ".hybridcoder" / "memory.md"
            memory_content = None
            if memory_path.exists():
                memory_content = memory_path.read_text(encoding="utf-8")

            self._agent_loop = AgentLoop(
                provider=self._provider,
                tool_registry=self._tool_registry,
                approval_manager=self._approval_manager,
                session_store=self.session_store,
                session_id=self.session_id,
                memory_content=memory_content,
            )

        return self._agent_loop

    async def _run_agent(self, user_message: str) -> None:
        """Run agent loop and stream output via renderer."""
        self.renderer.print_user_message(user_message)

        # Auto-title session from first user message
        if not self._session_titled:
            title = user_message[:60] + ("..." if len(user_message) > 60 else "")
            self.session_store.update_session(self.session_id, title=title)
            self._session_titled = True

        agent_loop = self._ensure_agent_loop()

        # Start streaming
        self.renderer.start_streaming()

        try:
            response = await agent_loop.run(
                user_message,
                on_chunk=self.renderer.stream_chunk,
                on_thinking_chunk=self.renderer.print_thinking,
                on_tool_call=self.renderer.print_tool_call,
                approval_callback=self._approval_prompt,
                ask_user_callback=self._ask_user_prompt,
            )
        except Exception as e:
            self.renderer.end_streaming()
            self.renderer.print_system(f"Error: {e}")
            return

        self.renderer.end_streaming()

    # --- Interactive prompts ---

    async def _approval_prompt(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Show Y/n/a approval prompt.

        Returns True if approved, False if denied.
        'a' (always) enables shell permanently for this session.
        """
        self.renderer.print_approval_context(tool_name, arguments)

        try:
            answer = await self.session.prompt_async(
                "Allow? [Y/n/a] ",
            )
            answer = answer.strip().lower()

            if answer in ("", "y", "yes"):
                # If this is run_command and shell is disabled, enable it
                if tool_name == "run_command" and self._approval_manager:
                    self._approval_manager.enable_shell()
                return True
            elif answer in ("a", "always"):
                if self._approval_manager:
                    self._approval_manager.enable_shell()
                return True
            else:
                self.renderer.print_system("Denied.")
                return False
        except (EOFError, KeyboardInterrupt):
            self.renderer.print_system("Denied.")
            return False

    async def _ask_user_prompt(
        self, question: str, options: list[str], allow_text: bool
    ) -> str:
        """Show question with numbered options or free-text input.

        Example output:
            Question: Which approach do you prefer?
            1. Option A
            2. Option B
            3. Option C
            Enter choice (1-3 or type answer):
        """
        self.console.print(f"[bold]{question}[/bold]")

        if options:
            for i, opt in enumerate(options, 1):
                self.console.print(f"  {i}. {opt}")

            prompt_text = f"Enter choice (1-{len(options)}"
            if allow_text:
                prompt_text += " or type answer"
            prompt_text += "): "

            try:
                answer = await self.session.prompt_async(prompt_text)
                answer = answer.strip()

                # Check if it's a number
                try:
                    idx = int(answer) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                except ValueError:
                    pass

                # Return as free text if allowed
                if allow_text and answer:
                    return answer

                # Default to first option
                return options[0] if options else answer

            except (EOFError, KeyboardInterrupt):
                return options[0] if options else ""
        else:
            # Free-text only
            try:
                answer = await self.session.prompt_async("Answer: ")
                return answer.strip()
            except (EOFError, KeyboardInterrupt):
                return ""
```

---

## 6. Modified Files (Detailed)

### 6.1 `pyproject.toml`

Add to `dependencies` list:

```toml
"prompt_toolkit>=3.0",
```

prompt_toolkit is a well-maintained library (~4MB installed) with zero heavy dependencies. It's already an indirect dependency via IPython in many Python environments.

### 6.2 `src/hybridcoder/tui/commands.py`

**What changes:**

1. Add `AppContext` protocol class at the top of the file
2. Change handler type hints from `HybridCoderApp` to `AppContext`
3. Replace Textual widget calls with `AppContext` method calls

**The AppContext protocol:**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AppContext(Protocol):
    """Minimal interface for slash command handlers.

    Both InlineApp and HybridCoderApp implement this protocol,
    allowing the same command handlers to work in both modes.
    """

    session_store: SessionStore
    session_id: str
    config: HybridCoderConfig
    project_root: Path

    def add_system_message(self, content: str) -> None:
        """Display a system message to the user."""
        ...

    def get_assistant_messages(self) -> list[str]:
        """Get all assistant message contents from current session."""
        ...

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard. Returns True on success."""
        ...

    @property
    def approval_mode(self) -> str: ...

    @approval_mode.setter
    def approval_mode(self, value: str) -> None: ...

    @property
    def shell_enabled(self) -> bool: ...

    @shell_enabled.setter
    def shell_enabled(self, value: bool) -> None: ...
```

**Handler adaptation examples:**

```python
# BEFORE (Textual-coupled):
async def _handle_help(app: HybridCoderApp, args: str) -> None:
    chat = app.query_one("#chat-view", ChatView)
    help_text = "Available commands:\n"
    for cmd in app.command_router.get_all():
        aliases = ", ".join(f"/{a}" for a in cmd.aliases)
        help_text += f"  /{cmd.name}"
        if aliases:
            help_text += f" ({aliases})"
        help_text += f" — {cmd.description}\n"
    chat.add_message("system", help_text)

# AFTER (framework-agnostic):
async def _handle_help(app: AppContext, args: str) -> None:
    help_text = "Available commands:\n"
    router = app.command_router if hasattr(app, 'command_router') else None
    if router:
        for cmd in router.get_all():
            aliases = ", ".join(f"/{a}" for a in cmd.aliases)
            help_text += f"  /{cmd.name}"
            if aliases:
                help_text += f" ({aliases})"
            help_text += f" — {cmd.description}\n"
    app.add_system_message(help_text)
```

```python
# BEFORE:
async def _handle_sessions(app: HybridCoderApp, args: str) -> None:
    chat = app.query_one("#chat-view", ChatView)
    sessions = app.session_store.list_sessions()
    # ... format sessions ...
    chat.add_message("system", output)

# AFTER:
async def _handle_sessions(app: AppContext, args: str) -> None:
    sessions = app.session_store.list_sessions()
    # ... format sessions ...
    app.add_system_message(output)
```

```python
# BEFORE:
async def _handle_mode(app: HybridCoderApp, args: str) -> None:
    chat = app.query_one("#chat-view", ChatView)
    if not args:
        chat.add_message("system", f"Current mode: {app._approval_manager.mode.value}")
        return
    # ... set mode ...

# AFTER:
async def _handle_mode(app: AppContext, args: str) -> None:
    if not args:
        app.add_system_message(f"Current mode: {app.approval_mode}")
        return
    app.approval_mode = args
    app.add_system_message(f"Mode changed to: {args}")
```

```python
# /freeze — inline mode doesn't need this (native scrollback)
async def _handle_freeze(app: AppContext, args: str) -> None:
    if hasattr(app, 'frozen'):  # Textual TUI
        # ... existing freeze/unfreeze logic ...
        pass
    else:
        app.add_system_message(
            "Scroll-lock is not needed in inline mode — "
            "use your terminal's native scrollback."
        )
```

### 6.3 `src/hybridcoder/tui/app.py`

**What changes:** Add methods to satisfy `AppContext` protocol. These are thin wrappers around existing widget calls.

```python
# Add these methods to HybridCoderApp:

def add_system_message(self, content: str) -> None:
    """AppContext: Display system message via ChatView."""
    chat = self.query_one("#chat-view", ChatView)
    chat.add_message("system", content)

def get_assistant_messages(self) -> list[str]:
    """AppContext: Get assistant messages from session store."""
    messages = self.session_store.get_messages(self.session_id)
    return [m.content for m in messages if m.role == "assistant"]

def copy_to_clipboard(self, text: str) -> bool:
    """AppContext: Copy to clipboard using platform-native command."""
    return _copy_to_clipboard(text)

@property
def approval_mode(self) -> str:
    """AppContext: Current approval mode."""
    if self._approval_manager:
        return self._approval_manager.mode.value
    return self.config.tui.approval_mode

@approval_mode.setter
def approval_mode(self, value: str) -> None:
    """AppContext: Set approval mode."""
    if self._approval_manager:
        self._approval_manager.mode = ApprovalMode(value)

@property
def shell_enabled(self) -> bool:
    """AppContext: Whether shell execution is enabled."""
    if self._approval_manager:
        return not self._approval_manager.is_shell_disabled()
    return self.config.shell.enabled

@shell_enabled.setter
def shell_enabled(self, value: bool) -> None:
    """AppContext: Enable/disable shell."""
    if self._approval_manager and value:
        self._approval_manager.enable_shell()
```

### 6.4 `src/hybridcoder/cli.py`

**What changes:** Default `chat` command uses InlineApp. Add `--tui` flag.

```python
@app.command()
def chat(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    session: str | None = typer.Option(None, "--session", "-s", help="Resume session by ID"),
    tui: bool = typer.Option(False, "--tui", help="Use fullscreen Textual TUI"),
    alternate_screen: bool = typer.Option(False, "--alternate-screen", help="Alias for --tui"),
    legacy: bool = typer.Option(False, "--legacy", help="Use legacy Rich REPL (no agent loop)"),
) -> None:
    """Start an interactive chat session."""
    config = load_config()

    if legacy:
        asyncio.run(_chat_loop(config))
    elif tui or alternate_screen:
        # Fullscreen Textual TUI (opt-in)
        from hybridcoder.tui.app import HybridCoderApp

        use_inline = False  # Always fullscreen when --tui
        tui_app = HybridCoderApp(config=config, session_id=session)
        tui_app.run(inline=use_inline)
    else:
        # Default: inline REPL (Rich + prompt_toolkit)
        from hybridcoder.inline.app import InlineApp

        inline_app = InlineApp(config=config, session_id=session)
        asyncio.run(inline_app.run())
```

---

## 7. Feature Matrix

| Feature | Inline (Rich + pt) | Textual TUI | Implementation Notes |
|---------|:------------------:|:-----------:|---------------------|
| Streaming text output | Yes | Yes | Inline: `console.print(chunk, end="")`. TUI: `Static.update()` |
| Rich Markdown rendering | Yes | Yes | Both use `rich.Markdown` |
| Syntax-highlighted diffs | Yes | Yes | Both use `rich.Syntax` |
| Slash commands (12) | Yes | Yes | Shared `CommandRouter` via `AppContext` |
| @file references | Yes | Yes | Shared `file_completer` functions |
| @file tab completion | Yes | Yes | Inline: `HybridCompleter`. TUI: `InputBar` suggestions |
| Approval prompts (Y/n/a) | Yes | Yes | Inline: `session.prompt_async()`. TUI: `ApprovalPrompt` widget |
| ask_user (options) | Yes | Yes | Inline: numbered list. TUI: `OptionSelector` widget |
| ask_user (free text) | Yes | Yes | Inline: prompt. TUI: `InputBar` wait |
| Session persistence | Yes | Yes | Shared `SessionStore` (SQLite + WAL) |
| Session compaction | Yes | Yes | Shared via `/compact` command |
| Tool call display | Yes | Yes | Inline: `[tool] name ✓`. TUI: `Collapsible` |
| Thinking tokens | Yes | Yes | Inline: dim text. TUI: `Collapsible(collapsed=True)` |
| /copy command | Yes | Yes | Shared `_copy_to_clipboard()` helper |
| /freeze (scroll-lock) | N/A | Yes | Inline: no-op (native scrollback). TUI: freezes auto-scroll |
| **Native text selection** | **Yes** | **No** | Inline outputs to stdout → terminal scrollback |
| **Terminal scrollback** | **Yes** | **No** | Inline: content persists in terminal buffer |
| **Terminal search (Ctrl+F)** | **Yes** | **No** | Terminal-native feature, works with scrollback |
| **Works on Windows** | **Yes** | Yes | Inline: no `termios` dependency |
| Interactive option selector | Numbered list | Arrow-key OptionList | Different UX, same result |
| Persistent status bar | No | Yes | Inline: status shown in welcome + on demand |
| Mouse-driven UI | No | Limited | Neither captures mouse events |
| PageUp/PageDown scroll | Terminal native | Textual binding | Both work, different mechanism |
| Input history (arrow keys) | Yes | Yes | Inline: `FileHistory`. TUI: `TextArea` |
| Multi-line input | Shift+Enter* | Shift+Enter | *prompt_toolkit needs key binding |

---

## 8. Implementation Steps (Detailed)

### Step 1: Add prompt_toolkit dependency

**File:** `pyproject.toml`
**Change:** Add `"prompt_toolkit>=3.0"` to `dependencies` list
**Test:** `uv sync && python -c "import prompt_toolkit; print(prompt_toolkit.__version__)"`

### Step 2: Define AppContext protocol + adapt handlers

**File:** `src/hybridcoder/tui/commands.py`
**Changes:**
1. Add `AppContext` protocol class (see Section 6.2)
2. Update all 12 handler signatures from `HybridCoderApp` to `AppContext`
3. Replace `app.query_one("#chat-view", ChatView).add_message(...)` with `app.add_system_message(...)`
4. Replace direct widget access with AppContext properties

**Why this is the hardest step:** Each handler needs individual review. Some handlers are simple (just change `chat.add_message` to `app.add_system_message`), but others have more complex widget interactions (e.g., `/copy` accesses chat message widgets, `/freeze` toggles ChatView state).

**Handler complexity map:**

| Handler | Complexity | Changes Needed |
|---------|-----------|---------------|
| `_handle_exit` | Trivial | No Textual calls |
| `_handle_new` | Low | `app.add_system_message()` |
| `_handle_sessions` | Low | `app.add_system_message()` with formatted output |
| `_handle_resume` | Medium | Resets session_id, reloads messages |
| `_handle_help` | Low | `app.add_system_message()` |
| `_handle_model` | Low | `app.add_system_message()` |
| `_handle_mode` | Low | `app.approval_mode` property |
| `_handle_compact` | Medium | Needs agent loop access |
| `_handle_init` | Low | File creation, `app.add_system_message()` |
| `_handle_shell` | Low | `app.shell_enabled` property |
| `_handle_copy` | Medium | `app.get_assistant_messages()` + `app.copy_to_clipboard()` |
| `_handle_freeze` | Low | No-op for inline, guard with `hasattr` |

### Step 3: Add AppContext methods to HybridCoderApp

**File:** `src/hybridcoder/tui/app.py`
**Changes:** Add 6 methods/properties (see Section 6.3)
**Test:** Existing TUI tests must still pass — these are additive methods

### Step 4: Create InlineRenderer

**File:** `src/hybridcoder/inline/renderer.py`
**Dependencies:** `rich` (already installed)
**Test immediately:** Write `tests/unit/test_inline_renderer.py` (8 tests)

### Step 5: Create HybridCompleter

**File:** `src/hybridcoder/inline/completer.py`
**Dependencies:** `prompt_toolkit`, `tui/file_completer.py`, `tui/commands.py`
**Test immediately:** Write `tests/unit/test_inline_completer.py` (5 tests)

### Step 6: Create InlineApp

**File:** `src/hybridcoder/inline/app.py`
**Dependencies:** Everything in the shared backend + renderer + completer
**This is the integration point.** Wire all components together.
**Test immediately:** Write `tests/unit/test_inline_app.py` (8 tests)

### Step 7: Create `__init__.py`

**File:** `src/hybridcoder/inline/__init__.py`

### Step 8: Update CLI

**File:** `src/hybridcoder/cli.py`
**Changes:** See Section 6.4

### Step 9: AppContext protocol tests

**File:** `tests/unit/test_app_context.py` (4 tests)

### Step 10: Sprint verification

**File:** `tests/test_sprint_verify.py` — add `TestSprint2C` class (6 tests)

### Step 11: Full test suite + lint

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/hybridcoder/
```

---

## 9. QA Matrix

### Inline Mode Validation

| OS | Terminal | Text Selection | Scrollback | Clipboard | Priority |
|----|---------|:-------------:|:----------:|:---------:|----------|
| **Windows** | Windows Terminal | Verify | Verify | `clip.exe` | P0 |
| **Windows** | PowerShell (conhost) | Verify | Verify | `clip.exe` | P1 |
| **macOS** | Terminal.app | Verify | Verify | `pbcopy` | P0 |
| **macOS** | iTerm2 | Verify | Verify | `pbcopy` | P1 |
| **Linux** | gnome-terminal | Verify | Verify | `xclip`/`xsel` | P0 |
| **Linux** | tmux | Copy mode | Verify | `xclip`/`xsel` | P1 |
| **Linux** | zellij | Verify | Verify | `xclip`/`xsel` | P2 |

**Verification steps for each environment:**
1. `hybridcoder chat` → starts inline REPL
2. Type a message → streaming response appears
3. Scroll up with mouse wheel or keyboard → previous output visible
4. Select text with mouse → copies to clipboard
5. `/copy` → content copied to system clipboard
6. Ctrl+D → exits cleanly
7. `hybridcoder chat --tui` → Textual TUI launches (existing behavior)

### Textual TUI Regression (Best-Effort)

| OS | Terminal | Expected Behavior | Priority |
|----|---------|-------------------|----------|
| **Windows** | Windows Terminal | App launches, all widgets render, `/copy` works | P1 |
| **macOS** | Terminal.app | App launches, all widgets render | P1 |
| **Linux** | gnome-terminal | App launches, all widgets render | P1 |

### Feature Verification Checklist

For **both** modes, verify:

- [ ] User can type and submit messages
- [ ] Streaming responses render incrementally
- [ ] `/help` — shows all 12 commands
- [ ] `/exit` — exits cleanly
- [ ] `/model` — shows current model
- [ ] `/mode suggest` — changes approval mode
- [ ] `/sessions` — lists sessions
- [ ] `/new` — creates new session
- [ ] `/resume <id>` — resumes session
- [ ] `/compact` — summarizes history
- [ ] `/init` — creates project memory file
- [ ] `/shell on` — enables shell execution
- [ ] `/copy` — copies last assistant message to clipboard
- [ ] `@README.md` in input — file content expanded
- [ ] Tab completion for `/` commands
- [ ] Tab completion for `@` file paths
- [ ] Approval prompt appears for `write_file` (suggest mode)
- [ ] ask_user questions display with numbered options
- [ ] Tool call results display
- [ ] Ctrl+C during generation — cancels gracefully
- [ ] Ctrl+D — exits REPL

---

## 10. Tests (Detailed)

### Testing Strategy

**InlineRenderer:** Capture Rich Console output to a `StringIO` buffer. Assert output contains expected formatted text.

```python
from io import StringIO
from rich.console import Console
from hybridcoder.inline.renderer import InlineRenderer

def test_print_welcome():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    renderer = InlineRenderer(console=console)
    renderer.print_welcome(model="qwen3-8b", provider="ollama", mode="suggest")
    output = buf.getvalue()
    assert "HybridCoder" in output
    assert "qwen3-8b" in output
    assert "suggest" in output
```

**HybridCompleter:** Create a mock `Document` and verify completions.

```python
from prompt_toolkit.document import Document
from hybridcoder.inline.completer import HybridCompleter
from hybridcoder.tui.commands import create_default_router

def test_slash_command_completion(tmp_path):
    router = create_default_router()
    completer = HybridCompleter(router, tmp_path)
    doc = Document("/he", cursor_position=3)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "help" in names
```

**InlineApp:** Mock the prompt_toolkit `PromptSession` and Rich `Console` to test the REPL logic without actual terminal I/O.

```python
from unittest.mock import AsyncMock, MagicMock, patch
from hybridcoder.inline.app import InlineApp

@pytest.fixture
def inline_app(tmp_path):
    config = create_test_config(tmp_path)
    app = InlineApp(config=config, project_root=tmp_path)
    return app

async def test_slash_command_dispatch(inline_app):
    """Verify /help dispatches to help handler."""
    with patch.object(inline_app, 'add_system_message') as mock_msg:
        await inline_app._handle_input("/help")
        mock_msg.assert_called_once()
        assert "Available commands" in mock_msg.call_args[0][0]
```

### New Test Files

#### `tests/unit/test_inline_renderer.py` (8 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_print_welcome` | Output contains model name, provider, mode |
| 2 | `test_print_user_message` | Output contains ">" prefix and message text |
| 3 | `test_print_assistant_message` | Markdown renders (headers become styled text) |
| 4 | `test_print_tool_call_success` | Output contains tool name and "✓" |
| 5 | `test_print_tool_call_error` | Output contains tool name and "✗" |
| 6 | `test_print_diff` | Output contains diff markers (+/-) |
| 7 | `test_streaming_accumulates` | start → chunks → end returns concatenated content |
| 8 | `test_print_sessions_table` | Output contains session ID and title |

#### `tests/unit/test_inline_completer.py` (5 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_slash_command_completion` | `/he` yields `help` completion |
| 2 | `test_slash_command_all` | `/` yields all 12 command completions |
| 3 | `test_at_file_completion` | `@README` yields `README.md` when file exists |
| 4 | `test_no_completion_for_regular_text` | `hello world` yields no completions |
| 5 | `test_mixed_text_with_at` | `read @RE` yields `README.md` completion |

#### `tests/unit/test_inline_app.py` (8 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_app_creates_session` | `session_id` is set, session exists in store |
| 2 | `test_slash_command_dispatch` | `/help` calls `add_system_message` |
| 3 | `test_exit_raises_eof` | `/exit` raises `EOFError` to break loop |
| 4 | `test_at_file_expansion` | `@file.txt` expands to file content |
| 5 | `test_agent_response_rendered` | Mock agent returns text → renderer called |
| 6 | `test_tool_call_displayed` | Mock tool call → `print_tool_call` called |
| 7 | `test_approval_prompt_yes` | Mock prompt returns "y" → callback returns True |
| 8 | `test_approval_prompt_no` | Mock prompt returns "n" → callback returns False |

#### `tests/unit/test_app_context.py` (4 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_inline_app_satisfies_protocol` | `isinstance(InlineApp(...), AppContext)` is True |
| 2 | `test_tui_app_satisfies_protocol` | `isinstance(HybridCoderApp(...), AppContext)` is True |
| 3 | `test_add_system_message_inline` | `add_system_message()` calls renderer |
| 4 | `test_get_assistant_messages` | Returns messages with role="assistant" from session |

#### `tests/test_sprint_verify.py` additions (6 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_inline_app_imports` | `from hybridcoder.inline.app import InlineApp` succeeds |
| 2 | `test_inline_renderer_imports` | `from hybridcoder.inline.renderer import InlineRenderer` succeeds |
| 3 | `test_hybrid_completer_imports` | `from hybridcoder.inline.completer import HybridCompleter` succeeds |
| 4 | `test_app_context_protocol` | `AppContext` has all required methods |
| 5 | `test_cli_tui_flag` | `--tui` parameter exists on `chat` command |
| 6 | `test_prompt_toolkit_installed` | `import prompt_toolkit` succeeds, version >= 3.0 |

### Test Count Summary

| Category | Count |
|----------|-------|
| Existing tests | 307 |
| `test_inline_renderer.py` | 8 |
| `test_inline_completer.py` | 5 |
| `test_inline_app.py` | 8 |
| `test_app_context.py` | 4 |
| `test_sprint_verify.py` additions | 6 |
| **Total** | **~338** |

---

## 11. Performance Budgets

Inline mode must meet or beat the Textual TUI budgets from `docs/plan/resource_profiling.md`:

| Metric | Inline Budget | Textual Budget | Notes |
|--------|:------------:|:--------------:|-------|
| Cold startup | < 1.5s | < 2.0s | Fewer imports (no Textual CSS engine) |
| Warm startup | < 0.5s | < 1.0s | Rich + pt are lightweight |
| Keystroke echo | < 50ms | < 100ms | prompt_toolkit is inherently fast |
| Idle RSS | < 50 MB | < 80 MB | No widget tree, no event loop |
| Peak RSS (chat) | < 100 MB | < 150 MB | During streaming with large responses |
| Time-to-first-token | Same | Same | Provider-dependent (shared backend) |
| Idle CPU | < 1% | < 3% | No frame rendering loop |

**Expected improvements over Textual TUI:**
- **Lower idle RSS:** No Textual widget tree, CSS engine, or compositor in memory
- **Faster startup:** `import prompt_toolkit` + `import rich` is faster than `import textual`
- **Lower idle CPU:** No periodic frame rendering (Textual renders at ~16ms intervals)
- **Same agent performance:** Shared AgentLoop, same provider, same tool execution

---

## 12. Dual-UI Guardrails

These guardrails were agreed with Codex (Entries 56-Codex, 58) and the user:

### Canonical Mode

**Inline (Rich + prompt_toolkit) is canonical.** This means:
- New user-visible features land in inline first
- Textual TUI gets features only when explicitly needed
- Bug fixes that affect shared backend apply to both modes
- UI-specific bugs are fixed in the affected mode only

### Shared Rendering Contract

Both modes consume the same AgentLoop callbacks:

| Callback | Inline Implementation | Textual Implementation |
|----------|----------------------|----------------------|
| `on_chunk(text)` | `renderer.stream_chunk(text)` | `chat_view.add_streaming_chunk(text)` |
| `on_thinking_chunk(text)` | `renderer.print_thinking(text)` | `chat_view.add_thinking_chunk(text)` |
| `on_tool_call(name, status, result)` | `renderer.print_tool_call(...)` | `chat_view.add_tool_call(...)` |
| `approval_callback(name, args) -> bool` | `_approval_prompt(...)` | `_interactive_approval(...)` |
| `ask_user_callback(q, opts, allow) -> str` | `_ask_user_prompt(...)` | `_interactive_ask_user(...)` |

The AgentLoop doesn't know or care which mode is active. It calls the same callbacks.

### Feature Matrix (Mode-Specific)

Features that exist in only one mode:

| Feature | Inline Only | Textual Only | Reason |
|---------|:-----------:|:------------:|--------|
| Native text selection | Yes | — | stdout → scrollback → terminal handles it |
| Terminal scrollback | Yes | — | stdout enters scrollback buffer |
| Terminal search | Yes | — | Terminal's built-in Ctrl+F |
| `/freeze` command | — | Yes | Inline doesn't auto-scroll; no need |
| Persistent status bar | — | Yes | Textual widget; inline prints on demand |
| Arrow-key option selector | — | Yes | Textual OptionList widget |

### Parity Tests

- **Shared tests:** AgentLoop tests already verify callbacks fire correctly. These are mode-independent.
- **Renderer-specific tests:** Each mode has its own test file testing its specific rendering.
- **AppContext compliance:** `test_app_context.py` verifies both apps satisfy the protocol.

### CI Gating

Both test suites must pass on every commit:

```bash
# CI pipeline
uv run pytest tests/unit/ -v              # All unit tests (both modes)
uv run pytest tests/test_sprint_verify.py  # Sprint checks
uv run ruff check src/ tests/             # Linting
uv run mypy src/hybridcoder/              # Type checking
```

---

## 13. Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|-----------|
| **prompt_toolkit async complexity** | Medium | Low | Aider proves `PromptSession.prompt_async()` works. Our sequential REPL loop (await agent, then await prompt) avoids the concurrency issues that `patch_stdout()` was designed to solve. |
| **Feature drift between modes** | Medium | Medium | `AppContext` protocol enforces shared interface. New features land in inline first. CI runs both suites. |
| **Streaming formatting (mid-stream)** | Low | Medium | Use incremental print (plain text mid-stream). Final content stored in session DB as markdown. |
| **Handler adaptation breaks Textual** | Medium | Low | `AppContext` is additive — existing methods still work. All existing tests must pass. |
| **prompt_toolkit + Rich on Windows** | Low | Low | Both are well-tested on Windows. Note: `patch_stdout()` was found to corrupt Rich's ANSI escape sequences on Windows and was intentionally removed. The sequential REPL design makes it unnecessary. |
| **Approval prompt interrupts stream** | Low | Certain | Acceptable UX — pause stream, show prompt, resume. Same behavior as Textual mode. |
| **Tab completion performance** | Low | Low | `fuzzy_complete()` already handles large directories. prompt_toolkit completions are lazy (yielded). |

---

## 14. Exit Criteria

Sprint 2C is complete when ALL of these are met:

### Functional
- [ ] `hybridcoder chat` launches inline REPL (Rich + prompt_toolkit)
- [ ] `hybridcoder chat --tui` launches Textual TUI (existing behavior preserved)
- [ ] All 12 slash commands work in inline mode
- [ ] @file references work with tab completion in inline mode
- [ ] Streaming output renders incrementally
- [ ] Approval prompts work (Y/n/a) in inline mode
- [ ] ask_user questions work with numbered options in inline mode
- [ ] Tool calls display as `[tool] name ✓/✗` status lines
- [ ] Session persistence works (create, resume, list, compact)
- [ ] Ctrl+D exits cleanly, Ctrl+C cancels generation

### Quality
- [ ] All existing tests pass (307+)
- [ ] ~31 new inline tests pass
- [ ] `ruff check` clean
- [ ] `mypy` clean

### QA
- [ ] QA matrix P0 items verified manually (Windows Terminal, Terminal.app, gnome-terminal)
- [ ] Native text selection works in inline mode (verified on Windows)
- [ ] Terminal scrollback preserves conversation history

### Performance
- [ ] Cold startup < 1.5s
- [ ] Idle RSS < 50 MB

---

## 15. Implementation Order

```
Step  1: pyproject.toml             — add prompt_toolkit>=3.0
Step  2: tui/commands.py            — add AppContext protocol
Step  3: tui/commands.py            — adapt 12 handlers to AppContext
Step  4: tui/app.py                 — add AppContext methods to HybridCoderApp
Step  5: inline/__init__.py         — package init
Step  6: inline/renderer.py         — InlineRenderer class
Step  7: inline/completer.py        — HybridCompleter class
Step  8: inline/app.py              — InlineApp REPL loop
Step  9: cli.py                     — default to InlineApp, add --tui flag
Step 10: tests/unit/test_inline_renderer.py   — 8 tests
Step 11: tests/unit/test_inline_completer.py  — 5 tests
Step 12: tests/unit/test_inline_app.py        — 8 tests
Step 13: tests/unit/test_app_context.py       — 4 tests
Step 14: tests/test_sprint_verify.py          — Sprint 2C checks (6 tests)
→ Run: uv run pytest tests/ -v && uv run ruff check src/ tests/ && uv run mypy src/
```

**Estimated effort:** ~3-4 implementation sessions.

---

## 16. Dependencies on Existing Code

### Code Dependencies

| What | Location | How Used in Sprint 2C |
|------|----------|----------------------|
| `CommandRouter`, `SlashCommand` | `tui/commands.py:15-45` | Shared command dispatch for both modes |
| `create_default_router()` | `tui/commands.py:200+` | Registers all 12 commands |
| `_copy_to_clipboard()` | `tui/commands.py:50+` | Platform-native clipboard (clip.exe/pbcopy/xclip) |
| `AgentLoop` | `agent/loop.py:25-120` | Core LLM ↔ tool cycle (max 10 iterations) |
| `ToolRegistry`, `create_default_tools()` | `agent/tools.py:30-180` | 6 tools with JSON Schema parameters |
| `ApprovalManager`, `ApprovalMode` | `agent/approval.py:10-80` | 3 approval modes, shell gating |
| `build_system_prompt()` | `agent/prompts.py:5-40` | Dynamic system prompt with shell/approval state |
| `SessionStore` | `session/store.py:20-150` | SQLite persistence (WAL mode, 3 tables) |
| `detect_at_references()` | `tui/file_completer.py:10-30` | Find `@path` and `@path:start-end` in text |
| `expand_references()` | `tui/file_completer.py:50-70` | Replace @refs with file contents |
| `fuzzy_complete()` | `tui/file_completer.py:75-100` | Match partial paths against project files |
| `create_provider()` | `layer4/llm.py:181-185` | Factory for OllamaProvider or OpenRouterProvider |
| `load_config()`, `HybridCoderConfig` | `config.py:202-233` | YAML config loading, Pydantic models |
| `TUIConfig` | `config.py:99-107` | approval_mode, session_db_path, max_iterations |
| `ShellConfig` | `config.py:87-96` | enabled, timeout, allowed/blocked commands |

### Package Dependencies

| Package | Version | Purpose | Already Installed? |
|---------|---------|---------|:-----------------:|
| `rich` | >=13.0 | Markdown rendering, syntax highlighting, tables | Yes |
| `prompt_toolkit` | >=3.0 | Async input, tab completion, history | **New** |
| `textual` | >=0.89 | Textual TUI (existing, no changes) | Yes |
| `typer` | >=0.12 | CLI framework | Yes |

---

## 17. References

### Project Documents
- `docs/plan/inline-tui-research.md` — Full research document (699 lines, covers Claude Code, Codex CLI, Aider, OpenCode, Textual inline, prompt_toolkit)
- `docs/claude/08-inline-tui-research.md` — Research archive copy
- `docs/plan/phase2-tui-prototype.md` v3.5, Section 20 — Parent plan with inline mode addendum
- `docs/plan/resource_profiling.md` — Performance budgets and profiling cadence
- `docs/plan/tui-quality-checklist.md` — TUI quality checklist (BENCH sentinels)

### External References
- [Aider io.py source](https://github.com/Aider-AI/aider/blob/main/aider/io.py) — Rich + prompt_toolkit reference implementation
- [prompt_toolkit documentation](https://python-prompt-toolkit.readthedocs.io/) — Async prompts, completers, history
- [Rich documentation](https://rich.readthedocs.io/) — Console, Markdown, Syntax, Table
- [prompt_toolkit async example](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/examples/prompts/asyncio-prompt.py) — `prompt_async()` + `patch_stdout()` pattern

### Agent Communication
- Codex Entry 55: APPROVE with suggestions (QA matrix, test count)
- Codex Entry 56: Medium concern about dual-UI → resolved: inline canonical, Textual best-effort
- Codex Entry 58: Guardrails proposal (acceptance matrix, parity tests, perf budgets, CI gating)
- Codex Entry 61: Final acknowledgement — no further concerns
- Archived: `docs/communication/old/2026-02-06-inline-mode-approval.md`
