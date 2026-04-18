# TUI Style Gap Backlog (Track 3)

> **Purpose.** Track 3 of the three-track TUI Testing Strategy
> (`PLAN.md` §1g). This file is the living, prioritized backlog of
> **soft-style style work** that makes autocode look and feel more
> like Claude Code — informed by Track 2 reference captures and
> Entry 1136's concrete gap list.
>
> **This file is NOT the testing slice's Definition of Done.**
> It's produced BY the testing slice and consumed by later UX
> slices. Closing an item here = implementing a style change in
> autocode and re-running Track 1 + Track 2 to verify the delta.
>
> **Maintenance:** add items as new gaps are observed. Re-prioritize
> when user feedback changes what matters. Never delete items
> without archiving the reason.

**Last updated:** 2026-04-18 (initial populate from Entry 1136 research)
**Owner:** Claude (Coder) — maintains list; user decides priorities
**Source docs:**
- `PLAN.md` §1g (three-track architecture + hard vs soft predicate split)
- `AGENTS_CONVERSATION.MD` Entries 1135, 1136, 1139 (research + design)
- `research-components/claude-code-sourcemap/src/` (Claude Code real source)
- `/tmp/tui-probes/*` (live probe captures from 2026-04-18)

---

## Priority Legend

- **HIGH** — visible in the first 10 seconds of use; user has explicitly
  flagged in comms or direct feedback; or a predicate check fails on
  current autocode
- **MED** — affects UX ergonomics but not first-impression; nice-to-have
  for parity but won't make autocode feel "broken"
- **LOW** — stylistic / aesthetic; can wait indefinitely

Each item lists:
- **What:** the gap in plain language
- **Source:** research citation
- **Target state:** what autocode should look like when fixed
- **Predicate:** the soft-style predicate (if any) that detects this
- **Estimated effort:** S (≤1h) / M (≤4h) / L (≥4h)

---

## HIGH priority

### H1 — Composer has no rounded border
- **What:** autocode's composer is raw `❯ Ask AutoCode…` text with no border box. Claude Code renders the composer inside a rounded `╭──────────────╮` / `╰──────────────╯` frame with a 3-wide left gutter for the `>` prefix.
- **Source:** `claude-code-sourcemap/src/components/PromptInput.tsx:280-303` + `screens/REPL.tsx:550-645`
- **Target state:** rounded Unicode border around the composer area, dim gray border color, bash-mode variant in different color
- **Predicate:** `composer_has_rounded_border(screen)` — composer's top-left corner char in `{╭, ┌, ╒, ╓}`
- **Estimated effort:** M (touches `cmd/autocode-tui/view.go` + `styles.go`; need to build lipgloss border around composer area)

### H2 — Spinner missing "esc to interrupt" affordance
- **What:** autocode spinner renders as `Thinking… (Ns)`; Claude Code renders as `{char} {verb}… ({Ns} · esc to interrupt)`. Forge uses same pattern (`Migrating credentials 00s · Ctrl+C to interrupt`). This is cross-tool convention.
- **Source:** `claude-code-sourcemap/src/components/Spinner.tsx:96-106` + live probe `/tmp/tui-probes/forge.txt`
- **Target state:** autocode spinner line includes `· esc to interrupt` suffix (or `ctrl+c` since that's autocode's interrupt key)
- **Predicate:** `spinner_has_interrupt_hint(screen)` — spinner line contains `interrupt` or `esc`
- **Estimated effort:** S (touches `cmd/autocode-tui/view.go` spinner render path)

### H3 — `◆ AutoCode` orange diamond misplaced
- **What:** the `◆ AutoCode` mode indicator renders BEFORE the spinner during `stageStreaming`, creating a visually noisy "two header" effect (header in view row + orange diamond in render area). Observed in `/tmp/tui-probes/autocode-tui.txt`.
- **Source:** live probe 2026-04-18
- **Target state:** either (a) remove the diamond — it's redundant with the status-bar mode display; (b) relocate to status bar; or (c) only show during specific sub-states
- **Predicate:** none; qualitative call
- **Estimated effort:** S

### H4 — Composer order: status bar is ABOVE composer; Claude target is BELOW
- **What:** current autocode renders status bar above composer and mode-hint above spinner. Claude Code renders composer first, status + mode hint below.
- **Source:** `claude-code-sourcemap/src/screens/REPL.tsx` + live probe comparison
- **Target state:** reorder rows so composer is at bottom-minus-2, status bar at bottom-minus-1, mode hint at last row
- **Predicate:** `status_bar_below_composer(screen)` — status-bar signature row index > composer-signature row index
- **Estimated effort:** M (view.go structural change; may affect PTY phase-1 tests)

---

## MED priority

### M1 — Welcome richness gap
- **What:** autocode shows a 2-line welcome (`AutoCode — Edge-native AI coding assistant\nType a message to start...`). Claude Code shows a 4-6 row rounded dashboard with version, cwd, `/help` hint, optional MCP + override sub-blocks.
- **Source:** `claude-code-sourcemap/src/components/Logo.tsx`
- **Target state:** autocode welcome becomes a rounded box with: sparkle icon + product name + version, padded sub-block with `/help for help` (italic) + `cwd: {path}`. Optional: if LiteLLM gateway reachable, show `model: {alias}` line.
- **Predicate:** `welcome_scoped_to_init(screen, turn_n)` — when `turn_n==0`, welcome box spans ≥3 rows and ≥40 cols
- **Estimated effort:** M (new rendering path for welcome)

