# Plan

Last updated: 2026-04-14
Owner: Codex
Purpose: detailed implementation plan for the active post-Phase-8 frontier. `EXECUTION_CHECKLIST.md` is the live status board; this file is the detailed execution map and ordered backlog. For every open checklist item, find the matching section here before implementing.

## How To Use This File

1. Start from `EXECUTION_CHECKLIST.md`.
2. Find the matching numbered section in this file.
3. Use that section’s:
   - goal
   - constraints
   - implementation steps
   - files
   - verification
4. Update both files together when reality changes.

## Ordered Backlog

Follow this order unless the user explicitly redirects:

1. Section 1f: Unified TUI Consolidation (supersedes "Claude Code primary TUI parity")
2. Section 1: Large Codebase Comprehension
3. Section 2: Native External-Harness Orchestration
4. Section 3: Terminal-Bench / Harness Engineering
5. Section 5: Documentation Discipline
6. Section 4: Research Corpus Maintenance
7. Section 0: Harness Architecture Refinement From Proposal v2 as a landed foundation / policy reference

Current practical rule:

- treat Section 0 as landed foundation unless a new gap is discovered
- treat Section 1f (Unified TUI) as the current primary UX workstream
- do not broaden B30 work while the higher-leverage comprehension/adapter items are still moving

---

## 0. Harness Architecture Refinement From Proposal v2

Status:
- landed as foundation
- not the active execution queue
- use this section as a design reference and guardrail source while implementing Sections 1-3

### Goal

Use `harness-improvement-proposal-v2-2026-04-08.md` as a selective improvement source, not as a second parallel architecture.

### Source Inputs

- `harness-improvement-proposal-v2-2026-04-08.md`
- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `docs/research/autocode-internal-first-orchestration.md`
- `docs/research/large-codebase-comprehension-and-external-harness-orchestration.md`

### 0.1 Four-Plane Context Model

#### Goal

Formalize the four context planes in AutoCode-native terms:

- durable instructions
- durable project memory
- live session state
- ephemeral scratch

#### Constraints

- do not introduce a mandatory `.harness/` tree yet
- do not duplicate existing source-of-truth docs
- map the planes onto current modules first

#### Implementation Steps

1. Write a short design doc mapping current modules/files into the four planes.
2. Identify which state is currently mixed across planes.
3. Add a minimal API or model layer that names these planes explicitly.
4. Use that model to guide compaction and handoff behavior.

#### Likely Files

- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `autocode/src/autocode/agent/context.py`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/src/autocode/agent/prompts.py`
- `autocode/src/autocode/agent/orchestrator.py`

#### Verification

- design doc exists and is specific
- no duplicate instruction/memory tree introduced
- compaction/handoff code references the new plane model cleanly

### 0.2 Durable-Memory Write and Preservation Rules

#### Goal

Define what belongs in durable memory, what stays session-local, and what survives compaction by rule.

#### Implementation Steps

1. Create a policy doc for durable-memory writes.
2. Define explicit triggers for durable writes.
3. Define explicit exclusions for transient tool output and dead-end exploration.
4. Update consolidation/memory code to follow those rules.

#### Likely Files

- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/src/autocode/agent/memory.py`
- `autocode/tests/unit/test_carry_forward.py`

#### Verification

- tests prove transient noise is not promoted to durable memory
- tests prove key durable facts survive compaction

### 0.3 Canonical Runtime-State Normalization

#### Goal

Stop spreading runtime state ad hoc across loop, frontend, orchestrator, and session objects.

#### Required State

- session id
- task id / active task
- approval mode
- agent mode
- project root / worktree
- working set
- checkpoint stack
- pending approvals
- subagent registry
- current plan pointer
- last compact summary

#### Implementation Steps

1. Define one canonical runtime-state model.
2. Identify duplicated state across frontends/orchestrator/loop.
3. Move all shared state reads/writes to the canonical model.
4. Keep frontend-local UI state separate from orchestration/runtime state.

#### Likely Files

