# AutoCode TUI v6.2 — Minimal Terminal UI Specification

## Purpose of this document

This document defines the final direction for **AutoCode**, a **terminal user interface (TUI)** for an AI coding agent.

AutoCode runs inside a real terminal on **Windows and Linux**. It is not a browser app, not a desktop app, not an IDE sidebar, and not a dashboard. The primary migration targets are engineers who already understand **Claude Code**, **OpenAI Codex CLI**, and lightweight terminal-first coding agents such as **Pi**.

The goal is to make AutoCode feel immediately familiar to those users while improving a few areas:

- editable queued follow-ups while an agent is working
- safer review and approval flows
- clearer recovery and checkpoint/restore behavior
- first-class session resume/fork behavior
- better live-output control without turning the UI into a dashboard
- keyboard-only operation

The most important product sentence is:

> **AutoCode is a minimal, keyboard-first terminal UI for coding agents: transcript-first, fixed composer, subtle queueing, bounded live output, focus modes instead of overlays, and rare side rails only when a decision requires them.**

---

# 1. Current draft verdict

## 1.1 Do you need to change anything?

Yes, but the direction is now correct. The first draft is much closer than the earlier command-center/dashboard attempts. Keep the minimal shell and the no-overlay decision.

The changes needed are mostly **polish and consistency**, not new product direction:

1. **Remove demo/prototype chrome from product mockups.**
   - No state switcher.
   - No external brand badge.
   - No screen-number navigation.
   - No "host:" labels outside the terminal.

2. **Remove all overlay/modal concepts from the product spec and implementation.**
   - No centered overlay.
   - No dimmed background.
   - No floating cards.
   - Use focus modes, bottom drawers, inline panels, and composer-attached pickers.

3. **Standardize HUD grammar.**
   - Use the same order everywhere.
   - Keep only core state on row 1.
   - Use row 2 only for meaningful secondary state.

4. **Standardize tool-call grammar.**
   - Prefer Claude Code-like `⏺ Verb(args)` lines.
   - Do not mix arbitrary dots, bullets, and plain function calls.

5. **Fix plan alignment.**
   - The current plan screen is the weakest because metadata overlaps and feels too table-like.
   - Keep plan inline, but make each plan item readable and stable.

6. **Shrink secondary surfaces.**
   - Queue drawer should max around 30% of terminal height unless explicitly expanded.
   - File/symbol pickers should be 5–8 visible rows.
   - Bottom drawers should be bounded.

7. **Remove placeholder copy from final mockups.**
   - Never show `[transcript remains above]` in product UI.
   - Replace with real dimmed transcript lines.

8. **Keep side rail rare.**
   - Review approval: yes.
   - Protected-path escalation: yes.
   - Command center: yes.
   - Default active, queue, search, file picker, plan: no.

9. **Add missing core states before locking the product.**
   - Recovery/failure safe options.
   - Restore focus mode.
   - Session browser focus mode.
   - Slash command browser attached to composer.
   - Transcript review/search mode.

10. **Do not add more visual complexity.**
    - The product is already feature-complete enough.
    - The next iteration should be about fewer visible surfaces, clearer focus rules, and more consistent keyboard behavior.

## 1.2 What is already correct

Keep these choices:

- compact top HUD
- no default right rail
- no centered overlays
- transcript-first layout
- fixed boxed composer
- one-line queue strip
- queue drawer instead of queue page
- composer-attached file/symbol/command pickers
- diff focus as a full focus mode
- protected-path escalation with factual reason and approval choices
- search/grep as a focus mode
- command center as a deliberate power mode, not default

---

# 2. Product design doctrine

## 2.1 The default UI

The default shell is always:

```text
HUD row 1
HUD row 2 only if needed
────────────────────────────────────────────────────────────
Transcript
────────────────────────────────────────────────────────────
Optional bottom drawer
Optional one-line queue strip
Composer
Hint line
Optional tmux/status strip
```

This is the product. Everything else is conditional.

## 2.2 What AutoCode must feel like

AutoCode should feel:

- terminal-native
- calm
- sparse by default
- readable under long-running work
- keyboard-first
- familiar to Claude Code and Codex users
- distinct through better queueing, restore, review, and recovery

It should not feel:

- like a web dashboard
- like an IDE panel
- like a project-management board
- like a command center by default
- like a mockup gallery
- like a modal-heavy app

## 2.3 The no-overlay rule

The final product uses **no centered overlays**.

Forbidden:

```text
centered overlay
floating modal
modal dim layer
overlay backdrop
hidden underlying TUI
browser-like dialog
```

Allowed:

```text
focus mode
bottom drawer
inline panel
composer-attached picker
rare side rail
```

### Surface mapping

| Feature | Correct surface |
|---|---|
| Normal work | Default shell |
| Running stdout/stderr | Bottom drawer |
| Queue editing | Bottom drawer |
| `/` commands | Composer-attached picker |
| `@file` picker | Composer-attached picker |
| `#symbol` picker | Composer-attached picker |
| Model picker | Composer-attached picker or focus mode |
| Review approval | Diff + rare side rail |
| Protected-path approval | Inline warning + rare side rail |
| Recovery | Inline panel |
| Restore browser | Focus mode |
| Session browser | Focus mode |
| Command palette | Focus mode |
| Diff focus | Focus mode |
| Search/grep | Focus mode |
| Transcript review | Focus mode |
| Command center | Explicit power mode |

---

# 3. Global visual system

## 3.1 Canvas and rendering

| Property | Value |
|---|---|
| Aspect ratio | 16:9 |
| Preferred image size | 2560×1440 |
| Acceptable image size | 1920×1080 |
| Terminal grid target | 160–180 columns × 45–52 rows |
| Font | JetBrains Mono, Cascadia Code, Iosevka, or similar |
| Font size | 14px at 2560×1440, 13px at 1920×1080 |
| Line height | 1.32–1.38 |
| Ligatures | off |
| Rendering | crisp, no glow, no blur |
| Supported platforms | Windows Terminal, Linux terminal, tmux, IDE terminal |
| Unsupported style | macOS-native chrome |

## 3.2 Palette

Use this palette exactly.

| Token | Hex | Usage |
|---|---:|---|
| `bg` | `#0b0f14` | main terminal background |
| `outer_bg` | `#06080b` | outside terminal if visible |
| `surface` | `#11161d` | drawer, queue row, subtle focused strip |
| `surface_2` | `#151c25` | stronger drawer/focus region |
| `surface_3` | `#1a2230` | selected row |
| `rule` | `#1c232e` | separators |
| `rule_strong` | `#2a3442` | composer border, focused border |
| `fg` | `#e6e9ef` | primary text |
| `fg_2` | `#a6b0bf` | secondary text |
| `fg_3` | `#8a94a5` | supporting text |
| `dim` | `#6f7a88` | hints, disabled text, timestamps |
| `blue` | `#7aa2f7` | active, selected, focus |
| `amber` | `#e0af68` | queued, waiting, blocked |
| `green` | `#9ece6a` | success, done, approved |
| `red` | `#f7768e` | error, reject, destructive |
| `violet` | `#bb9af7` | special mode, symbols, reasoning |
| `cyan` | `#7dcfff` | file paths, symbols |
| `diff_add_bg` | `#1b2b1f` | added diff row background |
| `diff_remove_bg` | `#2b1b20` | removed diff row background |
| `diff_add_fg` | `#9ece6a` | added diff text |
| `diff_remove_fg` | `#f7768e` | removed diff text |
| `warning_bg` | `#1c160b` | protected-path warning bg |
| `error_bg` | `#211016` | recovery/failure bg |
| `selection_bg` | `#1c2738` | selected row |
| `selection_border` | `#7aa2f7` | active selection edge |

## 3.3 Symbol vocabulary

