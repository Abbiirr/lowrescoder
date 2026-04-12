# Claude Code Visual Parity — Gap Analysis & Fix Plan

## Current State (AutoCode screenshot)

```
◆ AutoCode v0.1.0
  /help for help
───────────────────────────────────────────────────────────────
❯ █                                          tools · suggest
```

## What Claude Code Actually Looks Like

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
  ! for bash · / for commands · esc to undo
```

## Gap List

### 1. Welcome Box — Missing Rounded Border

**Current:** Plain text header with a `───` separator line.
**Claude Code:** Rounded-border box (`╭╮╰╯│─`) with `#D97757` terracotta orange border.

**Fix in `autocode/src/autocode/inline/renderer.py`:**

```python
def print_welcome(self, model, provider, mode, profile="default"):
    from autocode import __version__
    
    if profile == "claude_like":
        width = max(46, len(str(Path.cwd())) + 12)
        border = "─" * (width - 2)
        cwd = str(Path.cwd())
        self.console.print(f"[#D97757]╭{border}╮[/]")
        self.console.print(f"[#D97757]│[/] [bold #D97757]✻[/] [bold]Welcome to AutoCode![/]{' ' * (width - 25)}[#D97757]│[/]")
        self.console.print(f"[#D97757]│[/]{' ' * (width - 2)}[#D97757]│[/]")
        self.console.print(f"[#D97757]│[/]   [dim italic]/help for help[/]{' ' * (width - 19)}[#D97757]│[/]")
        self.console.print(f"[#D97757]│[/]{' ' * (width - 2)}[#D97757]│[/]")
        self.console.print(f"[#D97757]│[/]   [dim]cwd: {cwd}[/]{' ' * max(0, width - len(cwd) - 9)}[#D97757]│[/]")
        self.console.print(f"[#D97757]╰{border}╯[/]")
```

### 2. Logo Character — ◆ vs ✻

**Current:** `◆` (BLACK DIAMOND)
**Claude Code:** `✻` (TEARDROP-SPOKED ASTERISK) colored `#D97757`

**Fix:** Replace `◆` with `✻` everywhere.

```python
# renderer.py — change all ◆ to ✻
# Old:
self.console.print(f"[bold orange3]◆[/bold orange3] ...")
# New:
self.console.print(f"[bold #D97757]✻[/bold #D97757] ...")
```

### 3. Accent Color — orange3 vs #D97757

**Current:** `orange3` (Rich named color, approximately `#d78700`)
**Claude Code:** `#D97757` (terracotta orange)

**Fix:** Replace all `orange3` references with `#D97757`.

### 4. Prompt Character — ❯ vs >

**Current:** `❯` (HEAVY RIGHT-POINTING ANGLE QUOTATION MARK, green bold)
**Claude Code:** `>` (GREATER-THAN SIGN) inside a rounded-border box

**Fix in `autocode/src/autocode/inline/app.py`:**

```python
# Current prompt:
message = [("fg:ansigreen bold", "❯ ")]

# Claude Code parity:
message = [("fg:ansiwhite", "> ")]
```

### 5. Prompt Box — Missing Rounded Border

**Current:** Bare `❯` prompt with rprompt on right.
**Claude Code:** Prompt is inside a rounded-border box (`╭──╮ / ╰──╯`), border color `#888`.

This is the hardest to fix because `prompt_toolkit` doesn't natively support box-drawing around the input. Options:

**Option A — Rich pre-print (simpler, good enough):**
Print the top border before prompt, bottom border after input:
```python
# Before prompt_async():
self.renderer.console.print(f"[dim]╭{'─' * (width-2)}╮[/]")

# The prompt line renders inside the box visually
# After input captured:  
self.renderer.console.print(f"[dim]╰{'─' * (width-2)}╯[/]")
```

**Option B — prompt_toolkit multiline container (complex):**
Use `prompt_toolkit`'s `Frame` or custom `Window` with border. This requires significant refactoring of the PromptSession layout.

**Recommendation:** Option A for now.

### 6. Hint Line Below Prompt — Missing

**Current:** No hint line.
**Claude Code:** Shows `! for bash mode · / for commands · esc to undo` in dim text below the prompt box.

**Fix:** Print after the prompt box bottom border:
```python
self.renderer.console.print(
    "[dim]  ! for bash · / for commands · esc to undo[/]"
)
```

### 7. Tool Call Rendering — ⎿ Position & Dot Indicator

**Current:** `⎿ ✓ Read File src/main.py` (continuation bracket, inline icon, title-cased)
**Claude Code:**
```
● Read(file_path: src/main.py)…
  ⎿  [result content]
```