- `autocode/src/autocode/agent/orchestrator.py`
- `autocode/src/autocode/agent/factory.py`
- `autocode/src/autocode/agent/loop.py`
- `autocode/src/autocode/inline/app.py`
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/tui/app.py`

#### Verification

- runtime state has one clear owner
- frontend recreation does not lose orchestration state unexpectedly
- tests cover state propagation and resume behavior

### 0.4 Tool Metadata Expansion

#### Goal

Give tools enough metadata to support compaction, scheduling, policy, and external-adapter compatibility.

#### Additions

- concurrency safety
- interruptability
- output budget hints
- direct-call eligibility
- orchestrated-call eligibility
- maybe: estimated cost / latency class

#### Likely Files

- `autocode/src/autocode/agent/tools.py`
- `autocode/src/autocode/external/harness_adapter.py`
- `autocode/tests/unit/test_tools.py`

#### Verification

- metadata exists on all core tools
- scheduler/policy code uses metadata instead of name-based special cases

### 0.5 Artifact-First Resumability

#### Goal

Make resumed work depend on durable artifacts, not only raw transcript recovery.

#### Outputs to Strengthen

- handoff packet
- compact summary
- checkpoint manifest
- artifact bundle
- resume packet

#### Likely Files

- `autocode/src/autocode/session/checkpoint_store.py`
- `autocode/src/autocode/agent/artifact_collector.py`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/tests/unit/test_consolidation.py`

#### Verification

- resumed sessions recover from artifacts cleanly
- handoffs preserve objective, blockers, and next steps

---

## 1. Large Codebase Comprehension

### Goal

Make AutoCode effective on genuinely large repos without overloading the hot context.

### 1.1 Large-Repo Validation

#### Goal

Validate the already-landed retrieval/comprehension stack on repos where naive whole-context use fails.

#### Metrics

- turns to first relevant file
- context growth rate
- compaction frequency
- recovery quality after long tasks
- working-set usefulness

#### Implementation Steps

1. Pick at least one genuinely large repo.
2. Run a small fixed task set with current retrieval/comprehension behavior.
3. Record metrics and observed failure modes.
4. Feed findings back into retrieval/compaction policy.

#### Verification

- stored artifact with metrics
- specific findings, not just anecdotes

### 1.2 LanceDB and Dependency Contract

#### Goal

Make the retrieval dependency/runtime contract explicit rather than half-optional.

#### Implementation Steps

1. Decide whether LanceDB is required, optional, or profile-gated.
2. Align `doctor`, setup docs, and runtime behavior with that decision.
3. Add tests around missing/available dependency behavior.

---

## 1f. Unified TUI Consolidation

**Last updated: 2026-04-15**

### Goal

Close the Unified TUI migration truthfully. Go BubbleTea (`autocode-tui`) is already the default interactive frontend, and the focused closeout gates for PTY evidence and the CLI/inline contract are now green. Backend parity for `steer`, `session.fork`, and per-turn `on_cost_update` is landed. Remaining work is commit-scope cleanup plus prioritizing what follows Section 1f. Build the Go TUI to be best-in-class, drawing on every `research-components/` TUI plus web research.

### Architecture Direction

```
BEFORE:                              AFTER:
autocode chat  → Python inline REPL  autocode (interactive) → Go BubbleTea TUI
autocode-tui   → Go BubbleTea TUI   autocode -p "..."      → headless/piped
                → Python backend     autocode serve         → Python backend daemon
```

Live-tree clarification:
- `autocode chat` defaults to the Go TUI today
- `autocode/src/autocode/cli.py` still exposes `--inline`, so the Python inline path is not removed yet
- docs must describe the target state separately from the current state until that cleanup is actually done

**Key rationale:**
- Pi-mono (research reference) is Go+BubbleTea with one TUI
- BubbleTea v2 supports Mode 2026 natively (`tea.EnableMode2026()`)
- Python inline REPL has no feature advantage worth maintaining a parallel frontend for
- Go TUI already has significant investment; fixing its bugs is cheaper than maintaining two codebases
- Inline mode (no alternate screen) is achievable in Go and preserves user scrollback

### Research Basis