| Meaning | Glyph | Color |
|---|---|---|
| User prompt | `>` | prefix `blue`, body `fg` |
| Planning/thinking | `✻` | `amber` or `violet` |
| Tool call | `⏺` | state-colored |
| Success | `✓` or `√` | `green` |
| Running | `●` | `blue` |
| Waiting | `◐` | `amber` |
| Failure | `✗` | `red` |
| Pending | `○` | `dim` |
| Queue | `≡ queued` | `amber` |
| Restore | `↻` | `blue` |
| Warning | `⚑` or `⚠` | `amber` |
| Separator | `·` | `dim` |

## 3.4 Canonical HUD

Use the same order everywhere.

### Row 1

```text
model · effort · cwd · branch · permission · context · cost · state
```

Example:

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k ▌▌▌░░░░░░░ · $0.31 · ● working
```

### Row 2

```text
sandbox · Δ/files · tasks · agents · queue · checkpoint
```

Example:

```text
sandbox:local · Δ3 · tasks:6 · agents:2 · q:2 · checkpoint 14:19
```

### HUD colors

| Segment | Color |
|---|---|
| model | `amber` |
| effort | `blue` |
| cwd | `fg_2` |
| branch | `amber`; dirty `*` is `red` |
| `[default]` | `fg_2` |
| `[accept-edits]` | `green` |
| `[auto]` | `blue` |
| `[plan]` | `green` or `amber` depending state |
| `[review-needed]` | `amber` |
| `[halted]` | `red` |
| context/cost | `fg_3` |
| working | `blue` or `green` |
| waiting | `amber` |
| halted | `red` |

## 3.5 Canonical transcript grammar

Use these exact row types:

```text
> user request
✻ Planning: concise intent
⏺ Read(path)
⏺ Search("pattern" scope)
⏺ Edit(path)
   - removed line
   + added line
⏺ Run(command)
   ✓ result
   ● live status
```

### Tool-state coloring

| Tool state | Prefix |
|---|---|
| completed | `green ⏺` |
| running | `blue ⏺` |
| waiting | `amber ◐` |
| failed | `red ✗` |
| delegated | `violet ⏺` or `cyan ⏺` |

## 3.6 Composer rules

The composer is always a boxed editing surface:

```text
╭──────────────────────────────────────────────────────────────────────────╮
│ > Type a follow-up instruction...                                        │
╰──────────────────────────────────────────────────────────────────────────╯
```

It supports:

- multiline input
- queueing with `Alt+Enter`
- sending with `Ctrl+Enter`
- slash commands
- file picker
- symbol picker
- history
- external editor handoff
- preserved draft across recovery
- continued typing while agent is running

## 3.7 Default key map

| Key | Action |
|---|---|
| `Ctrl+Enter` | Send composer |
| `Alt+Enter` | Add composer text to queue |
| `Shift+Enter` | Newline |
| `Esc` | Close current focus/drawer; otherwise interrupt |
| `/` | Command picker attached to composer |
| `Ctrl+Shift+P` | Command focus mode |
| `Ctrl+R` | History |
| `Ctrl+O` | Transcript review/search |
| `PgUp` / `PgDn` | Scroll transcript |
| `Ctrl+Home` | Top of transcript |
| `Ctrl+End` | Jump live and resume auto-follow |
| `Alt+Q` | Queue drawer |
| `Alt+D` | Toggle bottom drawer |
| `Alt+C` | Restore focus mode |
| `Alt+S` | Session browser focus mode |
| `Alt+F` | Diff focus |
| `Alt+G` | Search/grep focus mode |
| `F8` | Command center power mode |
| `Shift+Tab` | Cycle permission mode when composer focused |

---

# 4. State inventory overview

This spec defines **24 states**:

1. Ready / quiet continuity
2. Normal active session
3. Active minimal / no drawer
4. Multitasking with subtle queue strip
5. Queue editor bottom drawer
6. Plan mode / inline first
7. Live output drawer focus
8. Review / evidence-first approval
9. Diff focus mode
10. Protected path escalation
11. Recovery / failure safe options
12. Restore focus mode
13. Session browser focus mode
14. Command palette focus mode
15. Slash command picker attached to composer
16. File picker attached to composer
17. Symbol picker attached to composer
18. Search / grep investigation focus
19. Transcript review / search mode
20. Subagent coordination minimal
21. Command center power mode
22. Ask-user / decision needed
23. External editor handoff
24. Narrow terminal fallback

The first five define the default visual identity:

- Ready
- Normal active
- Multitasking queue
- Review
- Recovery

Everything else proves product completeness.

---

# 5. State 01 — Ready / quiet continuity

## Purpose

Start or resume work without showing a welcome dashboard. This should be the calmest screen.

## Trigger

- User launches AutoCode in a repo.
- User returns to an idle session.
- No current active task.

## Surface

Default shell only.

No rail. No drawer. No queue strip unless there is a real unsent queue.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · main · [accept-edits] · 12.4k/200k ▌░░░░░░░░░ · $0.04 · • ready
sandbox:local
────────────────────────────────────────────────────────────────────────────

                         Describe a change, ask a question, or paste a stack trace

                         ↻ Restore · feat/parser-fix · 2h ago

                         recent session · parser import patch · 19m ago

last branch activity · src/utils/parser.ts · 3 files touched

╭──────────────────────────────────────────────────────────────────────────╮
│ >                                                                        │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Enter queue · Esc interrupt · Ctrl+R history · / @ #
```

## Behavior

- Composer is focused.
- Typing begins a new instruction.
- `Restore` hint is actionable via `Alt+C` or `/restore`.
- Recent session hint is actionable via `Alt+S` or `/sessions`.
- If no restore point exists, omit restore line entirely.

## Keyboard

| Key | Action |
|---|---|
| `Ctrl+Enter` | Submit instruction |
| `/` | Open command picker attached to composer |
| `Alt+C` | Open restore focus mode |
| `Alt+S` | Open sessions focus mode |
| `Ctrl+R` | History |
| `Shift+Tab` | Cycle permission mode |

## Do not show

- No mascot.
- No recent-activity card.
- No tutorial panel.
- No right rail.
- No dashboard.

---

# 6. State 02 — Normal active session

## Purpose

Default work loop: user asked for code work, agent reads/edits/runs tests, composer stays alive.

## Trigger

- User submits a coding request.
- Agent is actively working.
- A command/test stream is running.

## Surface

Default shell + optional bottom drawer.

No side rail.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k ▌▌▌░░░░░░░ · $0.31 · ● working
sandbox:local · Δ2 · tasks:3 · q:0
────────────────────────────────────────────────────────────────────────────

> fix nested import extraction and run targeted parser tests

✻ Planning: inspect parser flow, patch extractImports, run targeted tests.

⏺ Read(src/utils/parser.ts)
⏺ Search("extractImports|ImportNode" src)
⏺ Read(src/types.ts)
⏺ Edit(src/utils/parser.ts)

   - const nodes = extractImports(ast.imports)
   + const nodes = ast.imports ? extractImports(ast.imports) : []

⏺ Run(bun test ./tests/parser.test.ts)
   ✓ 42 passing
   ● resolving missing imports...

validation · targeted tests running · stderr hidden · +28 lines

────────────────────────────────────────────────────────────────────────────
bun test ./tests/parser.test.ts                                      ● running
[bun] ✓ parses optional import list
[bun] ✓ extracts nested imports
[bun] ● parser smoke path...

draft stays live while validation streams

╭──────────────────────────────────────────────────────────────────────────╮
│ > Type a follow-up instruction...                                        │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Enter queue · Esc interrupt · Ctrl+R history · / @ #
```

## Behavior

- Transcript auto-follows while user has not scrolled away.
- Composer stays focused and editable.
- Drawer appears only because a live command stream exists.
- Tool output collapses automatically after a readable summary.
- User can queue a follow-up while the current run is active.

## Keyboard

| Key | Action |
|---|---|
| `Esc` | Interrupt current run |
| `Alt+D` | Toggle drawer height |
| `Alt+Enter` | Queue composer draft |
| `Ctrl+Enter` | Submit composer immediately if allowed |
| `Ctrl+End` | Jump to latest output |
| `Ctrl+O` | Transcript review mode |
| `/` | Command picker |

## Do not show

- No side rail.
- No full plan panel.
- No risk dashboard.
- No subagent roster.

---

# 7. State 03 — Active minimal / no drawer

## Purpose

Simple active state when the agent is reading/explaining/planning and no stream output is active.

## Trigger

- User asks a question or explanation.
- Agent reads files or searches but no command is streaming.

## Surface

Default shell only.

## Visual content

```text
sonnet-4.7 · think(low) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 19.8k/200k ▌▌░░░░░░░░ · $0.12 · ● working
────────────────────────────────────────────────────────────────────────────

