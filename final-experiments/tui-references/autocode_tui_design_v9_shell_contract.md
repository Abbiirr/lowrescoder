# AutoCode Minimal TUI — v9 Shell Contract and Corrected Design Instructions

**Version:** v9.0  
**Product:** AutoCode coding-agent terminal UI  
**Primary users:** engineers migrating from Codex CLI, Claude Code, and other prompt-first coding agents  
**Primary implementation target:** Rust TUI over typed backend events  
**Companion artifact:** `autocode_tui_v9_corrected_static.html`  
**Screen export set:** `autocode_tui_v9_screens_png.zip`

This version converts the design from independent mock screens into a strict shell contract. The most important correction is that the composer and footer are owned by the application shell, not by individual screens. Focus modes replace only the middle region.

---

## 1. Product doctrine

AutoCode should be:

```text
Codex-simple by default
Claude-Code-stable while running
terminal-native under stress
AutoCode-powerful only when needed
```

Default UI should remain prompt-first, keyboard-first, and minimal. Do not make a permanent dashboard. Do not add always-visible rails for subagents, plans, risk, queue, or settings.

---

## 2. Non-negotiable shell contract

The app owns one canonical layout:

```text
AppShell
  Header / status                optional, one or two rows
  MainRegion                     transcript or focus mode
  Drawer                         optional, bounded
  QueueStrip                     optional, exactly one row
  Composer                       always present, exactly one live composer
  Footer                         always present, compact
```

Screens may replace only `MainRegion`, `Drawer`, and `QueueStrip`. Screens must not directly mount or unmount the live composer or footer.

### Required layout model

Use named grid areas or an equivalent terminal layout model:

```css
.shell-host {
  display: grid;
  grid-template-areas:
    "header"
    "content"
    "drawer"
    "queue"
    "composer"
    "footer";
  grid-template-rows:
    auto
    minmax(0, 1fr)
    auto
    auto
    auto
    auto;
  height: 100%;
}
.region-content { min-height: 0; overflow: hidden; }
```

The middle content region gets the flexible row. Composer and footer never get the flexible row.

### Required runtime invariant

```text
every visible app state has exactly one live composer
every visible app state has exactly one footer
focus modes replace only MainRegion
bounded drawers never push composer off-screen
queue strip is one line only
```

---

## 3. Composer contract

The composer is the primary user surface.

```text
Enter              send when idle, queue/send when agent is running
Tab                queue while agent is running
Ctrl+Enter         force send where terminal supports it
Shift+Enter        newline
Esc                cancel picker, blur focus mode, or interrupt depending state
/                  command picker attached to composer
@                  file picker attached to composer
#                  symbol picker attached to composer
Ctrl+O             copy latest completed output
Alt+O              transcript review
Alt+Q              queue drawer
Alt+D              live drawer
Ctrl+X Ctrl+E      open current draft in $EDITOR
```

### Focus safety rules

When composer focus is active:

```text
letters always edit text
Enter sends or queues text
single-key review/list actions are disabled
a/r/x/R never approve, reject, archive, delete, or restore
```

When review/list focus is active:

```text
single-key review/list actions may work
i returns focus to composer
footer must say FOCUS review or FOCUS list
composer remains visible but is not the active key target
```

Dangerous actions require explicit confirmation. This includes delete/archive, restore, broad approval scopes, remote actions, and any operation that escapes local reversible changes.

---

## 4. Submitted prompt versus live composer

Submitted prompts are transcript entries. They are not editable and must not reuse the live composer component.

Recommended grammar:

```text
> submitted user message

╭─ current instruction ───────────────────────────╮
│ › live editable text█                           │
╰─────────────────────────────────────────────────╯
```

The static HTML uses `.composer-box.live-composer` for the one live composer and `.draft-editor-box` for queued draft editing.

---

## 5. Queue contract

Queue item states:

```text
draft        local editable text, not queued
queued       will run next
blocked      waiting for condition
needs-review invalidated by restore/context change
submitted    immutable transcript entry
```

Do not count `[draft]` as queued. Use separate counts when necessary:

```text
q:2 · drafts:1
```

The collapsed queue strip is exactly one row and truncates rather than wraps.

The queue drawer may include a queued-draft editor, but that editor is not the live composer. It must use a distinct component/class and label.

---

## 6. Drawer contract

Drawers are bounded bottom regions. They are not overlays.

```text
default drawer height: 3–6 rows
expanded drawer max: 30–35% terminal height
internal scroll only
composer position unchanged
footer position unchanged
```

Use drawers for live command output, queue editing, stderr expansion, and selected tool output. Never dump large logs into transcript.

---

## 7. Approval and permission contract

Approval surfaces must be evidence-first and scoped.

Every approval panel must show:

```text
operation type
exact target
patch hash or command hash
requested by current turn / plan / tool
matched rule
policy source
network state
reversibility
expiration/scope
```

Prefer narrow scopes:

```text
approve this exact patch
approve this file for this turn
approve this command invocation
approve this MCP read call
```

Avoid broad scopes such as `approve session`. Protected path approval and remote/network approval are separate decisions.

---

## 8. Effective policy/status contract

`/status` and settings must show effective resolution, not vague source labels.

Required fields:

```text
model
reasoning/effort
mode
sandbox
cwd
branch/worktree dirty state
protected paths
queue state
context/cost
clipboard capability
network effective policy
MCP read/write policy
remote CI policy
settings precedence
policy source
ignored overrides
```

Recommended precedence:

```text
managed > command-line > local > project > user
```

If AutoCode intentionally differs, the UI must state the difference explicitly.

---

## 9. Copy/export contract

`Ctrl+O` copies the latest completed output. `/copy` can copy selected ranges, full transcript, diffs, command output, or exported files.