| Source | Features extracted |
|--------|-------------------|
| `research-components/pi-mono` | Differential rendering, steering queues, JSONL branching, log/context split, skills as shell scripts |
| `research-components/claude-code` (kuberwastaken spec) | Ink diff-engine, inline mode, status bar, Ctrl+K palette, permission dialogs, memory consolidation |
| `research-components/aider` | Sliding window streaming, token-aware summarization, multiline input, external editor, lazy tokenization |
| `research-components/opencode` | Solid.js reactive TUI, frecency history, timeline fork, background theme detection, leader-key shortcuts |
| `research-components/goose` | Task dashboard emojis, thinking randomization, theme persistence, full output toggle, `/plan` mode |
| `research-components/gastown` | charmbracelet stack, agent-mode awareness, adaptive lipgloss colors, pager support |
| `research-components/claw-code` | Box-drawn tool borders, syntect highlighting, TUI Enhancement Plan |
| `research-components/t3code` | Context-aware keybindings (when-clause), diff worker pool |
| BubbleTea v2 (web) | `tea.EnableMode2026()`, native Mode 2026 support, Elm MVU architecture |

### PTY Bug Report

Historical PTY findings are documented at `autocode/docs/qa/pty-tui-bug-report.md`. That report is useful as debugging context, but the current closeout gate is the newer stored PTY artifact set. Original fix order:
1. C3: Go TUI PTY startup (backend subprocess deadlock)
2. C1: Model picker after every chat (unsolicited `backendModelListMsg`)
3. C2: "(queued N pending)" text leak in stream area
4. M3: Python inline session not self-healing after gateway timeout (fix in backend for headless mode)
5. H4: @file expansion context guard

### Already Landed (do not redo)

- `stagePalette` + Ctrl+K palette with 24 commands
- 187 rotating spinner verbs + `verbTicks` 8-tick rotation
- `❯` prompt, compact branded header, braille thinking spinner
- footer-first status bar, compact tool-row styling
- `/undo`, `/diff`, `/cost`, `/export` commands in `tui/commands.py`
- `todo_write`, `todo_read`, `glob_files`, `grep_content` tools
- palette entries for new commands
- `todo_write`/`todo_read` in `CORE_TOOL_NAMES`
- `load_project_memory_content()` shared RulesLoader in `agent/factory.py`
- **Phase 1 bug fixes (2026-04-13):**
  - C3: `startupTimeoutMsg` type (`messages.go`), 15s timeout constant + cmd (`model.go`), handler in `update.go`, spinner in `view.go` — `stageInit` unblocks after timeout with error shown
  - C2: `_RULES_MAX_CHARS = 3000` cap in `load_project_memory_content()` (`agent/factory.py`) — prevents LLM reproducing status text from large CLAUDE.md injections
  - C1: Regression tests in `model_picker_test.go` — `TestModelPickerDoesNotAppearAfterChatDone`, `TestModelPickerDoesNotAppearAfterStatus`, `TestStartupTimeoutTransitionsToInput`, `TestStartupTimeoutNoopAfterBackendConnects`
- **Phase 2 (wired, 2026-04-13):** `autocode chat` already launches Go TUI via `_find_go_tui_binary()` in `cli.py`; binary at `autocode/build/autocode-tui`

### 1f.1 Phase 1 — Fix Critical Bugs ✅ DONE

(See Already Landed above.)

### 1f.2 Phase 2 — TUI Consolidation: default routing done, contract cleanup pending

What is true now:
- `autocode chat` already prefers the Go TUI through `_find_go_tui_binary()` in `cli.py`
- the Go binary is the default interactive entrypoint on machines where it is present

What is still open:
- ~~`--inline` remains a live Python fallback path in `cli.py`~~ **DECIDED**: `--inline` is kept as an explicit documented fallback. Docs updated.
- ~~docs currently overstate that the Python inline REPL is removed~~ **FIXED**: docs now accurately describe `--inline` as an explicit fallback.
- the binary/install naming contract is still split between `autocode` and `autocode-tui`

### 1f.3 Phase 3 — Mode 2026 + Differential Rendering ✅ GO SIDE DONE

**Implementation completed (2026-04-13):**

1. **BubbleTea v2 migration** — Migrated from v1.3.4 to v2.0.2. All 22+ Go source files and 10 test files updated. Import paths changed to `charm.land/*` vanity domains. `View()` returns `tea.View` struct (not string). Key messages use `tea.KeyPressMsg`. Mode 2026 is enabled by default in BubbleTea v2 — no manual ANSI sequences needed.