Key differences:
- Claude uses `●` (BLACK_CIRCLE) before tool name, NOT `⎿`
- `⎿` is only for the **result** line, indented below
- Tool name is bold, followed by `(param: value)…`
- The dot blinks while running, turns green on success, red on error

**Fix in `renderer.py`:**
```python
if profile == "claude_like":
    # Tool invocation line
    if status in ("completed", "success"):
        dot = "[#4eba65]●[/]"
    elif status in ("error", "blocked"):
        dot = "[#ff6b80]●[/]"
    else:
        dot = "[dim]●[/]"
    
    display_name = tool_name.replace("_", " ").title()
    self.console.print(f"{dot} [bold]{display_name}[/]({result[:60]})…")
    
    # Result line (if result provided)
    if result and status in ("completed", "success"):
        self.console.print(f"  [dim]⎿[/]  {result[:80]}")
```

### 8. Thinking Indicator — Static vs Animated

**Current:** `⠋ Thinking...` (static braille frame)
**Claude Code:** `✻ Thinking…` with animated spinner cycling through `· ✢ ✳ ∗ ✻ ✽` at 120ms, plus elapsed time and "esc to interrupt" hint. The verb is randomly selected from 57 options ("Pondering", "Brewing", "Clauding", etc.)

**Fix in `renderer.py`:**
```python
import random

_THINKING_VERBS = [
    "Thinking", "Processing", "Pondering", "Computing",
    "Crafting", "Generating", "Working", "Brewing",
    "Cooking", "Synthesizing", "Ruminating", "Musing",
]

def print_thinking_indicator(self):
    if getattr(self, "_profile", "default") == "claude_like":
        verb = random.choice(_THINKING_VERBS)
        self.console.print(f"[#D97757]✻ {verb}…[/]")
    else:
        self.console.print("[dim italic]Thinking...[/dim italic]")
```

### 9. User Message in History — > Prefix

**Current:** User messages shown without prefix.
**Claude Code:** `> user message text` with `>` in gray, message in gray, wrapping to `columns - 4`.

**Fix in `renderer.py`:**
```python
def print_user_message(self, text, profile="default"):
    if profile == "claude_like":
        self.console.print(f"[dim]>[/] [dim]{text}[/]")
    else:
        self.console.print(f"[bold green]You:[/] {text}")
```

### 10. Status Display — Different Position

**Current:** Right-side rprompt showing `tools · suggest`.
**Claude Code:** No persistent status bar. Token warnings appear inline near the prompt hints only when context exceeds 60%.

**Fix:** This is acceptable as-is. Having a persistent status indicator is useful for AutoCode. Keep the rprompt but style it dimmer.

## Priority Order

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Welcome box with rounded border | Medium | High — first thing users see |
| 2 | `✻` instead of `◆`, color `#D97757` | Trivial | High — brand identity |
| 3 | `>` prompt instead of `❯` | Trivial | Medium — feels like Claude |
| 4 | Tool call rendering (● dot + ⎿ result) | Medium | High — visible every interaction |
| 5 | Thinking verb randomization | Trivial | Low — delightful detail |
| 6 | Prompt box border (╭──╮ / ╰──╯) | Hard | Medium — signature look |
| 7 | Hint line below prompt | Trivial | Low — discoverability |
| 8 | User message `>` prefix | Trivial | Low — conversation history |
| 9 | Color scheme alignment (#D97757, #4eba65, etc.) | Easy | Medium — consistency |

## Files to Modify

| File | Changes |
|------|---------|
| `autocode/src/autocode/inline/renderer.py` | Welcome box, ✻ logo, tool calls, thinking, user messages |
| `autocode/src/autocode/inline/app.py` | Prompt character `>`, hint line, prompt box borders |
| `autocode/src/autocode/tui/styles.tcss` | Color tokens: `$accent: #D97757`, `$success: #4eba65`, etc. |
| `autocode/cmd/autocode-tui/styles.go` | `welcomeStyle` color to `#D97757`, logo char to `✻` |
| `autocode/tests/unit/test_inline_renderer.py` | Update snapshot tests for new characters/colors |

## Color Token Mapping

| AutoCode Current | Claude Code | Semantic |
|-----------------|-------------|----------|
| `orange3` | `#D97757` | Brand accent (logo, spinner, welcome border) |
| `green` (✓) | `#4eba65` | Success (tool complete) |
| `red` (✗) | `#ff6b80` | Error (tool failed) |
| `yellow` (…) | `#ffc107` | Warning (token limit) |
| `dim` | `#999` | Secondary text |
| `ansigreen bold` (❯) | `#888 dim` (>) | Prompt character |
| N/A | `#b1b9f9` | Permission dialogs |
| N/A | `#fd5db1` | Bash mode (!  prefix) |