> explain why extractImports misses nested imports

✻ Reading the parser and type definitions before proposing a change.

⏺ Read(src/utils/parser.ts)
⏺ Read(src/types.ts)
⏺ Search("kind === 'import'|extractImports" src)

I found the issue: extractImports only walks the top-level AST import list.
Nested import nodes inside resolver output are skipped when ast.imports is undefined.

Next: I can patch parser.ts to guard missing imports and add a regression test.

╭──────────────────────────────────────────────────────────────────────────╮
│ > patch it and run the targeted parser tests                             │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Enter queue · Esc interrupt · Ctrl+R history · / @ #
```

## Behavior

- No drawer is shown because no stream exists.
- Composer remains the primary action area.
- User can convert explanation into edit request directly.

## Keyboard

Same as normal active session, minus drawer-specific controls unless drawer appears.

---

# 8. State 04 — Multitasking with subtle queue strip

## Purpose

Show that the user has queued follow-ups while current work is still running.

## Trigger

- User presses `Alt+Enter` while work is running.
- User adds follow-up instructions to queue.
- Queue count > 0.

## Surface

Default shell + one-line queue strip.

No rail. No expanded queue unless requested.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k ▌▌▌░░░░░░░ · $0.31 · ● working
sandbox:local · tasks:3 · agents:2 · q:2
────────────────────────────────────────────────────────────────────────────

⏺ Edit(src/utils/parser.ts)
✻ Note: discovered a potential circular import recursion issue. Adding a visited-set guard.
⏺ Edit(src/utils/resolver.ts)
⏺ Run(bun test --watch ./tests/parser.test.ts)
   ✓ 14 passing
   ● resolving deeply nested imports... (5s)

────────────────────────────────────────────────────────────────────────────
≡ queued (2)  [next] clean up redundant null checks · [blocked:tests] run full suite     Alt+Q edit

╭──────────────────────────────────────────────────────────────────────────╮
│ > once tests pass, inline the visited-set helper if only used once█       │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Enter queue · Esc interrupt · Ctrl+R history · / @ #
```

## Behavior

- Queue strip is one row.
- First item is shown; later items summarized.
- Queued drafts remain editable until submitted.
- Submitted queue items become normal transcript entries and are no longer editable.

## Keyboard

| Key | Action |
|---|---|
| `Alt+Q` | Open queue drawer |
| `Alt+Enter` | Add current composer text to queue |
| `Ctrl+Enter` | Submit current composer text |
| `Esc` | Interrupt running task |

## Do not show

- No half-screen queue by default.
- No side rail.
- No separate message list.

---

# 9. State 05 — Queue editor bottom drawer

## Purpose

Let the user view, edit, reorder, submit, or remove queued drafts.

## Trigger

- User presses `Alt+Q`.
- User selects `edit` from queue strip.
- User runs `/queue`.

## Surface

Bottom drawer, max 30% of viewport by default.

## Visual content

```text
HUD
────────────────────────────────────────────────────────────────────────────
⏺ Run(bun test --watch ./tests/parser.test.ts)
   ✓ 14 passing
   ● resolving deeply nested imports... (5s)
────────────────────────────────────────────────────────────────────────────
QUEUE · editable drafts until submitted

1  [next]          clean up redundant null checks after tests pass
2  [blocked:tests] run full matrix suite once watch mode stabilizes
3  [draft]         write a concise PR summary

selected: 1 · queued messages stay editable until submitted

╭─ edit queued draft #1 ──────────────────────────────────────────────────╮
│ once targeted tests pass, clean up redundant null checks in resolver.ts  │
│ and inline the visited-set helper if it is only used once█               │
╰──────────────────────────────────────────────────────────────────────────╯

e edit · x remove · r reorder · Enter submit · Ctrl+Enter submit all · Esc collapse
╭──────────────────────────────────────────────────────────────────────────╮
│ > Type a new instruction...                                              │
╰──────────────────────────────────────────────────────────────────────────╯
```

## Behavior

- Drawer opens above composer.
- Existing transcript remains visible above drawer.
- Editing a queue item uses the same editor engine as composer.
- `Esc` cancels queue item edit first, then collapses drawer.
- Submitted items are removed from queue and appended to transcript.

## Keyboard

| Key | Action |
|---|---|
| `Alt+Q` | Toggle queue drawer |
| `↑/↓` | Select item |
| `e` | Edit selected draft |
| `x` | Remove selected draft |
| `r` | Reorder mode |
| `Shift+↑/↓` | Move selected item |
| `Enter` | Submit selected item now |
| `Ctrl+Enter` | Submit all eligible items |
| `Esc` | Cancel edit or close drawer |

---

# 10. State 06 — Plan mode / inline first

## Purpose

Show planning without turning the UI into a project management dashboard.

## Trigger

- User enters `/plan`.
- Permission mode is `[plan]`.
- Agent decides to plan before editing.

## Surface

Inline plan in transcript.

No rail by default.

## Visual content

```text
sonnet-4.7 · think(high) · ~/dev/compiler-rs · feat/parser-fix* · [plan] · 22.4k/200k ▌▌░░░░░░░░ · $0.16 · ● planning
sandbox:local · tasks:6
────────────────────────────────────────────────────────────────────────────

> stabilize parser + resolver so matrix tests are reliably green

✻ Planning
  Seven steps queued. Step 4 is active; step 5 is blocked on watch-mode shard finishing.

  ✓ Inspect parser flow & call sites
    2 reads · 1 search

  ✓ Extend ASTNode with optional imports
    +1 -1 · src/types.ts

  ✓ Patch extractImports guard
    +2 -1 · src/utils/parser.ts

  ● Run targeted parser tests
    running · 14 passing, 2 left · bun test --watch ./tests/parser.test.ts

  ◐ Run full matrix suite
    blocked · waiting on shard 3

  ○ Update docs/parser.md
    delegated · doc-writer

  ○ Review & approve
    manual

plan persisted · re-opens if you reconnect · checkpoint at step 3

╭──────────────────────────────────────────────────────────────────────────╮
│ > plan stays editable · Tab to open step detail                          │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Esc interrupt · Ctrl+R history · Ctrl+Shift+P palette · / @ #
```

## Behavior

- Plan is a transcript element, not a board.
- Active step is highlighted but not boxed heavily.
- User can edit/append instructions.
- Agent can update step states as work proceeds.

## Keyboard

| Key | Action |
|---|---|
| `Tab` | Focus plan steps |
| `↑/↓` | Move selected step |
| `Enter` | Expand step detail inline |
| `e` | Edit selected step if plan editable |
| `r` | Retry step if failed/blocked |
| `Esc` | Return focus to composer |
| `F8` | Open command center if heavy oversight needed |

## Do not show

- No kanban.
- No permanent plan rail.
- No dashboard grid.

---

# 11. State 07 — Live output drawer focus

## Purpose

Let the user inspect streaming command output without losing transcript or composer.

## Trigger

- Live command/test output exists.
- User presses `Alt+D` or focuses drawer.

## Surface

Expanded bottom drawer, max 35% height.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 48.0k/200k ▌▌▌░░░░░░░ · $0.34 · ● working
sandbox:local · drawer:validation
────────────────────────────────────────────────────────────────────────────

⏺ Run(bun test --watch ./tests/parser.test.ts)
   ✓ 14 passing
   ● resolving deeply nested imports... (6s)