2. **Rendering model** — user-space differential-rendering scaffolding was removed after review. View() renders full content each frame and BubbleTea v2 Mode 2026 handles terminal-level diffing. Stable scrollback lines are flushed via `tea.Println` and never redrawn.

3. **Inline mode** — `--inline` flag added to `main.go`. In inline mode, no alternate screen is used, preserving user scrollback.

4. **Sliding window streaming** — `tickMsg` handler flushes completed lines to `stableScrollbackLines` via `tea.Println`. Only the last `maxLiveLines` (default 10) lines remain in the live `streamBuf`. `renderStreamArea` shows a `[N lines above]` indicator for flushed content.

**Files:** `model.go`, `view.go`, `update.go`, `main.go`, `go.mod`, all 22+ source files

**Tests:** 350+ Go tests passing. Sliding window tests (`TestTickFlushesStableLinesToScrollback`, `TestTickNoFlushWhenBelowMaxLiveLines`, `TestViewStreamBufSlidingWindow`).

### 1f.4 Phase 4 — Pi-mono Features ✅ DONE

**Implementation completed (2026-04-13):**

1. **Steering queue** — `Ctrl+C` during `stageStreaming` enters `stageSteer` instead of cancelling. User types steer message, Enter sends `steer` RPC to backend. Esc exits steer mode (continues streaming). Second `Ctrl+C` force-quits. `handleSteerKey` in `update.go`, `steerSendMsg` in `messages.go`, `SteerParams` in `protocol.go`.

2. **Follow-up queue** — `/followup <msg>` slash command queues a message via `followupQueue`. After `backendDoneMsg`, followup queue drains first, then message queue. `followupDrainMsg` processes the next queued message.

3. **JSONL session branching** — `/fork` slash command sends `session.fork` RPC to backend. `ForkSessionParams` and `ForkSessionResult` protocol types defined. `backendForkResultMsg` updates session ID on response.

4. **log.jsonl + context.jsonl split** — still open (Python/session-store change, not Go TUI)

5. **Backend RPC for `steer` and `session.fork`** — landed in `autocode/src/autocode/backend/server.py` with explicit dispatch handling and targeted backend tests covering happy-path and no-active-run / fork-contract cases

**Files:** `update.go`, `model.go`, `view.go`, `messages.go`, `protocol.go`

**Tests:** `TestSteerModeEnterOnCtrlC`, `TestSteerModeEscapeReturnsToStreaming`, `TestSteerModeCtrlCQuitsOnSecondPress`, `TestSteerModeEnterSendsMessage`, `TestFollowupQueueCommand`, `TestCtrlCEntersSteerDuringStreaming`

### 1f.5 Phase 5 — Best-of-All Features ✅ GO SIDE DONE

**Implementation completed (2026-04-13):**

1. **Multiline input** — `Alt+Enter` / `Ctrl+J` inserts newline (already in composer via `textarea.KeyMap`). `Enter` submits. Visual hint in composer footer.

2. **External editor** — `Ctrl+E` keybinding in `handleInputKey` triggers `openEditorCmd()`, which opens `$EDITOR` with current composer content in a temp file. `editorDoneMsg` loads the result back.

3. **Frecency-based prompt history** — `historyEntry` type with `frecencyScore()`, `sortByFrecency()`, `historyAddFrecency()`. `loadFrecencyHistory()` / `saveFrecencyHistory()` for persistence to `~/.autocode/prompt_history`.

4. **Task dashboard** — `renderTaskDashboard()` shows pending/running/done/failed counts from `taskPanelTasks`. Footer shows `⏳ N running` etc. only when tasks exist.

5. **`/plan` mode** — `/plan` slash command toggles `planMode` boolean. `planModeStyle` renders `[PLAN MODE]` indicator in view.

6. **Background theme detection** — `detectThemeCmd()` reads `COLORFGBG` environment variable at startup. `bgColorMsg` sets `themeDetected`="dark"/"light" and `bgColorR`/`bgColorG`/`bgColorB` for adaptive styling.

**Files:** `update.go`, `model.go`, `view.go`, `history.go`, `composer.go`

**Tests:** `TestFrecencyAddNewEntry`, `TestFrecencyAddExistingEntry`, `TestFrecencySortByScore`, `TestCtrlEInInputStage`, `TestThemeDetectionDarkDefault`, `TestPlanModeToggle`

