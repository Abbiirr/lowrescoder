# Inline Terminal UI Research: How Modern AI Coding Assistants Render

> HybridCoder -- Edge-Native AI Coding Assistant
> Date: 2026-02-05
> Purpose: Research how Claude Code, Codex CLI, Aider, and OpenCode implement terminal UIs, with focus on inline rendering, scrollback behavior, and recommendations for HybridCoder.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Claude Code -- Custom React Renderer](#2-claude-code)
3. [OpenAI Codex CLI -- Ink to Ratatui/Rust](#3-codex-cli)
4. [Aider -- Rich + prompt_toolkit](#4-aider)
5. [OpenCode -- Bubble Tea Fullscreen](#5-opencode)
6. [Textual Inline Mode -- Deep Dive](#6-textual-inline-mode)
7. [prompt_toolkit -- Deep Dive](#7-prompt_toolkit)
8. [The Two Paradigms: Inline vs Fullscreen](#8-two-paradigms)
9. [What Makes Claude Code Feel "Inline"](#9-what-makes-claude-code-feel-inline)
10. [Hybrid Approaches](#10-hybrid-approaches)
11. [Recommendations for HybridCoder](#11-recommendations)
12. [Sources](#12-sources)

---

## 1. Executive Summary

Modern CLI AI coding assistants fall into two rendering paradigms:

| Paradigm | Tools | Approach |
|----------|-------|----------|
| **Inline/Streaming** | Claude Code, Aider, pi | Content appended to terminal scrollback, no alternate screen |
| **Fullscreen TUI** | Codex CLI (Rust), OpenCode, Amp | Alternate screen buffer, custom viewport management |

The key finding: **the tools that feel most native to terminal users (Claude Code, Aider) deliberately avoid fullscreen mode.** They append output to the scrollback buffer, let the terminal handle text selection and search, and only use cursor repositioning for the input area and live-updating sections.

For HybridCoder, which currently uses Textual (a fullscreen TUI framework), there are three viable paths:

1. **Textual inline mode** -- limited, no Windows support, widget interaction concerns
2. **Rich + prompt_toolkit hybrid** -- the Aider approach, most proven for Python
3. **Custom differential renderer** -- the Claude Code approach, highest effort but best UX

**Recommendation:** Adopt the **Rich + prompt_toolkit hybrid** (Option 2) as the primary rendering mode, with Textual fullscreen as an optional alternate mode triggered by a flag. This gives the inline feel that users expect while keeping all interactive features.

---

## 2. Claude Code

### Architecture

Claude Code is built with **React and Ink** (React for terminals), but Anthropic has **rewritten the renderer from scratch** while keeping React as the component model. The original Ink renderer did not support the fine-grained incremental updates needed for a long-running interactive UI.

### Rendering Pipeline

The custom renderer follows a game-engine-like pipeline:

```
React scene graph --> layout elements --> 2D rasterization --> screen diffing --> ANSI sequence generation
```

This runs within a ~16ms frame budget. The implementation uses **packed TypedArrays** for the screen buffer to minimize garbage collection pauses that caused stuttering on slower machines.

### Key Design Decisions

1. **No alternate screen mode.** Claude Code deliberately stays in the main terminal buffer, preserving:
   - Native text selection with the mouse
   - Terminal scrollback history
   - Terminal search (Cmd+F / Ctrl+Shift+F)
   - Copy/paste behavior

2. **Differential rendering.** Compares current and previous screen states, emitting ANSI commands only for changed cells. This is called "cell-based diffing."

3. **Synchronized output (DEC mode 2026).** Wraps output in sync markers (`CSI ?2026h` / `CSI ?2026l`) so the terminal renders everything atomically -- no flicker. Anthropic has contributed patches upstream to VSCode's terminal and tmux.

4. **Input bar at the bottom.** The entire UI (chat history + input bar) is rendered as one React component tree. The input bar is always at the bottom of the visible region. When content grows beyond the viewport, earlier content scrolls into the terminal's native scrollback.

### Tradeoffs

- **Pro:** Best native terminal experience -- text selection, scrollback, search all work
- **Pro:** No mouse capture -- terminal handles mouse natively
- **Con:** Massive engineering effort (custom renderer, frame budgets, TypedArray buffers)
- **Con:** Flickering issues in ~1/3 of sessions (terminals without DEC 2026 support)
- **Con:** Cursor position drift bugs on Windows (ConPTY issues)
- **Con:** Performance degrades over long conversations (O(width x height) diffing per frame)

### How the Input Bar Works

The input bar is not a separate widget -- it is part of the React component tree that gets re-rendered each frame. The cursor position is managed by the renderer, which knows where the input area is in the screen buffer. When the user types, only the input area cells change, so the differential renderer only updates those cells.

---

## 3. Codex CLI

### Architecture Evolution

Codex CLI has gone through two major architectural phases:

1. **Original (TypeScript/Ink):** Built with React/Ink, similar to Claude Code's original approach
2. **Rust rewrite (current):** Rebuilt in Rust using **Ratatui + Crossterm**

### Current Rendering (Rust)

The Rust TUI uses **fullscreen/alternate screen mode**. The initialization explicitly enters the alternate screen buffer before creating the App and ChatWidget components.

Layout:
- **Upper section:** Conversation history (scrollable)
- **Lower section:** Input bar + status

Event handling uses an event-driven pattern:

| Event Type | Source | Purpose |
|------------|--------|---------|
| KeyEvent | Keyboard | User keypresses |
| Scroll | Mouse wheel | Navigate history |
| CodexEvent | Core | Model responses |
| Redraw | Internal | UI state changes |

### Tradeoffs

- **Pro:** Zero-dependency install (Rust binary, no Node.js needed)
- **Pro:** Native performance, no GC pauses
- **Pro:** Clean separation of concerns (event-driven)
- **Con:** Fullscreen mode breaks terminal scrollback
- **Con:** Custom scrolling implementation needed
- **Con:** Mouse events captured by the app, not the terminal
- **Con:** Text selection does not work natively in the chat area

### Note on Feeling "Inline"

Despite using fullscreen mode, early versions of Codex CLI (TypeScript/Ink) did feel more inline. The Rust rewrite with Ratatui is a more traditional fullscreen TUI. Users have reported issues with scrollback not being available after exiting.

---

## 4. Aider

### Architecture

Aider uses the **Rich + prompt_toolkit** combination, which is the most common Python approach for terminal REPL applications.

- **prompt_toolkit:** Handles all interactive input (PromptSession, completion, key bindings, history)
- **Rich:** Handles all formatted output (Markdown rendering, syntax highlighting, tables, colors)

### How It Works

```
User Input:  prompt_toolkit.PromptSession.prompt()
    |
    v
Processing:  coder.run() --> LLM API --> parse edits
    |
    v
Output:      rich.Console.print(Markdown(response))
    |
    v
Loop back to input
```

### Key Implementation Details

1. **No alternate screen.** Output goes directly to stdout, becoming part of the terminal scrollback.

2. **prompt_toolkit features used:**
   - `PromptSession` with `FileHistory` for persistent history
   - `AutoCompleter` with `ThreadedCompleter` for non-blocking file/command completion
   - `PygmentsLexer(MarkdownLexer)` for input syntax highlighting
   - Custom `KeyBindings` for Ctrl+Z (suspend), Ctrl+Space, Ctrl+X+E (external editor)
   - Both EMACS and VI editing modes
   - `CompleteStyle.MULTI_COLUMN` for completion display

3. **Rich features used:**
   - `Markdown` class for rendering LLM responses with code themes
   - `Console` for styled output
   - `Columns` for file list layout
   - Color validation with fallback

4. **Streaming:** Uses a `MarkdownStream` class for incremental markdown rendering during LLM response streaming. Output appears token-by-token.

5. **No mouse capture.** Terminal handles mouse selection natively.

### Tradeoffs

- **Pro:** Simple architecture, easy to understand and maintain
- **Pro:** Native scrollback, text selection, terminal search
- **Pro:** Battle-tested libraries (prompt_toolkit is used by IPython, AWS CLI, etc.)
- **Pro:** Cross-platform (Windows, macOS, Linux)
- **Con:** No persistent UI elements (no status bar that stays visible during output)
- **Con:** No interactive widgets during streaming (approval prompts must wait)
- **Con:** Cannot show a spinner/status while output streams
- **Con:** Input and output are sequential, not concurrent (the prompt blocks)

---

## 5. OpenCode

### Architecture

OpenCode is built in **Go with Bubble Tea** (charmbracelet/bubbletea), using a **fullscreen TUI** approach.

- Takes ownership of the terminal viewport
- Treats the viewport as a character cell buffer
- Custom scrolling, Vim-like keybindings
- Event-driven architecture (Elm Architecture pattern)

### Tradeoffs

Same as Codex CLI's fullscreen approach: clean UI, but loses native scrollback, text selection, and terminal search.

---

## 6. Textual Inline Mode -- Deep Dive

### How It Works

When `app.run(inline=True)` is called:

1. The app **does not enter alternate screen mode** (application mode)
2. The app renders beneath the current prompt position
3. Frames are rendered as styled text with ANSI escape sequences
4. Each frame ends with a cursor repositioning escape code that moves the cursor back to the start of the frame
5. Subsequent frames overwrite previous content
6. When frames shrink, an escape code clears lines from cursor downward

### Mouse Handling

Mouse events work in inline mode, but with a complication:
- Mouse coordinates are relative to the **terminal top-left** (0,0)
- The app needs to know where it was rendered (its origin)
- Textual queries the terminal for cursor position via an escape code
- App-relative coordinates are calculated by subtracting the origin

### What Works

- Widgets render and are interactive
- Mouse events are captured and routed to widgets
- Keyboard events work normally
- CSS styling works (with `:inline` pseudo-selector for inline-specific styles)
- Height can be controlled: `height: 50vh`, `max-height`, etc.
- `dock: bottom` for sticky footer widgets
- Default padding (1 line above + borders) can be removed with `INLINE_PADDING = 0`

### What Does NOT Work

1. **Windows is not supported.** Inline mode relies on `termios`, which is Unix-only. There is no official workaround. A community fork has "rudimentary" Windows inline support but it is not production-ready.

2. **Interactive widget lag (fixed in 0.56.3).** Versions prior to 0.56.3 had severe lag with Checkbox, Input, and other interactive widgets in inline mode. This was fixed, but suggests the inline rendering path is less battle-tested than fullscreen.

3. **Command palette incompatibility.** The command palette does not work well in inline mode (Issue #4385).

4. **Fixed height.** The inline app occupies a fixed portion of the terminal (e.g., `50vh`). It cannot dynamically grow to fill available space as content accumulates. Content that exceeds the frame height must be scrolled *within the app*, not in the terminal scrollback.

5. **Mouse capture.** Textual captures mouse events in inline mode (it must, to route them to widgets). This means **the terminal cannot handle mouse-based text selection** within the app area. This is a fundamental limitation -- any framework that needs mouse events for widgets will have this problem.

6. **No scrollback integration.** Content that scrolls past the top of the inline app frame is gone -- it does not enter the terminal scrollback. This is the opposite of how Claude Code and Aider work.

### `inline=True` vs `inline=False` Summary

| Feature | `inline=False` (fullscreen) | `inline=True` (inline) |
|---------|---------------------------|----------------------|
| Screen mode | Alternate screen buffer | Main buffer, below prompt |
| Terminal scrollback | Not accessible | Accessible *above* the app |
| App content scrollback | Managed by Textual | Managed by Textual |
| Mouse events | Captured by Textual | Captured by Textual |
| Text selection | Not native | Not native (in app area) |
| Widget interactivity | Full | Full (with caveats) |
| Windows support | Yes | **No** |
| Height | Full terminal | Configurable (e.g., 50vh) |
| Borders | App-managed | Default top+bottom borders |

### Critical Insight

Textual inline mode does NOT achieve what Claude Code achieves. Textual inline mode is a **fixed-size widget embedded in the terminal**, not a **stream of content that joins the scrollback**. This is a fundamental architectural difference:

- **Claude Code:** Output becomes part of scrollback. Older content scrolls up naturally. Terminal handles everything above the current "frame."
- **Textual inline:** The app is a fixed-height box. Content inside the box is managed by Textual. Nothing from the app enters the terminal scrollback.

---

## 7. prompt_toolkit -- Deep Dive

### Core Features for REPL Building

prompt_toolkit is the library behind IPython, AWS CLI, pgcli, and many other Python REPL tools. Key features:

1. **`PromptSession`**: Manages interactive input with history, completion, validation
2. **`patch_stdout`**: Context manager that ensures all `print()` calls appear *above* the active prompt, preserving the input line
3. **`print_formatted_text`**: Renders styled text above the current prompt
4. **`prompt_async()`**: Async version of prompt that integrates with asyncio
5. **Layout system**: HSplit/VSplit/FloatContainer for building full-screen apps
6. **Full-screen mode**: Optional, via `full_screen=True` parameter

### The patch_stdout Pattern (Critical for Streaming)

```python
async def main():
    session = PromptSession()
    with patch_stdout():
        # Background tasks can print() freely -- output appears above the prompt
        background_task = asyncio.create_task(stream_llm_output())
        result = await session.prompt_async(">>> ")
```

When `patch_stdout()` is active:
- Any `print()` call from any coroutine appears **above** the prompt line
- The prompt line is re-rendered below the new output
- The user can keep typing while output streams above

This is exactly the pattern needed for streaming LLM output while maintaining an input bar.

### Limitations

1. **No persistent status bar.** prompt_toolkit's inline mode has no concept of a sticky status bar. The prompt is the only persistent element. (Full-screen mode can have one, but then you lose scrollback.)

2. **No interactive widgets during streaming.** You cannot show an approval prompt *while* output is streaming. The prompt blocks (even `prompt_async` blocks the user's perspective -- they either see the prompt or they don't).

3. **Output is plain text.** While `print_formatted_text` supports styled text, it does not support Rich's Markdown rendering, tables, or syntax highlighting directly. You would need to render Rich output to ANSI text first, then print it.

4. **Windows support is good.** prompt_toolkit has a Win32 output backend and works well on Windows.

### Can prompt_toolkit + Rich Work Together?

Yes. The pattern:

```python
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

console = Console()

async def stream_response(text):
    # Rich renders to string, then prints to stdout
    # patch_stdout ensures it appears above the prompt
    console.print(Markdown(text))

async def main():
    session = PromptSession(">>> ")
    with patch_stdout():
        while True:
            user_input = await session.prompt_async()
            # Start streaming in background
            await stream_response(llm_response)
```

Rich's `Console` can be configured to output ANSI-styled text to stdout, and `patch_stdout` will capture it and render it above the prompt. This is essentially what Aider does.

---

## 8. The Two Paradigms: Inline vs Fullscreen

### Inline/Streaming (Claude Code, Aider, pi)

**How it works:**
- Content is appended to the terminal scrollback buffer
- Cursor repositioning is used only for the "active frame" (input bar, currently-streaming response)
- Once a response is complete, it becomes part of permanent scrollback
- Differential rendering updates only the changing portion

**User experience:**
- Scroll up in the terminal to see old conversation
- Cmd+F / Ctrl+Shift+F to search through history
- Select text with mouse normally
- Copy/paste works natively
- Feels like a natural terminal program (git log, man pages, etc.)

### Fullscreen TUI (Codex CLI Rust, OpenCode, Amp)

**How it works:**
- Enters alternate screen buffer
- Entire viewport is a character cell grid managed by the framework
- Custom scrolling, custom text selection (if any)
- On exit, returns to main buffer (conversation history is gone)

**User experience:**
- Clean, polished UI with panels and borders
- Custom keyboard shortcuts for everything
- Mouse captured by the app (no native text selection)
- Cannot search terminal scrollback
- History lost on exit (unless exported)
- Feels like a mini-IDE in the terminal (vim, htop, etc.)

### Industry Trend

The author of "pi" (a minimal coding agent) observes:

> "One approach to building terminal user interfaces is to take ownership of the terminal viewport and treat it like a pixel buffer. [...] These are called full screen TUIs, and Amp and opencode use this approach."
>
> "The other approach, used by claude code, codex, and Droid, is the streaming/inline approach. Content is appended to the scrollback buffer with occasional cursor repositioning."

The inline approach is winning among AI coding tools. Claude Code (the market leader) uses it. The original Codex CLI (TypeScript) used it. Droid uses it. The tools that went fullscreen (Amp, OpenCode) are seen as having a less natural terminal experience.

---

## 9. What Makes Claude Code Feel "Inline"

The specific technical choices that give Claude Code its inline feel:

1. **No alternate screen.** The main terminal buffer is used throughout.

2. **No mouse capture.** The terminal handles mouse events natively. Users can select text, scroll, and right-click as normal.

3. **No box-drawing characters or borders around the main content area.** The chat history looks like styled text, not a UI panel. (The input bar does have a subtle visual treatment, but it is minimal.)

4. **Output becomes scrollback.** When Claude finishes a response, the response text becomes part of the terminal's scrollback history. You can scroll up and see it just like any other terminal output.

5. **Streaming text appears character-by-character.** During generation, text appears incrementally, like watching a program print to stdout. This is not a TUI widget being updated -- it is actual text being written to the terminal.

6. **The input bar repositions using cursor escape codes.** After each frame, the cursor moves to the correct position for the input area. The input area is always at the bottom of the visible region.

7. **Minimal chrome.** No thick borders, no panel titles, no scrollbar widgets. The only visual elements are the input bar, a status line, and the streaming response text.

---

## 10. Hybrid Approaches

### Option A: Rich + prompt_toolkit (The Aider Model)

```
+--------------------------------------------------+
| $ hybridcoder                                     |  <-- terminal prompt
|                                                   |
| [system] Session started. Model: qwen3-8b         |  <-- Rich styled output
|                                                   |
| You: Fix the login bug in auth.py                 |  <-- prompt_toolkit input
|                                                   |
| Assistant:                                        |  <-- Rich Markdown output
| I'll look at the authentication module...         |     (streaming)
|                                                   |
| ```python                                         |
| def login(user, password):                        |     Rich syntax highlighting
|     ...                                           |
| ```                                               |
|                                                   |
| [tool] read_file("auth.py") -- approve? [Y/n/a]  |  <-- Rich styled prompt
|                                                   |
| >>> _                                             |  <-- prompt_toolkit input
+--------------------------------------------------+
```

**Implementation:**
- `prompt_toolkit.PromptSession` for the input bar
- `rich.Console.print()` for all output
- `patch_stdout()` for streaming output above the prompt
- Rich `Markdown`, `Syntax`, `Table` for formatted content
- Custom approval prompt using `prompt_toolkit.shortcuts.confirm()` or Rich `Prompt`

**Supports:**
- Streaming: Yes (via `patch_stdout` + async print)
- Approval prompts: Yes (Rich Prompt or prompt_toolkit confirm)
- Option selectors: Yes (prompt_toolkit `radiolist_dialog` or custom)
- Thinking tokens: Yes (Rich styled text, toggled by flag)
- @file completion: Yes (prompt_toolkit `Completer`)
- Persistent input: Yes (prompt_toolkit manages it)
- Mouse text selection: Yes (no mouse capture)
- Scrollback: Yes (all output is in scrollback)
- Windows: Yes (both libraries support Windows)

**Does NOT support:**
- Persistent status bar (without going full-screen)
- Interactive widgets *during* streaming (approval must wait for stream to finish, or stream must be paused)
- Live-updating progress within previous output (e.g., spinner that updates in-place)

### Option B: Textual Fullscreen with Inline-Like Styling

Keep the current Textual architecture but style it to feel less like a TUI:

- Remove borders and box-drawing characters
- Use minimal chrome
- Make the chat area look like plain text
- Only the input bar and status bar have visual treatment

**Supports:**
- All interactive features (approval prompts, option selectors, etc.)
- Persistent status bar
- Live-updating widgets
- Streaming within a widget

**Does NOT support:**
- Native text selection
- Terminal scrollback integration
- Terminal search
- Windows inline mode (fullscreen only)

### Option C: Dual-Mode Architecture

Support both rendering modes:

```python
if args.fullscreen or platform == "win32":
    # Textual fullscreen mode (current architecture)
    app = HybridCoderApp()
    app.run()
else:
    # Inline mode (Rich + prompt_toolkit)
    repl = HybridCoderREPL()
    repl.run()
```

This is more work but gives users the best of both worlds. The Textual fullscreen mode works for users who prefer a polished TUI (and is required on Windows). The inline mode works for users who prefer a native terminal feel.

### Option D: Custom Differential Renderer (Claude Code Approach)

Build a custom renderer that:
- Maintains a "frame" buffer for the active area (input bar + current response)
- Uses differential rendering to update only changed cells
- Uses synchronized output (DEC 2026) for flicker prevention
- Lets completed responses scroll into terminal scrollback

This is the most engineering-heavy option but produces the best UX. It is what Claude Code and "pi" both do.

**For Python, this would involve:**
- A screen buffer (2D array of styled cells)
- A diff function that compares old and new buffers
- ANSI escape code generation for cursor movement and styling
- Integration with Rich for content rendering (render to buffer, not to stdout)
- A custom input handler (could still use prompt_toolkit under the hood)

---

## 11. Recommendations for HybridCoder

### Primary Recommendation: Rich + prompt_toolkit Inline Mode (Option A)

**Rationale:**

1. **Edge computing first.** HybridCoder targets consumer hardware. A lightweight rendering approach (no Textual framework overhead) fits the resource-conscious philosophy.

2. **Cross-platform.** Rich and prompt_toolkit both support Windows, macOS, and Linux. Textual inline mode does not support Windows.

3. **Proven pattern.** Aider (the most popular open-source AI coding CLI) uses this exact approach. It works.

4. **Native terminal feel.** This is what users of CLI tools expect. Claude Code's success is partly due to its inline feel.

5. **Simpler architecture.** Rich + prompt_toolkit is significantly less code than Textual or a custom renderer.

6. **Memory efficient.** No Textual event loop, widget tree, or CSS engine running. Just print and prompt.

### Implementation Strategy

#### Phase 1: Core REPL

```python
# Simplified architecture
class HybridCoderREPL:
    def __init__(self):
        self.console = Console()
        self.session = PromptSession(
            completer=HybridCoderCompleter(),  # @file, /commands
            history=FileHistory(".hybridcoder/history"),
            key_bindings=create_keybindings(),
        )

    async def run(self):
        with patch_stdout():
            while True:
                user_input = await self.session.prompt_async(">>> ")
                await self.handle_input(user_input)

    async def handle_input(self, text):
        if text.startswith("/"):
            await self.handle_command(text)
        else:
            await self.stream_response(text)

    async def stream_response(self, text):
        async for chunk in self.agent.run(text):
            # Rich renders markdown incrementally
            # patch_stdout ensures it appears above prompt
            self.console.print(chunk, end="")
```

#### Phase 2: Approval Prompts

For tool approval, pause the streaming and show a Rich-styled prompt:

```python
async def request_approval(self, tool_name, args):
    self.console.print(
        f"[bold yellow]Tool:[/] {tool_name}",
        f"[dim]{json.dumps(args, indent=2)}[/]"
    )
    # Use prompt_toolkit for the approval input
    result = await self.session.prompt_async(
        "[Y/n/a] ",
        validator=ApprovalValidator(),
    )
    return result
```

#### Phase 3: Status and Progress

For status indicators during streaming, use Rich's `Status` or `Live` context:

```python
async def stream_response(self, text):
    with self.console.status("[bold green]Thinking..."):
        first_chunk = await self.agent.get_first_chunk(text)

    # Then stream the rest
    async for chunk in self.agent.stream(text):
        self.console.print(chunk, end="")
```

### Handling Current Textual Features

Map each current Textual feature to the Rich + prompt_toolkit equivalent:

| Textual Feature | Rich + prompt_toolkit Equivalent |
|-----------------|----------------------------------|
| Chat pane (ScrollableContainer) | Rich Console.print() to stdout (becomes scrollback) |
| Input bar (TextArea/Input) | prompt_toolkit PromptSession |
| Status bar | Rich Status / console.print() before prompt |
| Approval prompt (ApprovalPrompt widget) | prompt_toolkit confirm/custom prompt |
| Option selector (OptionSelector widget) | prompt_toolkit radiolist_dialog or numbered list |
| Slash commands | prompt_toolkit Completer + command handler |
| @file completion | prompt_toolkit Completer with fuzzy matching |
| Markdown rendering | Rich Markdown class |
| Syntax highlighting | Rich Syntax class |
| Diff preview | Rich Syntax with diff lexer |
| Thinking tokens | Rich styled text (dim/italic), toggleable |
| Streaming | Rich Live display or incremental print |
| Session list (/sessions) | Rich Table |
| Copy (/copy) | pyperclip + content from session DB |

### What We Lose (and Mitigations)

| Lost Feature | Mitigation |
|-------------|------------|
| Persistent status bar | Print status line before each prompt; or use Rich Status during operations |
| Live-updating spinners during streaming | Rich Live context for the streaming area |
| Interactive widgets during streaming | Pause stream, show prompt, resume -- this is acceptable UX |
| Header with model info | Print on startup and after /model changes |
| Borders/panels | Intentionally removed -- this is the inline feel |
| Mouse events for UI | Not needed -- terminal handles mouse natively |

### Fallback: Keep Textual as Optional Mode

```
hybridcoder              # Default: inline mode (Rich + prompt_toolkit)
hybridcoder --tui        # Optional: fullscreen Textual TUI
hybridcoder --tui-inline # Optional: Textual inline mode (Unix only)
```

This preserves all the Textual work done in Phase 2 while adding the inline mode that most users will prefer.

### Future: Custom Renderer (Phase 5+)

If the Rich + prompt_toolkit approach feels too limited (e.g., no live-updating status during streaming), consider building a lightweight custom differential renderer as a Phase 5+ enhancement. The key components would be:

1. A "frame" buffer for the active area only (not the full terminal)
2. Cell-based diffing between frames
3. DEC mode 2026 synchronized output
4. Rich as the content renderer (render to string, then to frame buffer)
5. prompt_toolkit or raw stdin for input handling

This would achieve Claude Code-level smoothness without the complexity of a full TUI framework.

---

## 12. Sources

### Claude Code
- [Claude Code Internals, Part 11: Terminal UI (Medium)](https://kotrotsos.medium.com/claude-code-internals-part-11-terminal-ui-542fe17db016)
- [The Signature Flicker (Peter Steinberger)](https://steipete.me/posts/2025/signature-flicker)
- [Claude Chill: Fix Claude Code's flickering (Hacker News)](https://news.ycombinator.com/item?id=46699072)
- [Profiling Claude Code Part 2: Do Androids Dream of O(n) Diffs?](https://dev.to/vmitro/i-profiled-claude-code-some-more-part-2-do-androids-dream-of-on-diffs-2kp6)
- [Claude Code Terminal Config Docs](https://code.claude.com/docs/en/terminal-config)
- [Claude Code GitHub Issues: #8618, #14599, #14208](https://github.com/anthropics/claude-code/issues)

### Codex CLI
- [Codex CLI GitHub](https://github.com/openai/codex)
- [TUI Implementation DeepWiki](https://deepwiki.com/oaiagicorp/codex/3.2-tui-implementation)
- [Codex CLI Going Native Discussion](https://github.com/openai/codex/discussions/1174)

### Aider
- [Aider io.py Source](https://github.com/Aider-AI/aider/blob/main/aider/io.py)
- [Aider CLI DeepWiki](https://deepwiki.com/helloandworlder/aider/5.1-command-line-interface)
- [Aider GitHub](https://github.com/Aider-AI/aider)

### Textual
- [Behind the Curtain of Inline Terminal Applications (Textual Blog)](https://textual.textualize.io/blog/2024/04/20/behind-the-curtain-of-inline-terminal-applications/)
- [Textual App Basics](https://textual.textualize.io/guide/app/)
- [Style Inline Apps](https://textual.textualize.io/how-to/style-inline-apps/)
- [Inline Widget Lag Issue #4403](https://github.com/Textualize/textual/issues/4403)
- [Windows Inline Support Issue #4409](https://github.com/Textualize/textual/issues/4409)

### prompt_toolkit
- [prompt_toolkit Documentation](https://python-prompt-toolkit.readthedocs.io/)
- [prompt_toolkit GitHub](https://github.com/prompt-toolkit/python-prompt-toolkit)
- [Async Prompt Example](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/examples/prompts/asyncio-prompt.py)
- [ptpython (Better Python REPL)](https://github.com/prompt-toolkit/ptpython)

### Other
- [What I Learned Building a Minimal Coding Agent (mariozechner.at)](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [OpenCode GitHub](https://github.com/opencode-ai/opencode)
- [Terminal Spec: Synchronized Output](https://gist.github.com/christianparpart/d8a62cc1ab659194337d73e399004036)
- [Bubble Tea GitHub](https://github.com/charmbracelet/bubbletea)
- [Ratatui GitHub](https://github.com/ratatui/ratatui)
