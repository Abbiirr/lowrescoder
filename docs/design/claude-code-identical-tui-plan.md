# Plan: Make AutoCode TUI Identical to Claude Code

> Source: studied `claude-code-sourcemap/src/`, `claw-code/`, `claude-code/`

## Architecture Difference

Claude Code uses **Ink** (React for terminals, Node.js). AutoCode uses **prompt_toolkit** (Python).
This means we can't copy components directly — we must translate the visual output.

## Current vs Target (side by side)

### Welcome Screen

**Current AutoCode:**
```
╭──────────────────────────────────────────────╮
│ ✻ Welcome to AutoCode!                       │
│                                               │
│   /help for help                              │
│                                               │
│   cwd: ~/projects/myapp                       │
╰──────────────────────────────────────────────╯
> █
```

**Claude Code (target):**
```
╭──────────────────────────────────────────────╮
│ ✻ Welcome to Claude Code!                    │
│                                              │
│   /help for help                             │
│                                              │
│   cwd: ~/projects/myapp                      │
╰──────────────────────────────────────────────╯

╭──────────────────────────────────────────────╮
│ >                                            │
╰──────────────────────────────────────────────╯
  ! for bash  ·  / for commands  ·  esc to undo
```

### Differences to Fix

| # | What | Current | Target | File | Fix |
|---|------|---------|--------|------|-----|
| 1 | Prompt box | No border | Rounded border `╭╮╰╯` in `#888` | `app.py` | Print borders around prompt |
| 2 | Prompt char | `>` bare | `>` inside border box, 3-char wide (` > `) | `app.py` | Already `>`, add padding |
| 3 | Hint line | Missing | `! for bash · / for commands · esc to undo` dim | `app.py` | Print after bottom border |
| 4 | Spacing | No gap between welcome and prompt | `marginTop=1` (blank line) | `app.py` | Add `console.print()` |
| 5 | Tool dot blink | Static ● | Blinks every 600ms | `renderer.py` | Can't animate in Rich (static output) |
| 6 | Spinner animation | Static `✻ Verb…` | Cycles `·✢✳∗✻✽` at 120ms + elapsed time | `renderer.py` | Can't animate in Rich |
| 7 | User turn | `> text` in dim | `> text` in `#999` with 2-char prefix box | `renderer.py` | Already close |
| 8 | Assistant text | Plain markdown | `● text` with 2-char dot prefix | `renderer.py` | Add dot prefix |
| 9 | Tool result | `⎿  result` | `  ⎿  result` (2-space indent + ⎿ + nbsp) | `renderer.py` | Already close |
| 10 | Turn spacing | `───` separator | `marginTop=1` (blank line, no `───` bar) | `renderer.py` | Replace separator with blank line |

## Implementation Plan

### Fix 1: Prompt Box Border (app.py)

The prompt input must sit inside `╭──╮ / ╰──╯` borders.

**Problem:** `prompt_toolkit` manages its own rendering area. We can't wrap its output in Rich borders because they're different rendering systems.

**Solution:** Print borders via Rich, the prompt renders between them visually.

```python
# In _run_sequential(), before prompt_async():
def _print_prompt_border(self, top=True):
    if self.config.ui.profile != "claude_like":
        return
    w = self.renderer._explicit_console_width() - 1
    c = "╭" if top else "╰"
    self.renderer.console.print(f"[dim #888]{c}{'─' * (w - 2)}[/]")

# Before prompt:
self._print_prompt_border(top=True)
text = await prompt_session.prompt_async(input_prompt)
self._print_prompt_border(top=False)
```

**Issue:** With `erase_when_done=True`, the top border gets erased too. 
**Workaround:** Set border color dim enough that the erase is acceptable, OR remove `erase_when_done` and manually handle scrollback.

### Fix 2: Spacing Between Welcome and Prompt

```python
# After print_welcome(), add a blank line:
self.console.print()  # marginTop=1 equivalent
```

### Fix 3: Hint Line Below Prompt

```python
def _print_prompt_hints(self):
    if self.config.ui.profile != "claude_like":
        return
    self.renderer.console.print(
        "[dim]  ! for bash  ·  / for commands  ·  esc to undo[/]"
    )
```

### Fix 4: Replace Turn Separators with Blank Lines

Claude Code does NOT use `───` horizontal bars between turns. It uses `marginTop=1` (blank line spacing).

```python
def print_turn_separator(self):
    if getattr(self, "_profile", "default") == "claude_like":
        self.console.print()  # Just a blank line
    else:
        self.print_separator()  # Original ─── bar
```

### Fix 5: Assistant Text with ● Dot Prefix

Claude Code shows assistant text with a leading `●` dot:

```python
def print_assistant_message(self, content, profile="default"):
    self.console.print()
    if profile == "claude_like":
        # Dot prefix like Claude Code
        from rich.columns import Columns
        self.console.print(f"● ", end="")
    self.console.print(Markdown(content))
    self.console.print()
```

### Fix 6: Animation Limitations

Claude Code's ● dot blinks (600ms) and spinner cycles (120ms). Rich/prompt_toolkit can't do real-time animation in the scrollback area. 

**Acceptable compromise:**
- Tool dots: static colored ● (green/red/gray) — already done
- Spinner: static `✻ Verb…` — already done
- These are cosmetic and don't affect functionality

### Fix 7: Border Color for Prompt Box

Claude Code uses `#888` (secondaryBorder) for normal mode, `#fd5db1` (bashBorder) for bash mode.

```python
border_color = "#fd5db1" if bash_mode else "#888"
self.renderer.console.print(f"[{border_color}]╭{'─' * w}╮[/]")
```

## Priority Order

1. **Replace `───` separator with blank line** — Trivial, high impact
2. **Add prompt box borders** — Medium effort, high visual impact
3. **Add hint line** — Trivial
4. **Add ● prefix to assistant text** — Trivial
5. **Fix spacing (marginTop=1)** — Trivial
6. **Border colors (#888, #fd5db1)** — Trivial

## Files to Modify

| File | Changes |
|------|---------|
| `autocode/src/autocode/inline/renderer.py` | Turn separator → blank line, assistant ● prefix |
| `autocode/src/autocode/inline/app.py` | Prompt borders, hint line, spacing |
| `autocode/tests/unit/test_inline_renderer.py` | Update assertions |
| `autocode/tests/unit/test_inline_app.py` | Update assertions |

## What We Cannot Match (Ink vs prompt_toolkit)

1. **Real-time animation** — Ink re-renders React components at 120ms; Rich prints are static
2. **Box-drawing around live input** — Ink wraps the text input in a Box component; prompt_toolkit manages its own area
3. **Transient vs static messages** — Ink separates streaming (transient) from completed (static) messages with different render paths
4. **React component tree** — Ink composes UI from reusable components; our Rich output is imperative print statements

These are architectural differences. For visual parity, the static output (what the user sees after each interaction) can be made identical. The dynamic rendering (animations during streaming) will differ.