### 1f.6 Phase 6 — Status Bar Enhancements ✅ DONE

**Implementation completed (2026-04-13):**

1. **Live cost display** — `totalCost` field on model, updated by `backendCostMsg`. Displayed in status bar via `statusBar.Cost`.

2. **Live token count** — `totalTokensIn` + `totalTokensOut` accumulated in `handleDone`. Status bar shows "X.Xk tokens" or "N tokens" depending on magnitude.

3. **Provider/model display** — Always visible in status bar via `backendStatusMsg` setting `statusBar.Model` and `statusBar.Provider`.

4. **Session ID display** — `sessionID` field set from `backendStatusMsg`. Shown in status bar via `statusBar.SessionID`.

5. **Background task indicator** — `backgroundTasks` count on model, shown as "⏳ N bg" in status bar via `statusBar.BackgroundTasks`.

6. **Backend `on_cost_update` event** — Go-side notification parsing is wired and the Python backend now emits per-turn `on_cost_update` snapshots with targeted backend-server tests covering payload shape and accumulation

**Files:** `statusbar.go`, `view.go`, `model.go`, `messages.go`

**Tests:** `TestStatusBarSessionID`, `TestStatusBarBackgroundTasks`, `TestStatusBarNoBackgroundTasks`

### 1f.7 Immediate Next Slice — Closeout

#### Goal

Finish the work required to call Section 1f complete without overstating the live tree.

#### Task A — PTY Validation Artifact Refresh ✅ DONE

**Starting point**
- `autocode/tests/pty/pty_smoke_backend_parity.py`
- `autocode/tests/pty/pty_tui_bugfind.py`
- `autocode/build/autocode-tui`

**Implementation instructions**
1. Rebuild `autocode/build/autocode-tui` from the current tree before running PTY checks so the artifact reflects the live code.
2. Run the narrow PTY smoke or an equivalent scripted PTY probe against the real Go TUI entrypoint.
3. Capture startup, Ctrl+K, `/model`, warning classification, and queue-cleanliness behavior.
4. Store the artifact under `autocode/docs/qa/test-results/`.

**Testing strategy**
- Real-terminal or PTY-backed validation only; unit tests are not sufficient for this gate.
- Prefer the focused PTY smoke first, then escalate to the deeper PTY bugfind script if the smoke exposes a regression.
- Keep the command reproducible via `./autocode/scripts/store_test_results.sh <label> -- ...`.

**Verification criteria**
- startup reaches a usable prompt or timeout fallback
- Ctrl+K opens the palette
- `/model` opens only when invoked, not unsolicited
- no queue/debug text leaks into the visible stream
- backend warnings do not render as fatal red error banners
- no panic or traceback appears in the transcript

**Exit gates**
- stored PTY artifact exists under `autocode/docs/qa/test-results/`
- artifact is from the rebuilt current-tree binary, not a stale build
- any failures found by the PTY run are either fixed or explicitly documented as blocking Section 1f closeout