────────────────────────────────────────────────────────────────────────────
VALIDATION DRAWER · bun test --watch ./tests/parser.test.ts          ● live
────────────────────────────────────────────────────────────────────────────
[bun v1.1] ✓ parses optional import list                         12ms
[bun v1.1] ✓ extracts nested imports                              8ms
[bun v1.1] ✓ parser smoke path                                    9ms
[bun v1.1] ● resolving missing imports...
stderr hidden · +28 lines · press e to expand stderr

draft stays live while validation streams

╭──────────────────────────────────────────────────────────────────────────╮
│ >                                                                        │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+D collapse drawer · e stderr · p pause · c clear
```

## Behavior

- Drawer streams output.
- User can pause, tail, expand stderr, or collapse.
- Drawer should never obscure composer.
- Drawer should disappear or collapse when command ends unless pinned.

## Keyboard

| Key | Action |
|---|---|
| `Alt+D` | Toggle drawer |
| `e` | Expand stderr |
| `p` | Pause/resume stream |
| `c` | Clear stream buffer |
| `t` | Toggle tail/follow |
| `Esc` | Collapse drawer |

---

# 12. State 08 — Review / evidence-first approval

## Purpose

Let the user approve a visible patch, not a vague summary.

## Trigger

- Edits are staged/pending approval.
- Permission mode requires review.
- Agent touches change needing approval.

## Surface

Main diff + rare side rail.

Side rail is allowed because user decision is required.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [review-needed] · 47.2k/200k ▌▌▌░░░░░░░ · $0.31 · ◐ waiting
sandbox:local · Δ3 · q:1
────────────────────────────────────────────────────────────────────────────

> patch import extraction and ensure tests pass before review

⏺ Edit(src/types.ts)
⏺ Edit(src/utils/parser.ts)
⏺ Run(bun test ./tests/parser.test.ts) · ✓ 42 passing
✻ All edits staged. Waiting for review.

── src/utils/parser.ts  lines 38–54 ───────────────────────────── +2 -1

38  function extractImports(nodes: ImportNode[] | undefined) {
39    if (!nodes) return []
40    const seen = new Set<string>()
41    const out: ResolvedImport[] = []
42    for (const n of nodes) {
43      if (seen.has(n.name)) continue
44      seen.add(n.name)
45 -    out.push(resolve(n))
45 +    const r = resolve(n)
46 +    if (r) out.push(r)
47    }
48    return out
49  }

tests/parser.test.ts · +4 assertions · details
```

Side rail:

```text
REVIEW
files changed        2
blast radius         parser + tests
network              off
reversible           yes
protected path       no
severity             medium

[a] approve   [r] reject
```

## Behavior

- User can approve or reject from keyboard.
- Diff remains main visual object.
- Rail stays narrow and factual.
- Composer remains visible for annotations or follow-up questions.

## Keyboard

| Key | Action |
|---|---|
| `a` | Approve current patch/hunk |
| `r` | Reject current patch/hunk |
| `d` | Enter diff focus |
| `n/N` | Next/previous hunk |
| `v` | Open patch in editor |
| `Esc` | Return to active transcript |

---

# 13. State 09 — Diff focus mode

## Purpose

Deep patch inspection in a terminal-native focus mode.

## Trigger

- User presses `d` from review.
- User presses `Alt+F`.
- User enters `/diff`.

## Surface

Full focus mode, no overlay.

Optional inline risk facts. No rail unless terminal is wide and approval decision requires it.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [review-needed] · 47.2k/200k · ◐ waiting for approval
sandbox:local · diff-focus
────────────────────────────────────────────────────────────────────────────

files changed · 3
● src/utils/resolver.ts                                           +6 -2
○ src/utils/parser.ts                                             +2 -1
○ src/types.ts                                                    +1 -0

── src/utils/resolver.ts  lines 108–128 ───────────────────────── +6 -2

108  export function resolve(node: ImportNode): ResolvedImport | null {
109    const seen = new WeakSet<ImportNode>()
110    return resolveInner(node, seen)
111  }
112
113  function resolveInner(n: ImportNode, seen: WeakSet<ImportNode>) {
114 -   if (seen.has(n)) return null
115 -   seen.add(n)
114 +   if (!n || seen.has(n)) return null
115 +   seen.add(n)
116 +   const kind = n.kind ?? "module"
117 +   if (kind === "dyn") return null
118 +   const target = lookup(n.name)
119 +   if (!target) return null
120    return { name: n.name, target, children: resolveChildren(n, seen) }
121  }

approval pattern · this hunk only
risk · parser only · network off · reversible yes · test delta +3 passing

≡ queued (2)  [next] run full validation after approval · [draft] write concise PR summary

╭──────────────────────────────────────────────────────────────────────────╮
│ > Reply, annotate this hunk, or request a follow-up check...             │
╰──────────────────────────────────────────────────────────────────────────╯
j/k hunk · n/N file · a approve · r reject · d raw command · Esc back
```

## Behavior

- Main diff scrolls.
- File list stays compact at top.
- Approval facts are inline below diff.
- Queue strip is allowed but remains one row.
- Composer lets user annotate, request test, or ask a follow-up.

## Keyboard

| Key | Action |
|---|---|
| `j/k` | Move hunk |
| `n/N` | Next/previous file |
| `a` | Approve selected hunk |
| `A` | Approve file or patch, depending selection |
| `r` | Reject selected hunk |
| `d` | Show raw command detail |
| `v` | Open in editor |
| `Esc` | Back to review/transcript |

---

# 14. State 10 — Protected path escalation

## Purpose

Pause and explain when a protected path or risk boundary is touched.

## Trigger

- Agent attempts to edit protected path.
- Permission mode would normally allow action but protected rules require approval.

## Surface

Inline warning panel + rare side rail.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [review-needed] · 47.2k/200k · ⚑ escalated
sandbox:local · protected path
────────────────────────────────────────────────────────────────────────────

⚑ Permission escalation · protected path touched

Auto-accept was on, but this edit would modify:
.github/workflows/ci.yml

matched rule     .autocode/protect + ".github/**"
edit origin      auto-planning · propagating bun version bump
blast radius     CI for all branches
reversible       yes · local only until push

> run the full matrix suite on CI with the new bun version

⏺ Read(.github/workflows/ci.yml)
⏺ Edit(.github/workflows/ci.yml) · hold · awaiting approval

── .github/workflows/ci.yml  lines 18–24 ─────────────── protected

18    - uses: oven-sh/setup-bun@v2
19      with:
20 -      bun-version: "1.1.0"
20 +      bun-version: "1.2.3"
21    - run: bun install --frozen-lockfile
22    - run: bun test --matrix

agent held before write · composer is safe · queue paused
```

Side rail:

```text
WHY NOW
[auto] is active, but .github/** is protected.

CHOICES
● approve this edit only
○ approve for this session
○ open diff focus
○ reject · keep CI unchanged

IF APPROVED
writes          1 file
push            manual only
ci impact       all branches
reversible      git revert

[a] approve   [r] reject
```

## Behavior

- Agent pauses before write.
- Composer stays alive.
- Queue is paused until decision.
- Approval is scoped to path/hunk/session depending user choice.

## Keyboard

| Key | Action |
|---|---|
| `a` | Approve once |
| `s` | Approve for session/scope |
| `d` | Diff focus |
| `r` | Reject |
| `Esc` | Stay paused / return focus |

---

# 15. State 11 — Recovery / failure safe options

## Purpose

Show failure, preserve draft, and give safe recovery choices.

## Trigger

- Test/command fails.
- Agent detects loop risk or unsafe continuation.
- Auto-retry threshold is reached.

## Surface

Inline failure panel.

No rail by default.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [halted] · 51.8k/200k ▌▌▌▌░░░░░░ · $0.42 · ● halted
sandbox:local · checkpoint step 3
────────────────────────────────────────────────────────────────────────────

✗ Run(bun test --matrix) failed — 3 of 72 shards

TypeError: cannot read properties of undefined (reading 'kind') · resolver.ts:118
last edit: src/utils/resolver.ts lines 116–122
agent paused safely before writing changelog