### M2 — Hint row content mismatch
- **What:** autocode hint row says `/help for help, /model to switch, Ctrl+D to quit`. Claude Code says `! for bash mode · / for commands · esc to undo` (left) + `shift+⏎ for newline` (right). pi has unified single row: `escape interrupt · ctrl+c/ctrl+d clear/exit · / commands · ! bash · ctrl+o more`.
- **Source:** `claude-code-sourcemap/src/components/PromptInput.tsx:328-365` + live probe `/tmp/tui-probes/pi.txt`
- **Target state:** adopt pi's unified single-row pattern or Claude's split-left-right pattern. Recommendation: pi pattern is cleaner for narrow terminals.
- **Predicate:** none directly; visible diff only
- **Estimated effort:** S

### M3 — Bash mode (`!` prefix) not supported
- **What:** Claude Code supports switching to `!` bash mode where the composer prefix becomes `!` and bash commands execute directly. autocode has no equivalent.
- **Source:** `claude-code-sourcemap/src/components/PromptInput.tsx:297-303`
- **Target state:** autocode accepts `!` as a mode-switch char; composer prefix visually changes; backend routes to shell tool
- **Predicate:** none; feature add
- **Estimated effort:** L (requires backend plumbing)

### M4 — Mode indicator position
- **What:** autocode mode hint is ABOVE composer (`◆ AutoCode` line during streaming). Claude Code pattern doesn't have this at all; mode lives in status bar.
- **Source:** live probe comparison
- **Target state:** remove the floating mode indicator; surface current mode in status bar only
- **Predicate:** overlaps with H3 and M1
- **Estimated effort:** S (partial overlap with H3)

---

## LOW priority

### L1 — Composer prefix character
- **What:** autocode uses `❯`; Claude Code uses `>`. Stylistic.
- **Estimated effort:** S (one char change in view.go)

### L2 — Version inline in top border
- **What:** Claude Code inlines version into the welcome border: `╭───Claude Code v2.1.114───...───╮`. Saves a row.
- **Source:** live probe `/tmp/tui-probes/claude.txt`
- **Estimated effort:** S (visual only; depends on M1)

### L3 — Spinner character set
- **What:** autocode uses Braille dots (`⠙⠹⠸⠼⠴⠦⠧⠇⠏`). Claude Code uses sparkle chars (`·✢✳∗✻✽`). Both are valid; Braille is more universally supported in older terminals.
- **Estimated effort:** S (if we want to match; debatable)

### L4 — Code-block formatting inside responses
- **What:** autocode renders code blocks inline; Claude Code uses `StructuredDiff.tsx` for diffs + `HighlightedCode.tsx` for syntax highlighting.
- **Source:** `claude-code-sourcemap/src/components/{StructuredDiff,HighlightedCode}.tsx`
- **Estimated effort:** L (requires syntax-highlighting library integration)

### L5 — Cost + token warning affordance below composer
- **What:** Claude Code shows `TokenWarning` + `AutoUpdater` widgets right-justified below composer. autocode surfaces cost + tokens only in status bar.
- **Source:** `claude-code-sourcemap/src/components/PromptInput.tsx:352-383`
- **Estimated effort:** M

---

## Items explicitly deferred / not pursued

These were considered but rejected:

- **Dashboard-style "Recent activity" + "What's new" startup (from Claude)** — too opinionated for autocode's local-first edge-native persona. Not worth the complexity.
- **Sentry error boundary patterns (from Claude)** — out of scope; autocode doesn't use Sentry.
- **Auto-updater UI (from Claude + Forge)** — autocode is uv-tool-installed; updates happen via `uv tool upgrade` externally. No in-TUI updater.
- **ASCII art logo (from Forge, OpenCode, Claude)** — autocode's orange `AutoCode` text header is simpler and sufficient; ASCII art is bloat.

---

## Process notes

- **When a HIGH item lands**, re-run Track 1 (`make tui-regression`) and Track 2 (if autocode baseline changed) and confirm the predicate flips from FAIL to PASS in `predicates.json`.
- **When a new gap is observed** during Track 1/2 captures, add it here with Source: live-probe citation + priority guess. User decides final priority.
- **Soft-style predicates** in `autocode/tests/tui-comparison/predicates.py` (once implemented) should mirror this file's predicate names for traceability.
- **This file gets committed** as part of the same Phase 1 patch that introduces the substrate — Codex Entry 1141 Suggested Change #2 requires the file to exist alongside the implementation.

---

## Appendix A — Source-audit quick reference

| Concern | Claude Code source | Line range |
|---|---|---|
| Welcome box | `Logo.tsx` | 1-148 |
| Spinner | `Spinner.tsx` | 73-126 |
| Composer | `PromptInput.tsx` | 280-460 |
| Main scene | `screens/REPL.tsx` | 550-645 |
| Message dispatch | `Message.tsx` | 40-220 |
| Thinking block | `messages/AssistantThinkingMessage.tsx` | — |
| Tool use card | `messages/AssistantToolUseMessage.tsx` | — |

## Appendix B — Cross-tool spinner format convention

From live probes 2026-04-18:

| Tool | Format |
|---|---|
| autocode | `{char} Thinking… ({Ns})` |
| Claude Code | `{char} {verb}… ({Ns} · esc to interrupt)` |
| forge | `{char} {task} {Ns}s · Ctrl+C to interrupt` |
| pi | `{char} {text}…` (no interrupt hint, no elapsed) |
| opencode | N/A (captured at placeholder state) |
| goose | `◒ starting N extensions: {list}` (boot-time) |

**Convention observed across high-quality TUIs:** `{char} {verb-or-task}… ({elapsed} · {interrupt-key} to interrupt)`.