**Completed artifact**
- `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
- companion log: `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.log`

#### Task B — CLI / Inline Contract Cleanup ✅ DONE

**Starting point**
- `autocode/src/autocode/cli.py`
- any user-facing docs that describe the interactive entrypoint

**Implementation instructions**
1. Keep `--inline` only if it remains a deliberate documented fallback.
2. Make sure CLI help text, source-of-truth docs, and tests all describe the same contract.
3. Do not claim the Python inline path is removed while the flag still exists.

**Testing strategy**
- Targeted CLI tests for branch selection and help text.
- One smoke on the chosen interactive path if behavior changes.

**Verification criteria**
- code, tests, and docs all agree on whether `--inline` is supported
- `autocode chat` still launches the Go TUI by default

**Exit gates**
- no stale docs claim the inline fallback is gone if the code still ships it
- focused CLI tests are green

**Completed state**
- `--inline` remains an explicit documented fallback
- source-of-truth docs describe Go TUI as default interactive path and Python inline as fallback, not removed

#### Task C — Commit-Scope Cleanup

**Starting point**
- repo root and worktree status
- docs/comms churn from the Unified TUI push

**Implementation instructions**
1. Keep the commit boundary intentional.
2. Separate ephemeral or reference-only files from the commit scope.
3. Do not delete user materials blindly; prefer exclusion, relocation, or explicit documentation of what is out of scope.

**Testing strategy**
- `git status --short` before and after cleanup
- verify that only intended files remain in the commit-ready slice

**Verification criteria**
- no loose root-level artifacts are accidentally treated as part of the product change
- unrelated churn is either preserved outside scope or clearly called out

**Exit gates**
- the remaining diff is small enough to describe and commit intentionally

### 1f.8 Phase 7 — Feature Completeness Backlog

**Feature audit source**: `research-components/` audit completed 2026-04-13 (see agent output). Covers 69 features across Aider, Claude Code, Codex, Claw Code, Gastown, Goose, OpenAI Codex, OpenCode, Pi, and others.

**Current coverage: 35 DONE (51%), 8 PARTIAL (12%), 26 MISSING (38%)**

Remaining work is ordered by ROI — quick wins first, then medium effort, then larger changes. With 1f.7 Tasks A-E closed, this backlog is now the forward-looking follow-up queue after commit-scope cleanup.

#### Tier 1 — Quick Wins (1-2h each, high visibility)

| # | Feature | Source | What to add |
|---|---------|--------|-------------|
| QW1 | Double-press Ctrl+C quit | Codex | On first Ctrl+C at `stageInput`, show "Press Ctrl+C again to quit" hint in the footer for 3s; only quit on second Ctrl+C within that window. Prevents accidental exits. |
| QW2 | Turn duration timer | Claw Code | Track turn-start time in model, show elapsed ("3.2s") in status bar while streaming; show final duration in `on_done` handler. Add `turnStartTime time.Time` to model, render as `statusBar.Duration`. |
| QW3 | Pager for long output | Claw Code | Commands like `/help`, `/config`, `/memory` that produce static multi-screen text should open a minimal pager (j/k scroll, q/Esc exit) rather than dumping to the stream area. Add `stagePager` and `pagerContent string` to model. |

#### Tier 2 — Medium Effort (half-day each, meaningfully better UX)

| # | Feature | Source | What to add |
|---|---------|--------|-------------|
| ME1 | Collapsible tool output | Claw Code | Tool call rows with output > N lines (e.g. 8) show a `[+N more]` truncation indicator. Tab or Enter on the row expands it. Add `expanded bool` to `toolCallEntry`. |
| ME2 | Tool timeline summary | Claw Code | After `on_done`, emit a single summary line: `bash → ✓ \| read_file → ✓ \| write_file → ✓ (3 tools, 2.1s)`. Render via `tea.Println` so it lands in the scrollback. |
| ME3 | Colored diff display | Claw Code | For tool calls where `Name == "edit_file"` and `Result` contains a unified diff, render `+` lines in green and `-` lines in red/dim. Detect unified diff by `--- a/` prefix in result. |
| ME4 | File path tab completion | Codex, Claw Code | Extend `completion.go` to also complete file paths: after `@` or within `/shell <partial>`, suggest local files via `os.ReadDir`. Requires knowing the `@file` expansion convention. |
| ME5 | Live markdown rendering in stream | Codex, Claw Code | Apply `glamour.Render()` (already a dep via `markdown.go`) to `streamBuf` content at tick time, not just in tool results. Use a line-by-line approach so partial code blocks don't break rendering. |
| ME6 | External editor ($EDITOR) | Codex | `Ctrl+E` at `stageInput` opens `$EDITOR` with current composer content in a temp file; on editor exit, load the content back into the composer. Already architected in Phase 5 (`editorDoneMsg` in `messages.go`) — wire it up if not already wired. |

#### Tier 3 — Larger Changes (multi-session, more design work)

| # | Feature | Source | What to add |
|---|---------|--------|-------------|
| L1 | /export command rendering | Claw Code, Aider | `/export` (already in `commands.go`) should write the current conversation (scrollback + tool calls) to a Markdown file. Path: `~/.autocode/exports/<session_id>-<timestamp>.md`. Show confirmation in status bar. |
| L2 | Session fork/branch UI | Codex, Gastown | `/fork` already emits `session.fork` RPC (Phase 4). Backend support is landed; the remaining UI work is adding a confirmation showing the new session ID and a "you are now in branch `<id>`" status bar indicator. |
| L3 | Help overlay (Ctrl+?) | Claw Code | `?` or `Ctrl+/` at any non-streaming stage shows a scrollable overlay with all keybindings. Add `stageHelp` and `helpContent string` generated from `knownCommands`. Close with Esc/q. |
| L4 | Dark/light theme variants | Claw Code | Use the already-detected `themeDetected` field to switch between two `lipgloss.Style` palettes (dark: current amber, light: muted blue accent). Gate behind a flag or `AUTOCODE_THEME=light` env var for now. |
| L5 | Syntax highlighting (code blocks) | Claw Code, Pi | Wrap `streamBuf` code block extraction (triple-backtick) through `chroma` or `syntect`-equivalent (Go: `alecthomas/chroma`). Render highlighted blocks lazily at tick time. High complexity; add as a `AUTOCODE_SYNTAX=1` opt-in first. |

#### Verification for Phase 7 items

Each Tier 1 and Tier 2 item must:
- have a unit test or PTY regression scenario
- not break the 350+ existing Go tests
- not degrade the Phase 1-6 behaviors confirmed by PTY artifact

Tier 3 items require a design note in a doc comment or a short addendum to this section before implementation begins.

---

## 2. Native External-Harness Orchestration

### Goal

Let AutoCode orchestrate Codex, Claude Code, OpenCode, and Forge while those tools keep using their own native harnesses.

### Principle

AutoCode is the control plane. External harnesses are worker runtimes.

### 2.1 Event Normalization

#### Goal

Normalize all external harnesses into AutoCode’s event model.

#### Event Types To Support

- session started/resumed
- prompt sent
- tool call started/finished
- approval requested/granted/denied
- message emitted
- task completed/failed
- artifact emitted
- interrupt/shutdown

#### Likely Files

- `autocode/src/autocode/external/event_normalizer.py`
- `autocode/src/autocode/external/harness_adapter.py`
- `autocode/src/autocode/agent/events.py`

#### Verification

- all first-wave adapters emit canonical events
- event consumers do not need harness-specific branching for common flows

### 2.2 First Real Adapters

#### Goal

Move from adapter contract + research into real integrations.

#### Order

1. Codex
2. Claude Code
3. OpenCode
4. Forge

#### For Each Adapter

Implement:

- launch
- prompt input
- structured output capture
- resume/continue/fork if supported
- permission/sandbox shaping
- artifact capture
- failure classification

#### Verification

- targeted contract tests
- one real smoke per adapter
- transcript/artifact capture proof

### 2.3 Worktree and Session Isolation

#### Goal

Run external harnesses in isolated worktrees/sessions where appropriate.

#### Verification

- no shared-workspace corruption
- artifacts clearly tied to worktree/session id

---

## 3. Terminal-Bench / Harness Engineering

### Goal

Move B30 beyond baseline Harbor recovery into strategy-quality improvement.

### Calibration Pair

- `break-filter-js-from-html`
- `build-cython-ext`

### 3.1 Strategy Overlays

#### Goal

Teach the Harbor path to behave differently by task family.

#### Families

- HTML/output cleanup
- Python/Cython build tasks

### 3.2 Verifier-Aware Retry Behavior

#### Goal

Require the agent to use failing output/verifier signal before repeating build or rewrite cycles.

### 3.3 Stronger Stagnation Detection

#### Goal

Catch repeated build/install/test cycles with no meaningful progress.

### 3.4 Re-Measure Before Broadening

#### Goal

Improve the 2-task subset before making broader B30 claims.

---

## 4. Research Corpus Maintenance

### Goal

Keep `research-components/` explicit and reproducible.

### Rules

- clone public references only
- update `research-components/MANIFEST.md` when adding repos
- keep them isolated from product/runtime dependencies

### Recent Additions

- `nodepad`

---

## 5. Documentation Discipline

### Goal

Keep the live docs coherent while this frontier evolves.

### Files That Must Stay Synced

- `EXECUTION_CHECKLIST.md`
- `current_directives.md`
- `PLAN.md`
- `docs/session-onramp.md`

### Rule

If implementation or research changes the true next step, update these in the same session.