> stabilize parser + resolver so the matrix tests are reliably green

14:02  ✓ Edit(src/types.ts) · ImportNode.visited added
14:05  ✓ Edit(src/utils/parser.ts) · extractImports guard
14:08  ✓ Run(bun test ./tests/parser.test.ts) · 42 passing
14:14  ✻ Planning · promote guard into resolver visited-set
14:17  ✓ Edit(src/utils/resolver.ts) · visited-set guard · +6 -2
14:20  ✗ Run(bun test --matrix) · 3/72 shards failed · stderr captured

[1] retry with fix · inline null-check        [2] inspect stderr
[3] restore checkpoint · step 3               [4] rewind to step
[5] compact context · 51.8k → 14k             [6] return to planning

no files written since checkpoint · draft preserved below · agent awaiting your decision

╭──────────────────────────────────────────────────────────────────────────╮
│ > before retry, add a defensive ?.kind at resolver.ts:118 and re-run only │
│   the 3 failed shards█                                                   │
╰──────────────────────────────────────────────────────────────────────────╯
Enter retry · E inspect stderr · R restore · W rewind · C compact · Esc stay halted
```

## Behavior

- Draft is preserved.
- Agent does not continue without decision.
- Recovery options are keyboard-accessible.
- Restore/rewind routes go to focus mode, not overlay.

## Keyboard

| Key | Action |
|---|---|
| `1–6` | Select recovery option |
| `Enter` | Run selected option |
| `E` | Inspect stderr in drawer |
| `R` | Restore focus mode |
| `W` | Rewind to step selector |
| `C` | Compact context |
| `Esc` | Stay halted |

---

# 16. State 12 — Restore focus mode

## Purpose

Browse checkpoints and restore safely without modal UI.

## Trigger

- `Alt+C`
- `/restore`
- recovery option `R`

## Surface

Focus mode replaces transcript region.

Composer remains visible.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix · [accept-edits] · restore
sandbox:local · safe · local · reversible
────────────────────────────────────────────────────────────────────────────

restore · 5 checkpoints · feat/parser-fix

TODAY
● step 3 · extractImports guard
  14:08 · 2 files · parser.ts + types.ts · 42 tests passed after

○ step 2 · ImportNode.visited added
  14:05 · 1 file · src/types.ts

○ step 1 · inspect parser flow
  14:02 · read-only · no writes

EARLIER
○ session start · parser import patch
  yesterday 18:41 · clean working tree

○ manual checkpoint · "before resolver refactor"
  yesterday 17:22 · 3 files staged

selected · step 3 · restoring will keep current draft in composer
safe · local only · reversible

╭──────────────────────────────────────────────────────────────────────────╮
│ >                                                                        │
╰──────────────────────────────────────────────────────────────────────────╯
↑↓ move · Enter restore · D diff from here · C code only · T transcript only · Esc back
```

## Behavior

- Checkpoints list is the main content, not a modal.
- Selected checkpoint previews metadata.
- User can restore code, transcript, or both.
- Draft remains preserved.

## Keyboard

| Key | Action |
|---|---|
| `↑/↓` | Move selection |
| `Enter` | Restore selected checkpoint |
| `D` | Diff from selected checkpoint |
| `C` | Restore code only |
| `T` | Restore transcript only |
| `B` | Restore both |
| `Esc` | Back to previous state |

---

# 17. State 13 — Session browser focus mode

## Purpose

Resume, fork, or archive prior sessions.

## Trigger

- `Alt+S`
- `/sessions`
- `/resume`
- empty launch with no active repo/session

## Surface

Focus mode replaces transcript region.

## Visual content

```text
sonnet-4.7 · think(med) · ~ · [accept-edits] · 0/200k · $0.00 · session browser
sandbox:local · ready
────────────────────────────────────────────────────────────────────────────

sessions · filter: parser                                      12 sessions · 3 projects

COMPILER-RS · FEAT/PARSER-FIX
● parser import patch                         feat/parser-fix* · 19m ago
  42 tests passed · 3 files · awaiting review

○ resolver visited-set refactor               feat/parser-fix · 2h ago
  halted · 3/72 matrix shards failed · checkpoint at step 3

○ typecheck + lint sweep                      main · yesterday
  completed · pushed to origin

ROUTER-RS
○ middleware pipeline refactor                feat/pipeline · 3d ago
  in progress · plan saved · no writes in last session

preview · parser import patch
last tool · Run(bun test ./tests/parser.test.ts) · 42 passing
queue · [next] inspect docs/parser.md

╭──────────────────────────────────────────────────────────────────────────╮
│ > filter sessions...                                                     │
╰──────────────────────────────────────────────────────────────────────────╯
Enter resume · F fork · D diff · X archive · Esc back
```

## Behavior

- Typing filters sessions.
- Preview updates with selection.
- Resume restores transcript and draft state.
- Fork creates a new branch/session continuation.

## Keyboard

| Key | Action |
|---|---|
| type | Filter sessions |
| `↑/↓` | Move selection |
| `Enter` | Resume |
| `F` | Fork |
| `D` | Diff/preview |
| `X` | Archive |
| `Esc` | Back |

---

# 18. State 14 — Command palette focus mode

## Purpose

Keyboard action hub using the same registry as slash commands.

## Trigger

- `Ctrl+Shift+P`
- `/palette`

## Surface

Focus mode, not floating palette.

## Visual content

```text
sonnet-4.7 · command palette · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k
sandbox:local · actions:42
────────────────────────────────────────────────────────────────────────────

Command Center
filter: rev

BEST MATCH
● Open review · inspect diff and approve
  current branch · feat/parser-fix · 2 files staged

ACTIONS
  ↻ Restore checkpoint · feat/parser-fix                    Ctrl+Shift+R
    5 points · most recent: step 3 · 14:08

  ⎘ Resume session · parser import patch                    Ctrl+Shift+O

  ◈ Jump to active subagent · lint-scout                    Ctrl+J

  ⚑ Change permission mode · [auto] / [accept-edits]        Ctrl+M

  ± Focus diff · full-screen review of current patch        Ctrl+D

  ⌕ Search / grep in repo                                  Ctrl+Shift+F

  ◌ Compact context · 47.2k → ~12k                          Ctrl+K

  ✕ Interrupt active run · bun test --matrix                Esc

╭──────────────────────────────────────────────────────────────────────────╮
│ > rev                                                                    │
╰──────────────────────────────────────────────────────────────────────────╯
↑↓ move · Enter run · Tab details · Esc back · same registry as slash commands
```

## Behavior

- Filters actions as user types.
- Same registry as `/` commands.
- Does not hide the TUI behind a modal.

## Keyboard

| Key | Action |
|---|---|
| type | Filter |
| `↑/↓` | Move selection |
| `Enter` | Run action |
| `Tab` | Show details / cycle detail |
| `Esc` | Back |

---

# 19. State 15 — Slash command picker attached to composer

## Purpose

Discover and run slash commands directly from composer.

## Trigger

- User types `/` in empty composer.
- User types `/` after prompt start and picker opens if parser recognizes command position.

## Surface

Composer-attached picker.

## Visual content

```text
⏺ Run(bun test --watch ./tests/parser.test.ts)
   ✓ 14 passing
   ● resolving deeply nested imports...
────────────────────────────────────────────────────────────────────────────
╭──────────────────────────────────────────────────────────────────────────╮
│ > /com                                                                   │
╰──────────────────────────────────────────────────────────────────────────╯
  /compact       summarize older messages and free context          Ctrl+K
  /compare       compare current patch against checkpoint
  /commit        draft commit message from staged diff
  /config        open settings
  /context       show context usage breakdown

  custom commands from .autocode/commands shown below built-ins

↑↓ move · Enter run · Tab complete · Esc close
```

## Behavior

- Picker is attached to composer, not floating.
- List maxes at 8 rows.
- Custom commands appear below built-ins.
- Running a command either executes immediately or inserts command with cursor.

