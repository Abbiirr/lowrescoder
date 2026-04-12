# Claude Code Visual Parity — UI Specification

> Target: Make AutoCode's primary full-screen terminal experience closely match Claude Code's look and feel.
> Policy: Primary full-screen TUI first. Existing inline/Textual `claude_like` work is useful scaffolding, not the completion gate for this pass.
> Rollout: Behind `claude_like` UI profile flag until focused render tests, manual smokes, and review gates all pass.

## Current Position

What already exists:
- `claude_like` profile exists in config
- inline and Textual already have partial Claude-like styling and snapshots
- Go TUI already has thinking, status bar, approval, and streaming primitives

What is still open:
- the primary TUI does not yet feel close enough to Claude Code structurally
- the spec needs to reflect newer Claude Code behavior signals from the local changelog
- completion should be based on explicit render states and review gates, not on the existence of a profile flag

## Reference: Claude Code Terminal Layout

### Header Block
```
╭─────────────────────────────────────────╮
│  ◆ Claude Code                          │
│  /help for help                         │
╰─────────────────────────────────────────╯
```
- Accent diamond icon (◆) in brand color
- Product name in bold
- Subtle help hint below

### Prompt
```
❯ _
```
- Single `❯` character as prompt prefix
- No model/mode decoration in the prompt itself
- Clean, minimal

### Status Bar (bottom)
```
 claude-sonnet-4-20250514 · 1.2k tokens · $0.02 · auto
```
- Model name · token count · cost · permission mode
- Dim/muted color
- Updates in real-time during streaming
- Survives narrow terminals without wrapping into visual noise
- Can also carry lightweight background-task / PR-state indicators when present

### Thinking Indicator
```
 ⠋ Thinking...
```
- Animated braille spinner
- Muted color
- Stable width so the layout does not jitter when it appears/disappears
- Replaced by response when done
- Wording should support “thinking” / “thought for Ns” / effort-like variants without changing layout width

### Tool Call Row
```
 ⎿ Read file: src/main.py
 ⎿ Edit file: src/utils.py (+12 -3)
 ⎿ Run: pytest -x
   ✓ 42 passed
```
- `⎿` prefix for tool calls (continuation bracket)
- Tool name in bold, arguments in normal weight
- Result summary inline (compact)
- Checkmark for success, ✗ for failure
- Repeated read/search activity should collapse/group where sensible
- Tool rows should avoid blank-line churn during streaming

### Assistant Response
```
I've updated the function to handle edge cases. The key changes:

1. Added null check on line 15
2. Fixed the off-by-one error in the loop
3. Added a test for the new behavior
```
- No special prefix — just text
- Markdown rendered inline
- Code blocks with syntax highlighting

### Approval Prompt
```
 Allow Edit to src/main.py? [y/n/a]
```
- Clear action description
- Single-key response options

## Explicit Non-Goals

- Do not turn the TUI into a multi-pane dashboard like Pi.
- Do not add project/session sidebars in this parity pass.
- Do not broaden this work into external-harness orchestration UI.

## Render States That Must Be Reviewed

- fresh session / welcome
- idle prompt
- visible thinking
- streaming answer
- compact tool call success
- compact tool call failure
- approval prompt
- narrow-terminal footer
- long-path / long-command row
- background-task indicator when present

## Token Mapping: AutoCode → Claude Code

### Colors
| Token | Current AutoCode | Target (Claude Code) |
|-------|-----------------|---------------------|
| `--color-accent` | (none) | `#cc7832` (amber/orange) |
| `--color-primary` | default terminal | white/bright |
| `--color-muted` | `ansibrightblack` | `ansibrightblack` (dim gray) |
| `--color-success` | (none) | `ansigreen` |
| `--color-error` | `ansired` | `ansired` |
| `--color-warning` | `ansiyellow` | `ansiyellow` |

### Typography
| Token | Current | Target |
|-------|---------|--------|
| `--prompt-prefix` | `❯` | `❯` (already matching) |
| `--tool-prefix` | (varies) | `⎿` |
| `--thinking-spinner` | `dots` | braille spinner (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) |
| `--separator` | `─` repeated | thin horizontal rule |

### Layout
| Token | Current | Target |
|-------|---------|--------|
| `--header-style` | Rich panel with version/model/mode | Minimal boxed header with icon |
| `--status-position` | Right-side rprompt | Bottom status bar |
| `--tool-density` | Full output shown | Compact: name + args + result summary |
| `--response-prefix` | (none) | (none) — matches |

## Implementation Zones

### Zone 1: Header
- Keep header minimal and non-dominating
- Show a compact branded identifier plus lightweight help hint
- Do not use a heavy dashboard frame

### Zone 2: Prompt
- Keep `❯`
- Avoid putting mode/model clutter directly into the prompt line
- Preserve clean input focus

### Zone 3: Status Bar / Footer
- Footer is the main live-status surface
- Model · tokens · cost · permission mode remain the baseline contract
- Updates on tool calls / LLM responses must not cause layout jitter
- Handle narrow width deliberately

### Zone 4: Tool Call Display
- Use `⎿ ToolName: args`
- Keep result summaries adjacent and compact
- Collapse or group repetitive low-value read/search activity where possible
- Avoid expanding large tool outputs inline by default

### Zone 5: Thinking
- Braille/shimmer spinner with stable width
- Muted styling
- Minimal text churn while the model is reasoning
- Thinking visibility must coexist with streaming text safely

### Zone 6: Approval
- Keep approvals terse and obvious
- Make the action, target, and key choices readable at terminal speed
- No bulky framing unless the prompt would otherwise be ambiguous

## Acceptance Rubric

Each zone scored independently:
- **Match**: Layout, spacing, and color are indistinguishable at normal terminal distance
- **Close**: Same structure/hierarchy, minor color/spacing differences
- **Different**: Visibly different structure or behavior

Target: all zones at **Close** or better.

## Verification and Completion Gates

Do not call this work complete until all of the following are true:

1. The spec reflects the current intended Claude-like behavior.
2. Focused render/snapshot/string-contract coverage exists for every required render state.
3. Existing TUI regression suites stay green.
4. Manual smoke artifacts are stored for:
   - 80-column terminal
   - 120+ column terminal
   - visible thinking + streaming in one turn
   - long file path / long command row
5. A review pass judges every zone `Close` or better.
6. Only after the above can `claude_like` be considered for promotion beyond a gated profile.

## Files to Modify

### Primary Full-Screen TUI (first target)
- `autocode/cmd/autocode-tui/styles.go`
- `autocode/cmd/autocode-tui/view.go`
- `autocode/cmd/autocode-tui/statusbar.go`
- `autocode/cmd/autocode-tui/model.go`
- `autocode/cmd/autocode-tui/update.go`
- `autocode/cmd/autocode-tui/view_test.go`
- `autocode/cmd/autocode-tui/statusbar_test.go`
- `autocode/cmd/autocode-tui/update_test.go`
- `autocode/cmd/autocode-tui/e2e_test.go`

### Inline/Textual (reference / follow-up alignment)
- `autocode/src/autocode/inline/app.py`
- `autocode/src/autocode/inline/renderer.py`
- `autocode/src/autocode/tui/app.py` — header, layout
- `autocode/src/autocode/tui/widgets/chat_view.py` — tool calls, messages
- `autocode/src/autocode/tui/widgets/status_bar.py` — bottom status
- `autocode/src/autocode/tui/widgets/input_bar.py` — prompt
- `autocode/src/autocode/tui/styles.tcss` — color tokens

### Config
- `autocode/src/autocode/config.py` — UIProfile enum (default / claude_like)