If direct clipboard copy is unavailable, the UI must show fallback paths and platform-specific commands:

```text
macOS:    pbcopy < .autocode/exports/latest-output.txt
Linux:    wl-copy < .autocode/exports/latest-output.txt
X11:      xclip -selection clipboard < .autocode/exports/latest-output.txt
Windows:  type .autocode\exports\latest-output.txt | clip
WSL:      clip.exe < .autocode/exports/latest-output.txt
```

---

## 10. Large paste contract

Large pastes must not auto-submit. Use bracketed paste and show a paste preview when content is large, multiline, or looks like logs/diffs/stack traces.

Required options:

```text
attach as paste-buffer file
summarize first
send raw anyway
cancel paste
```

The composer draft remains editable after paste preview.

---

## 11. Rendering and terminal requirements

Every screen must have a terminal column budget. Long table rows must truncate.

```text
80×24      mandatory fallback
120×40     default target
160×45     wide terminal target
```

Use terminal display width, not string length.

Required handling:

```text
wcwidth/grapheme measurement
CJK wide characters
emoji
combining marks
ANSI-colored segments
Powerline/Nerd Font glyphs
box drawing fallback
```

Use a double-buffered or diff-based render pipeline. Batch events and render full frames into a buffer before diffing to terminal.

Acceptance tests:

```text
resize from 160×45 → 80×24 → 120×40 preserves composer/footer
streaming output does not move composer y-position
drawer never exceeds max height
queue strip never wraps
wide rows truncate before terminal boundary
terminal crash/restore preserves draft and queue
```

---

## 12. Accessibility and fallback

The design must support:

```text
high-contrast mode
no-color mode
ASCII/no-glyph mode
screen-reader-friendly log export
keyboard-only operation
terminal selection/copy fallback
```

Do not rely on color alone. Every status must include text or glyph labels.

---

## 13. Screen inventory in the corrected HTML

| # | Screen id | Screen | Purpose |
|---:|---|---|---|
| 01 | `01_idle` | Ready / idle | minimal identity, composer owns focus |
| 02 | `02_active` | Active transcript | submitted prompt separated from live input |
| 03 | `03_drawer` | Active with bounded drawer | drawer cannot push composer |
| 04 | `04_queue_strip` | Multitasking with one-line queue | queue strip is fixed one line |
| 05 | `05_queue_drawer` | Queue drawer | queued draft editor is not the live composer |
| 06 | `06_slash_picker` | Composer-attached slash picker | no centered palette |
| 07 | `07_file_picker` | Composer-attached file picker | filter-first file attach |
| 08 | `08_symbol_picker` | Composer-attached symbol picker | symbol attach/jump without sidebar |
| 09 | `09_plan_inline` | Plan inline | plan visible only when useful |
| 10 | `10_review_approval` | Review approval | evidence-first approval; no hotkeys in composer focus |
| 11 | `11_diff_focus` | Diff focus | focus mode replaces middle only |
| 12 | `12_protected_path` | Protected path escalation | no broad approve-session action |
| 13 | `13_network_ci_denied` | Remote CI / network denied | separate from protected file edit |
| 14 | `14_recovery` | Recovery with preserved draft | draft and composer survive failure |
| 15 | `15_restore_focus` | Restore focus mode | queue impact visible before restore |
| 16 | `16_sessions` | Session browser focus mode | worktree safety signals included |
| 17 | `17_search_focus` | Search focus | search results with composer preserved |
| 18 | `18_transcript_review` | Transcript review/search | Alt+O review, Ctrl+O copy latest remains distinct |
| 19 | `19_status` | /status effective config | effective policy is resolved, not vague |
| 20 | `20_settings` | Settings / effective config | precedence and override source shown |
| 21 | `21_large_paste` | Large paste preview | bracketed paste, attach-or-send decision |
| 22 | `22_copy_fallback` | Copy/export fallback | cross-platform clipboard fallback |
| 23 | `23_mcp_read_approval` | MCP read approval | network/read-only tool access with source policy |
| 24 | `24_subagent_trace` | Subagent trace | subagents hidden by default but explainable when used |
| 25 | `25_ascii_fallback` | ASCII / no-glyph fallback | glyph-free equivalent |
| 26 | `26_exact_80x24` | True 80×24 fallback snapshot | 24 rows, 80 columns, fixed composer/footer |
| 27 | `27_command_center` | Command center power mode | explicit opt-in only |

---

## 14. Required implementation tests

```text
1. each app state renders exactly one live composer
2. submitted prompts are not composer nodes
3. composer y-position is stable while output streams
4. drawer max height is enforced
5. queue strip is one line and truncates
6. hotkeys are disabled while composer is focused
7. review hotkeys work only in review/list focus
8. destructive actions require confirmation
9. protected path approval has exact operation identity
10. remote/network action is separate from local protected file edit
11. /status shows effective policy and ignored overrides
12. Ctrl+O copy has visible fallback when clipboard is unavailable
13. large paste preview preserves draft
14. restore preview shows queue impact
15. session browser shows cwd, dirty state, sandbox, checkpoint
16. 80×24 snapshot preserves composer/footer
17. ASCII fallback renders without Unicode glyphs
18. ANSI/CJK/emoji wrapping uses display width
19. crash restore preserves draft, queue, checkpoint, and transcript tail
20. standalone review artifact has no runtime Babel or decompression bootstrap
```

---

## 15. HTML artifact requirements

The corrected HTML artifact is intentionally static:

```text
no React runtime
no Babel-in-browser
no compressed bundle bootstrap
no DecompressionStream requirement
no save controls that pretend to persist in standalone mode
all artboards visible without external assets
query param ?screen=<id> can isolate one screen for capture
```

The real TUI implementation should follow the shell contract rather than copying the static HTML literally.