## Keyboard

| Key | Action |
|---|---|
| `/` | Open picker |
| type | Filter |
| `↑/↓` | Move selection |
| `Enter` | Run/insert command |
| `Tab` | Complete command |
| `Esc` | Close picker |

---

# 20. State 16 — File picker attached to composer

## Purpose

Attach files via `@` without an IDE sidebar.

## Trigger

- User types `@` in composer.
- User presses `Tab` after a partial file path.

## Surface

Composer-attached picker, max 8 rows.

## Visual content

```text
⏺ Edit(src/utils/parser.ts)
⏺ Run(bun test --watch ./tests/parser.test.ts)
────────────────────────────────────────────────────────────────────────────
╭──────────────────────────────────────────────────────────────────────────╮
│ > inspect @parser                                                        │
╰──────────────────────────────────────────────────────────────────────────╯
  @ attach file                                      cwd: ~/dev/compiler-rs

  ● src/utils/parser.ts                      TypeScript · modified · 14.2k
    function extractImports(nodes: ImportNode[] | undefined)

  ○ tests/parser.test.ts                     TypeScript · test · 8.1k
    describe("extractImports", () => ...)

  ○ docs/parser.md                           Markdown · changed · 3.4k
    # Parser import behavior

  ○ src/types.ts                             TypeScript · modified · 4.7k
    export interface ImportNode

Enter attach · Space multi-select · Tab complete path · Esc close
```

## Behavior

- Picker opens under composer.
- Typing filters paths.
- `Space` multi-selects.
- Attached file references become visible composer chips/text.

## Keyboard

| Key | Action |
|---|---|
| `@` | Open file picker |
| type | Filter |
| `↑/↓` | Move selection |
| `Space` | Multi-select |
| `Enter` | Attach selected |
| `Tab` | Complete path |
| `Esc` | Close picker |

---

# 21. State 17 — Symbol picker attached to composer

## Purpose

Attach or jump to code symbols via `#`.

## Trigger

- User types `#`.
- User invokes symbol picker from palette.

## Surface

Composer-attached picker.

## Visual content

```text
⏺ Search("extractImports|ImportNode" src)
────────────────────────────────────────────────────────────────────────────
╭──────────────────────────────────────────────────────────────────────────╮
│ > explain #extract                                                       │
╰──────────────────────────────────────────────────────────────────────────╯
  # jump to symbol

  FUNCTION
  ● extractImports(node: ImportNode): ResolvedImport[]
    src/utils/parser.ts:38

  ○ extractNestedImports(ast: ASTNode): ImportNode[]
    src/utils/parser.ts:91

  TYPE
  ○ ExtractImportOptions
    src/types.ts:22

  TEST
  ○ "extracts nested imports"
    tests/parser.test.ts:18

Enter attach symbol · Ctrl+Enter jump · Tab complete · Esc close
```

## Behavior

- Symbol picker filters symbols.
- `Enter` attaches symbol reference.
- `Ctrl+Enter` jumps/opens focused symbol in transcript or editor.

## Keyboard

| Key | Action |
|---|---|
| `#` | Open symbol picker |
| type | Filter |
| `↑/↓` | Move selection |
| `Enter` | Attach symbol |
| `Ctrl+Enter` | Jump/open |
| `Tab` | Complete |
| `Esc` | Close |

---

# 22. State 18 — Search / grep investigation focus

## Purpose

Explore codebase relationships without an IDE file tree.

## Trigger

- User asks a codebase search question.
- User presses `Alt+G`.
- User uses `/grep` or `/search`.

## Surface

Focus mode.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix · [auto] · 22.4k/200k · $0.11 · ● investigating
sandbox:local · search
────────────────────────────────────────────────────────────────────────────

> where is extractImports used and how does it relate to ASTNode.kind?

⏺ Search("extractImports|ASTNode\\.kind" src) · 14 hits across 5 files

src/utils/parser.ts    4 hits
  12  import { extractImports, ASTNode } from "../types"
  71  const nodes = ast.imports ? extractImports(ast.imports) : []
  88  if (node.kind === "import") nodes.push(node)
 132  return extractImports(ast.children)

src/utils/resolver.ts  5 hits
  42  const imports = extractImports(n)
 116  const kind = n.kind ?? "module"
 117  if (kind === "dyn") return null
 148  switch (node.kind) {
 181  return extractImports(node.children)

src/types.ts           3 hits
  14  export type ASTNodeKind = "import" | "export" | "module" | "dyn"
  22  kind: ASTNodeKind
  46  export function extractImports(nodes?: ImportNode[])

@attach src/types.ts · #extractImports · press Tab to pull into composer

╭──────────────────────────────────────────────────────────────────────────╮
│ > propose a guard that narrows n.kind before calling extractImports       │
╰──────────────────────────────────────────────────────────────────────────╯
o open hit · Tab attach · Ctrl+J next file · / refine query · Esc back
```

## Behavior

- Search hits group by file.
- Highlight matched term only.
- `Tab` attaches selected file/symbol to composer.
- `/` refines current search query.

## Keyboard

| Key | Action |
|---|---|
| `Alt+G` | Enter search focus mode |
| `/` | Refine search |
| `↑/↓` | Move through hits |
| `Ctrl+J` | Next file group |
| `Enter` | Open hit |
| `Tab` | Attach hit/file/symbol |
| `Esc` | Back |

---

# 23. State 19 — Transcript review / search mode

## Purpose

Review long session history in-app, search transcript, export to scrollback/editor.

## Trigger

- `Ctrl+O`
- `/transcript`
- `/focus`

## Surface

Transcript focus mode.

Composer becomes a search/footer area rather than normal prompt.

## Visual content

```text
sonnet-4.7 · transcript · ~/dev/compiler-rs · feat/parser-fix* · 47.2k/200k · review mode
────────────────────────────────────────────────────────────────────────────

14:08  > fix nested import extraction and run targeted tests
14:08  ✻ Planning: inspect parser flow, patch extractImports, run targeted tests.
14:09  ⏺ Read(src/utils/parser.ts)
14:09  ⏺ Search("extractImports|ImportNode" src)
14:10  ⏺ Edit(src/utils/parser.ts) · +2 -1
14:11  ⏺ Run(bun test ./tests/parser.test.ts) · 42 passing
14:14  > once tests pass, clean up redundant null checks
14:15  ⏺ Edit(src/utils/resolver.ts) · +6 -2
14:17  ✗ Run(bun test --matrix) · 3/72 shards failed
14:18  ↻ Restore checkpoint · step 3 selected

/search: resolver
match 2 of 5 · n next · N previous · Esc close search
────────────────────────────────────────────────────────────────────────────
Ctrl+O exit · / search · [ write scrollback · v open in $EDITOR · PgUp/PgDn scroll
```

## Behavior

- Normal composer is suspended.
- Search is less-style.
- `[`: write transcript to terminal scrollback.
- `v`: open transcript in `$EDITOR`.
- Exiting restores composer and original scroll position.

## Keyboard

| Key | Action |
|---|---|
| `Ctrl+O` | Toggle transcript mode |
| `/` | Search transcript |
| `n/N` | Next/previous match |
| `j/k` | Scroll one line |
| `Ctrl+U/D` | Half-page scroll |
| `g/G` | Top/bottom |
| `[` | Write to scrollback |
| `v` | Open in editor |
| `Esc/q` | Exit transcript mode |

---

# 24. State 20 — Subagent coordination minimal

## Purpose

Show subagents without a dashboard or permanent roster.

## Trigger

- Agent delegates work to one or more specialist agents.
- Subagent activity is relevant but not enough for command center.

## Surface

Default shell with inline subagent events.

No rail by default.

## Visual content

```text
sonnet-4.7 · think(high) · ~/dev/compiler-rs · feat/parser-fix* · [auto] · 52.1k/200k ▌▌▌▌░░░░░░ · $0.38 · ● active
sandbox:local · tasks:8 · agents:3 · q:1 · checkpoint 14:19
────────────────────────────────────────────────────────────────────────────

> stabilize parser import path, write docs, and prepare review once validation passes

✻ Planning: fix import path + fallback, add docs, validate with targeted tests, then prep review.

⏺ Delegate → parser-scout
   scope: find circular import risk and propose safe path

⏺ Delegate → doc-writer
   scope: document import behavior and fallback guidance

⏺ Delegate → test-runner
   scope: run targeted suite for parser + resolver changes

⏺ parser-scout returned
   result: no cycle when lazy-load is used; recommend utils/parser entrypoint for re-exports.

⏺ test-runner running
   executing 14 tests (parser, resolver, smoke)...

⏺ doc-writer running
   writing docs/parser.md#import-fallback ...

⏺ Edit(src/utils/parser.ts)
   - export { parse, type AstNode } from "../core/parser";
   + export { parse, type AstNode } from "./parser";

validation: targeted parser tests passed (14/14) ✓
● full test suite running...
checkpoint saved · after parser import path update

────────────────────────────────────────────────────────────────────────────
test-runner / targeted suite                                      ● live
[14:25:00] ✓ parser optional imports
[14:25:01] ✓ resolver fallback path
[14:25:01] ● running docs smoke test...

≡ queued (1)  [next] when full suite completes, prepare review summary     Alt+Q edit

╭──────────────────────────────────────────────────────────────────────────╮
│ > if parser-scout confirms safe, have doc-writer summarize fallback       │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Q queue · Alt+D drawer · F8 command center · / @ #
```

## Behavior

- Subagents appear as transcript events.
- Only the active subagent stream may use drawer.
- Full roster is only visible in command center.

## Keyboard

| Key | Action |
|---|---|
| `F8` | Open command center for full roster |
| `Alt+D` | Focus subagent/test drawer |
| `Alt+Q` | Queue editor |
| `Tab` | Focus drawer/composer if drawer open |

---

# 25. State 21 — Command center power mode

## Purpose

High-load oversight mode for multi-agent, multi-task, queued work.

## Trigger

- `F8`
- `/command-center`
- System may suggest it when agents > 1, queue > 1, validation running, and approval pending.

## Surface

Side rail allowed. Drawer allowed. Queue allowed.

This state is not default.

## Visual content

```text
sonnet-4.7 · think(high) · ~/dev/compiler-rs · feat/parser-fix* · [auto] · 52.1k/200k ▌▌▌▌░░░░░░ · $0.38 · ● working
sandbox:local · tasks:12 · agents:3 · q:3
────────────────────────────────────────────────────────────────────────────

> implement standard formatting, doc-lint everything, and fix the import issue across the matrix tests

✻ Main thread handles import extraction · subagents clear lint and docs · waiting on test-runner

⏺ Delegate → doc-writer
   returned: docs/parser.md now explains import fallback

⏺ Delegate → lint-scout
   running: 24 of 38 files · 0 violations

⏺ Delegate → test-runner
   running: matrix tests · shard 2 of 4

⏺ Search("extractImports" src)
⏺ Read(src/utils/parser.ts)
⏺ Edit(src/types.ts)

   - export interface ImportNode { name: string; }
   + export interface ImportNode { name: string; visited?: boolean; }

⏺ Run(bun run typecheck)

checkpoint available · 14:19 · recent session restored after reconnect

────────────────────────────────────────────────────────────────────────────
test-runner / matrix tests                                      ● running
[node v20] ✓ src/utils/parser.test.ts (120ms)
[node v20] ✓ src/types.test.ts (45ms)
[bun v1.1] ✓ src/utils/parser.test.ts (80ms)
[bun v1.1] ● src/types.test.ts...

≡ queued (3)  [next] after validation write PR · [blocked:matrix] triage if fails

╭──────────────────────────────────────────────────────────────────────────╮
│ > if test-runner fails, open a sub-plan before full suite█               │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Esc interrupt · Ctrl+R history · Ctrl+Shift+P palette · Tab focus
```

Side rail:

```text
PLAN
✓ Inspect parser flow
✓ Update AST types
✓ Patch import extraction
● Run matrix tests
○ Write changelog
○ Review & approve

VALIDATION
targeted        passed
matrix          running
lint            delegated

SUBAGENTS
doc-writer      done
returned: docs/parser.md explains fallback

lint-scout      active
scope: resolver/types null checks

test-runner     waiting
waiting on shard 3

RISK
writes          local only
protected path  no
network         off
reversible      yes
files changed   4
severity        medium · parser + docs
```

## Behavior

- Command center shows everything, but only because user requested high-load oversight.
- Transcript remains primary.
- Rail is factual and narrow.
- Drawer is bounded.

## Keyboard

| Key | Action |
|---|---|
| `F8` | Exit command center |
| `Alt+R` | Focus rail |
| `Alt+D` | Focus drawer |
| `Alt+Q` | Queue drawer |
| `Tab` | Cycle mounted regions |
| `Shift+Tab` | Reverse focus cycle |
| `Esc` | Return to active shell |

---

# 26. State 22 — Ask-user / decision needed

## Purpose

Handle human decisions that are not approval prompts.

Examples:

- Which branch should I target?
- Choose a migration strategy.
- Pick one of several conflicting conventions.
- Provide missing credential/environment variable.
- Decide whether to preserve or rewrite public API.

## Trigger

- Agent cannot proceed without human product/technical judgment.
- The needed input is not a file edit approval.

## Surface

Inline decision panel.

No overlay.

## Visual content

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 31.4k/200k · ◐ waiting for input
sandbox:local · q:1
────────────────────────────────────────────────────────────────────────────

⏺ Search("ImportNode" src)
⏺ Read(src/types.ts)
⏺ Read(docs/parser.md)

◐ Decision needed · conflicting conventions found

I found two conventions for missing imports:

[1] Treat missing imports as empty list
    used in src/utils/parser.ts and tests/parser.test.ts

[2] Treat missing imports as parse error
    described in docs/parser.md older migration notes

Recommended: choose [1], then update docs/parser.md to match current behavior.

[1] use empty list behavior
[2] preserve parse error behavior
[3] inspect both call sites
[4] ask me to propose a migration note

╭──────────────────────────────────────────────────────────────────────────╮
│ > choose 1 and update docs to match current behavior█                    │
╰──────────────────────────────────────────────────────────────────────────╯
1-4 choose · Ctrl+Enter send · Esc pause · Alt+Q queue
```

## Behavior

- Agent pauses until user answers.
- Composer stays active.
- User can type a freeform answer or press numeric choice.
- Queued messages are held until decision resolves.

## Keyboard

| Key | Action |
|---|---|
| `1–9` | Select option |
| `Ctrl+Enter` | Submit typed response |
| `Alt+Enter` | Queue typed response |
| `Esc` | Pause/stay waiting |
| `Alt+Q` | Edit queue |

---

# 27. State 23 — External editor handoff

## Purpose

Allow large prompts, queue edits, patch notes, or transcript review in `$EDITOR`.

## Trigger

- `Ctrl+X Ctrl+E`
- `/editor`
- `v` in diff/transcript/review modes

## Surface

Inline handoff notice or focus mode message. No overlay.

## Visual content

```text
sonnet-4.7 · editor handoff · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k
sandbox:local
────────────────────────────────────────────────────────────────────────────

↗ Opened draft in $EDITOR

file        /tmp/autocode-draft-28491.md
mode        composer draft
status      waiting for editor to close

When the editor exits, AutoCode will reload the draft into the composer.
No agent action will run until you confirm.

current draft preview:

  once tests pass, clean up redundant null checks in resolver.ts
  and inline the visited-set helper if it is only used once

╭──────────────────────────────────────────────────────────────────────────╮
│ > editor open · waiting...                                               │
╰──────────────────────────────────────────────────────────────────────────╯
Esc cancel handoff · Ctrl+C force cancel
```

## Behavior

- TUI waits for editor process.
- On editor close, content returns to composer.
- User still confirms with `Ctrl+Enter`.
- If editor fails, show inline error and restore previous draft.

## Keyboard

| Key | Action |
|---|---|
| `Esc` | Cancel editor handoff if possible |
| `Ctrl+C` | Force cancel |
| after editor closes | Composer receives edited text |
| `Ctrl+Enter` | Submit returned draft |

---

# 28. State 24 — Narrow terminal fallback

## Purpose

Show how the TUI behaves inside narrow terminal panes, IDE terminals, or tmux splits.

## Trigger

- Terminal width below ~100 columns.
- Height below recommended rows.

## Surface

Default shell with collapsed secondary surfaces.

## Visual content

```text
sonnet-4.7 · think(med) · feat/parser-fix* · [accept-edits]
47.2k/200k · $0.31 · q:2 · ● working
────────────────────────────────────
tabs: transcript  plan(6)  risk  drawer

> refactor parser.ts safely

✻ Planning
  inspect flow · extend types · patch extractImports · run tests.

⏺ Read(src/utils/parser.ts)
⏺ Edit(src/types.ts)

   - imports: ImportNode[]
   + imports?: ImportNode[]

⏺ Run(bun test ./tests/parser.test.ts)
   ✓ 14 passing · ● resolving...

≡ queued (2) [next] inspect docs/parser.md

╭──────────────────────────────────╮
│ > once green, write PR summary█  │
╰──────────────────────────────────╯
Ctrl+Enter send · Tab tabs · Esc interrupt · / @ #
```

## Behavior

- No side rail.
- Rail content becomes tabs or focus modes.
- Drawer maxes at 3–4 rows.
- Queue strip truncates after first item.
- Composer always remains visible.
- Transcript remains main scroll root.

## Keyboard

| Key | Action |
|---|---|
| `Tab` | Cycle tabs if tab row is visible |
| `Alt+D` | Open/collapse drawer |
| `Alt+R` | Open rail content as focus/tab, not side rail |
| `Ctrl+End` | Jump live |
| `Esc` | Return to transcript/composer |

---

# 29. State transition rules

## 29.1 Default transitions

| From | Event | To |
|---|---|---|
| Ready | user sends prompt | Active |
| Active | command starts streaming | Active + Drawer |
| Active | user queues draft | Multitasking |
| Active | approval required | Review |
| Active | protected path touched | Protected path escalation |
| Active | command fails and agent pauses | Recovery |
| Review | `d` | Diff focus |
| Recovery | `R` | Restore focus |
| Any | `Ctrl+Shift+P` | Command palette focus |
| Any | `Alt+S` | Session browser focus |
| Any | `Alt+C` | Restore focus |
| Any | `Ctrl+O` | Transcript review |
| Any | terminal too narrow | Narrow fallback layout |

## 29.2 Side rail policy

Side rail is allowed only in:

```text
review approval
protected path escalation
command center
```

Never show side rail in:

```text
ready
normal active
multitasking
queue drawer
plan by default
search/grep
file picker
symbol picker
transcript review
restore/session focus modes
```

## 29.3 Drawer policy

Bottom drawer is allowed only for:

```text
stdout
stderr
validation stream
test watch
grep detail
queue editor
subagent stream
```

Drawer defaults:

- collapsed: 4–6 rows
- focused: max 30–35% height
- narrow terminal: max 3–4 rows

## 29.4 Queue policy

Queue states:

| State | Meaning |
|---|---|
| draft | editable, not submitted |
| next | first eligible queued item |
| blocked | waits on condition |
| prioritized | promoted by user |
| submitted | handed to agent; no longer editable |
| cancelled | removed |

Rules:

- Queue strip appears only if queue is non-empty.
- Queue strip is one row by default.
- Queue editor is a bottom drawer.
- Drafts editable until submitted.
- Submitted items become immutable transcript entries.

---

# 30. Implementation model

## 30.1 Core UI state types

```ts
type UiMode =
  | "ready"
  | "active"
  | "plan"
  | "review"
  | "diff_focus"
  | "protected_path"
  | "recovery"
  | "restore_focus"
  | "session_focus"
  | "command_palette_focus"
  | "search_focus"
  | "transcript_review"
  | "command_center"
  | "narrow";

type DrawerMode =
  | "none"
  | "stdout"
  | "stderr"
  | "validation"
  | "watch"
  | "grep"
  | "queue"
  | "subagent";

type RailMode =
  | "none"
  | "review"
  | "protected_path"
  | "command_center";

type ComposerPicker =
  | "none"
  | "slash"
  | "file"
  | "symbol"
  | "model"
  | "history";
```

## 30.2 Render priority

```text
HUD
focus content or transcript
drawer if mounted
queue strip if queue exists and queue drawer not mounted
composer
picker attached to composer if active
hint line
```

## 30.3 No-overlay enforcement

Do not use classes or render paths that imply:

```css
.overlay {}
.overlay-bg {}
.overlay-backdrop {}
.has-overlay > * { display: none; }
```

If there is existing prototype code with these concepts, keep it only for internal demo harnesses, not product UI.

---

# 31. Acceptance checklist

Use this as the ship gate.

## Shell

- [ ] HUD always visible.
- [ ] Default active state has no side rail.
- [ ] Composer is boxed and fixed.
- [ ] Hint line is one line and quiet.
- [ ] Transcript is the dominant scroll root.
- [ ] Drawer appears only with live/transient output.
- [ ] Queue strip appears only when queue exists.
- [ ] No centered overlays.
- [ ] No dimmed modal layers.

## Keyboard

- [ ] Every action works without a mouse.
- [ ] `/` opens command picker attached to composer.
- [ ] `@` opens file picker attached to composer.
- [ ] `#` opens symbol picker attached to composer.
- [ ] `Alt+Q` opens queue drawer.
- [ ] `Ctrl+O` opens transcript review/search.
- [ ] `Ctrl+End` returns to live output.
- [ ] `Shift+Tab` cycles permission mode when composer focused.
- [ ] Review can be approved/rejected by keyboard.
- [ ] Recovery actions are keyboard-selectable.

## Behavior

- [ ] Composer remains live while work streams.
- [ ] Queued drafts remain editable until submitted.
- [ ] Submitted queue items are immutable transcript entries.
- [ ] Recovery preserves unsent draft.
- [ ] Restore/session browsers are focus modes, not overlays.
- [ ] Protected path escalation explains why action paused.
- [ ] Side rail appears only for review, protected path, command center.
- [ ] Narrow mode keeps composer and transcript visible.

## Visual polish

- [ ] No placeholder text like `[transcript remains above]`.
- [ ] Plan metadata does not overlap.
- [ ] Search highlights are stable and precise.
- [ ] Picker height is capped.
- [ ] Queue drawer height is capped.
- [ ] Command center does not define the product identity.

---

# 32. Final recommendation

The current design direction is correct.

Do not add more UI concepts. Do not add more panels. Do not bring overlays back.

The next pass should do exactly this:

1. Standardize HUD order and coloring.
2. Standardize transcript tool grammar.
3. Shrink queue drawer and composer-attached pickers.
4. Fix plan alignment.
5. Remove placeholder copy.
6. Add recovery, restore focus, session focus, slash picker, transcript review.
7. Keep command center as an explicit advanced mode.

The target should feel like:

```text
Claude Code familiarity
+ Codex approval clarity
+ Pi-style terminal/editor primitives
+ AutoCode queue/recovery/session power
```

The product is minimal by default and powerful by command.

---

# 33. External references

- Claude Code fullscreen rendering: https://code.claude.com/docs/en/fullscreen
- Claude Code commands: https://code.claude.com/docs/en/commands
- Claude Code permission modes: https://code.claude.com/docs/en/permission-modes
- Claude Code checkpointing: https://code.claude.com/docs/en/checkpointing
- OpenAI Codex CLI getting started: https://help.openai.com/en/articles/11096431-openai-codex-ci-getting-started
- Pi TUI README: https://github.com/badlogic/pi-mono/blob/main/packages/tui/README.md
- OpenCode TUI docs: https://opencode.ai/docs/tui/
