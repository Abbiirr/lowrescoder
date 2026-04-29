# AutoCode Next Roadmap — Backend First, Then Minimal Rust TUI

**Scope:** `Abbiirr/lowrescoder` / AutoCode coding-agent harness and TUI rewrite  
**Goal:** finish the backend contracts that the TUI needs, then rebuild the TUI as a minimal, fast, no-jitter terminal interface that feels familiar to Claude Code, Codex CLI, and Pi users while preserving AutoCode’s distinct strengths.

---

## 0. Executive decision

AutoCode should now move into a **two-layer roadmap**:

1. **Backend contract hardening** — finish and verify the event/state/queue/permission/checkpoint/diff/recovery/contracts that the new TUI will render.
2. **TUI rewrite** — rebuild the visible Rust TUI around one minimal shell, no overlays, no permanent side panels, no dashboard default, and no rendering jitter.

The product should not start with a complex command center. It should start with:

```text
HUD
────────────────────────────────────────────────────────────
Transcript
────────────────────────────────────────────────────────────
Optional bounded drawer
Optional one-line queue
Boxed composer
Hint line
```

Everything else is a **focus mode**, **bottom drawer**, **inline panel**, **composer-attached picker**, or **rare decision rail**.

---

## 1. Inputs and source basis

This roadmap consolidates:

- the recent repo/commit findings about backend tranche, Rust TUI migration, HR-5 bindings, structured payloads, and regression gates;
- the uploaded strategic review noting backend strengths and risks;
- the latest TUI mockup critiques;
- the final UI doctrine: **no overlays**, **minimal default shell**, **focus modes instead of modal windows**, **side rail only for decisions**;
- external baseline references from Claude Code, Codex CLI, and Pi.

### External product baselines

Use these as behavioral references:

- **Claude Code fullscreen rendering**: fixed input at the bottom, visible-message rendering, transcript review/search mode, auto-follow, tmux support, less flicker in long sessions.  
  Source: <https://code.claude.com/docs/en/fullscreen>
- **Claude Code commands**: typing `/` shows and filters available commands inside the session.  
  Source: <https://code.claude.com/docs/en/commands>
- **Codex CLI**: lightweight local terminal agent with approval modes: Suggest, Auto Edit, Full Auto.  
  Source: <https://help.openai.com/en/articles/11096431-openai-codex-ci-getting-started>
- **Pi TUI**: differential rendering, CSI 2026 synchronized output, editor components, slash/file autocomplete, bracketed paste, key handling.  
  Source: <https://github.com/badlogic/pi-mono/blob/main/packages/tui/README.md>

### Current internal diagnosis

From the strategic review and repo findings:

- Backend has real substance: post-tool hooks, cost tracking, streaming-aware thinking parser, task lifecycle, episode summarization, structured payloads, and Rust TUI runtime work.
- Rust TUI exists and should be the current target; old Go/BubbleTea artifacts should be treated as historical.
- Several feature surfaces exist, but many were built for parity/binding rather than the final minimal UX.
- The current prototype/spec still has old overlay/modal concepts and demo-state switcher ideas that must not enter product UI.
- The TUI rewrite should start only after the backend contracts and event fixtures are locked.

---

# PART I — BACKEND ROADMAP

## 2. Backend objective

The backend is “TUI-ready” only when it exposes typed, replayable, testable contracts for all state the TUI must render.

The TUI must **not parse human text** to infer state. It should consume structured backend events and reducer snapshots.

The backend roadmap has four jobs:

1. consolidate docs and feature contracts;
2. harden event/state/queue/permission/checkpoint/diff/recovery contracts;
3. fix harness issues that affect correctness and local-model performance;
4. produce deterministic fixtures for the new TUI before implementation.

---

## 3. Backend Phase 0 — Audit and freeze active architecture

### 3.1 Goal

Create a single source of truth for what backend + TUI stack is current.

### 3.2 Tasks

Create:

```text
docs/tui/current-architecture.md
```

Content must state:

```text
Current interactive TUI: Rust.
Backend: Python JSON-RPC backend.
Old Go/BubbleTea TUI: historical migration reference only.
New minimal shell work targets Rust only.
Product TUI must not use centered overlays or demo switchers.
```

Run and record:

```bash
git log --oneline --decorate -n 3
git show --stat --name-status HEAD
git show --stat --name-status HEAD~1
git show --stat --name-status HEAD~2
git diff HEAD~3..HEAD -- docs features docs/features docs/plan autocode/rtui autocode/src/autocode
```

Create audit output:

```text
docs/audits/tui_backend_readiness.md
```

### 3.3 Acceptance criteria

- The last 3 commits are summarized.
- Current TUI stack is explicitly Rust.
- Historical Go/BubbleTea docs are marked historical or archived.
- Backend features are classified as `ready`, `partial`, `missing`, or `blocked`.
- TUI work is not allowed to start from old overlay/modal specs.

---

## 4. Backend Phase 1 — Normalize `docs/features/`

### 4.1 Goal

Turn scattered feature docs into implementation contracts.

The folder should exist and contain:

```text
docs/features/agent-events.md
docs/features/session-lifecycle.md
docs/features/transcript.md
docs/features/composer.md
docs/features/queue.md
docs/features/commands.md
docs/features/permissions.md
docs/features/protected-paths.md
docs/features/diff-review.md
docs/features/checkpoints-restore.md
docs/features/recovery.md
docs/features/validation-output.md
docs/features/subagents-tasks.md
docs/features/search-file-symbol.md
docs/features/tui-rendering.md
docs/features/terminal-compat.md
```

### 4.2 Contract standard

Each feature file must define:

```text
1. Purpose
2. User-visible TUI surfaces
3. Backend types
4. Event types
5. State/reducer behavior
6. Persistence behavior
7. Commands/keybindings
8. Failure/recovery behavior
9. Tests and fixtures
10. Acceptance criteria
```

### 4.3 Acceptance criteria

A feature is not “done” just because it has a command. It is done when:

```text
feature doc exists
backend type exists
event emitted
reducer handles it
state can be replayed
persistence is clear
TUI fixture exists
tests exist
```

---

## 5. Backend Phase 2 — Agent event stream contract

### 5.1 Goal

Everything the TUI renders must be driven by structured events.

### 5.2 Required event model

```ts
type AgentEvent =
  | UserMessageEvent
  | AssistantTextEvent
  | PlanEvent
  | ToolStartEvent
  | ToolResultEvent
  | EditEvent
  | DiffEvent
  | CommandStartEvent
  | CommandOutputEvent
  | CommandEndEvent
  | ValidationEvent
  | QueueEvent
  | ApprovalRequestEvent
  | RecoveryEvent
  | CheckpointEvent
  | SessionStateEvent
  | SubagentEvent;

interface BaseEvent {
  id: string;
  sessionId: string;
  parentId?: string;
  timestamp: string;
  type: string;
  status?: "pending" | "running" | "done" | "failed" | "blocked" | "cancelled";
}
```

### 5.3 Required behavior

- Tool start/result must be pairable by ID.
- stdout/stderr must be tied to command IDs.
- diffs must be structured, not only raw strings.
- approval/recovery/checkpoint events must be replayable.
- transcript review must replay from events, not terminal scrollback.

### 5.4 Backend tasks

- Audit all JSON-RPC notifications.
- Ensure every event has stable IDs.
- Add missing event variants.
- Add schema tests.
- Create JSONL fixtures for all major states.

### 5.5 Acceptance criteria

- TUI can render a full session from a JSONL event log.
- TUI can restore a snapshot from reducer state.
- A test fails if event schema changes without fixture update.

---

## 6. Backend Phase 3 — Central reducer and replayable state

### 6.1 Goal

The TUI should consume one canonical state snapshot.

### 6.2 Required state shape

```ts
interface BackendSessionState {
  session: SessionState;
  transcript: TranscriptState;
  tools: Record<string, ToolCall>;
  commands: Record<string, CommandStream>;
  queue: QueueState;
  approvals: ApprovalState;
  checkpoints: CheckpointState;
  recovery?: RecoveryState;
  subagents: Record<string, SubagentState>;
  validation: ValidationState;
  cost: CostState;
}
```

### 6.3 Tasks

- Add reducer tests for each event type.
- Add replay tests from JSONL fixtures.
- Add snapshot serialization tests.
- Add migration/version field to stored state.

### 6.4 Acceptance criteria

- Same event log always produces same snapshot.
- TUI does not directly parse logs to infer status.
- Session restore can rehydrate snapshot + transcript.

---

## 7. Backend Phase 4 — Queue system as editable drafts

### 7.1 Goal

Queue is a first-class AutoCode differentiator.

Queued messages are **editable drafts until submitted**.

### 7.2 Required model

```ts
type QueueItemState =
  | "draft"
  | "queued"
  | "next"
  | "blocked"
  | "prioritized"
  | "submitted"
  | "cancelled";

interface QueueItem {
  id: string;
  sessionId: string;
  text: string;
  state: QueueItemState;
  blockedReason?: string;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
  editableUntilSubmitted: boolean;
}
```

### 7.3 Required behavior

- `Alt+Enter` adds current composer draft to queue.
- `Alt+Q` opens queue drawer.
- queued item can be edited before submission.
- queued item can be reordered.
- queued item can be removed.
- selected item can be submitted immediately.
- all items can be submitted in order.
- submitted item becomes transcript entry and read-only.

### 7.4 Events

```ts
QueueItemCreated
QueueItemEdited
QueueItemReordered
QueueItemCancelled
QueueItemBlocked
QueueItemUnblocked
QueueItemSubmitted
QueueDrained
```

### 7.5 Backend tasks

- Audit existing follow-up/steering queue.
- Add missing editable draft state.
- Add persistence.
- Add queue lifecycle tests.
- Add TUI fixture: collapsed queue + queue drawer + editing selected item.

### 7.6 Acceptance criteria

- Queue strip can render from state.
- Queue drawer can edit selected item.
- Reloading session preserves queue.
- Submitted items cannot be edited.

---

## 8. Backend Phase 5 — Command registry

### 8.1 Goal

There must be one command registry.

The following must all read from the same registry:

```text
/ slash browser
Ctrl+Shift+P command focus mode
keybindings
custom commands
skills/workflows
```

### 8.2 Required model

```ts
interface CommandDefinition {
  id: string;
  slashName?: string;
  title: string;
  description: string;
  keybinding?: string;
  category:
    | "session"
    | "model"
    | "queue"
    | "diff"
    | "recovery"
    | "settings"
    | "search"
    | "permissions"
    | "tools";
  enabledWhen: string;
  argsSchema?: unknown;
  runMode: "immediate" | "composer_insert" | "focus_mode" | "drawer";
}
```

### 8.3 Required commands

```text
/help
/model
/effort
/mode
/permissions
/plan
/compact
/clear
/new
/resume
/sessions
/restore
/checkpoints
/diff
/review
/grep
/search
/editor
/export
/tasks
/cost
/status
/config
/theme
/interrupt
/command-center
```

### 8.4 Tasks

- Find existing slash parser.
- Find palette/action registry if any.
- Merge into one registry.
- Add enabled/disabled state.
- Add keybinding output.
- Remove Mac-only glyphs like `⌘`.

### 8.5 Acceptance criteria

- `/` and `Ctrl+Shift+P` show the same commands.
- Keybindings invoke registry commands.
- Unknown command shows feedback.
- Disabled command explains why disabled.

---

## 9. Backend Phase 6 — Permissions, approvals, protected paths

### 9.1 Goal

Approval must be evidence-first and mode-aware.

### 9.2 Permission modes

```ts
type PermissionMode =
  | "suggest"
  | "accept-edits"
  | "auto"
  | "full-auto"
  | "review-needed"
  | "halted";
```

### 9.3 Risk facts

```ts
interface RiskFacts {
  writes: "none" | "local-only" | "external";
  network: "off" | "on";
  protectedPathTouched: boolean;
  reversible: boolean;
  filesChanged: number;
  blastRadius: string;
  affectedPaths: string[];
}
```

### 9.4 Approval request

```ts
interface ApprovalRequest {
  id: string;
  sessionId: string;
  reason: string;
  sourceEventId: string;
  risk: RiskFacts;
  choices: ApprovalChoice[];
  defaultChoice?: string;
}
```

### 9.5 Required behavior

- Protected paths always escalate.
- Approval request has structured reason.
- Review shows patch evidence before approval.
- Approve once / session / pattern are distinct choices.
- Reject is explicit.
- Approval events are replayable.

### 9.6 Tasks

- Verify protected path config.
- Verify approval request model.
- Add protected-path escalation fixture.
- Add review approval fixture.
- Add rejection path tests.

### 9.7 Acceptance criteria

- Protected path screen can render without string parsing.
- Review rail can render factual risk values.
- Approval action produces event and resumes execution.

---

## 10. Backend Phase 7 — Structured diff/review model

### 10.1 Goal

Diff focus and review must render structured hunks.

### 10.2 Required model

```ts
interface FileDiff {
  filePath: string;
  oldPath?: string;
  hunks: DiffHunk[];
  added: number;
  removed: number;
  protected?: boolean;
}

interface DiffHunk {
  id: string;
  oldStart: number;
  newStart: number;
  lines: DiffLine[];
  approvalState?: "pending" | "approved" | "rejected";
}

interface DiffLine {
  kind: "context" | "add" | "remove";
  oldLine?: number;
  newLine?: number;
  text: string;
}
```

### 10.3 Required behavior

- Review state renders visible patch.
- Diff focus navigates files and hunks.
- Per-hunk approval possible or explicitly not supported.
- Raw command/source edit can be inspected.
- Test delta can be displayed.

### 10.4 Tasks

- Audit structured diff payloads.
- Add missing file/hunk IDs.
- Add approval scope model.
- Add `diff-focus.jsonl` fixture.
- Add rendering tests with long paths and wide lines.

### 10.5 Acceptance criteria

- Diff focus can render without raw string parsing.
- Each hunk has stable ID.
- Approval actions refer to hunk/file/patch IDs.

---

## 11. Backend Phase 8 — Checkpoint, restore, rewind

### 11.1 Goal

Restore is a focus mode backed by real checkpoints.

### 11.2 Required model

```ts
interface Checkpoint {
  id: string;
  sessionId: string;
  label: string;
  timestamp: string;
  stepId?: string;
  filesChanged: string[];
  testsPassed?: number;
  reversible: boolean;
  messageSnapshotId?: string;
}
```

### 11.3 Restore modes

```text
code only
transcript only
both code + transcript
rewind to step
compare from checkpoint
```

### 11.4 Tasks

- Verify checkpoint message snapshot work.
- Verify restore rehydrates transcript.
- Add diff-from-checkpoint.
- Preserve composer draft during restore focus.
- Add restore fixture.

### 11.5 Acceptance criteria

- Restore focus renders checkpoint list.
- Selection can restore code-only / transcript-only / both.
- Current draft remains available after cancel/restore.

---

## 12. Backend Phase 9 — Recovery state

### 12.1 Goal

Failure should become a safe inline recovery panel.

### 12.2 Required model

```ts
interface RecoveryState {
  failureEventId: string;
  summary: string;
  failedCommand?: string;
  stackOrError?: string;
  lastSafeCheckpointId?: string;
  timeline: RecoveryTimelineItem[];
  options: RecoveryOption[];
  preservedDraft?: string;
}
```

### 12.3 Required options

```text
retry with fix
inspect stderr
restore checkpoint
rewind to step
compact context
return to planning
```

### 12.4 Tasks

- Link failed command to stderr tail.
- Add last-safe checkpoint.
- Add preserved draft.
- Add recovery options.
- Add recovery fixture.

### 12.5 Acceptance criteria

- Failure screen renders from backend state.
- User can choose 1–6 actions.
- Draft is preserved across failure.

---

## 13. Backend Phase 10 — Validation, stdout, stderr streams

### 13.1 Goal

Streaming output must be bounded and drawer-friendly.

### 13.2 Required model

```ts
interface CommandStream {
  commandId: string;
  command: string;
  status: "running" | "passed" | "failed" | "cancelled";
  stdoutTail: string[];
  stderrTail: string[];
  hiddenLines: number;
  startedAt: string;
  endedAt?: string;
}
```

### 13.3 Required behavior

- stdout and stderr separate.
- output tail bounded.
- hidden line counts available.
- drawer height bounded.
- long output does not flood transcript.

### 13.4 Tasks

- Audit command stream events.
- Add hidden-line counts.
- Add drawer fixture.
- Add stderr expand/collapse tests.

### 13.5 Acceptance criteria

- Live drawer can render running command.
- Failed command can open stderr.
- Transcript remains concise.

---

## 14. Backend Phase 11 — Sessions and session tree

### 14.1 Goal

Session browser focus mode should be backed by real session metadata.

### 14.2 Required model

```ts
interface SessionSummary {
  id: string;
  title: string;
  cwd: string;
  branch?: string;
  status: "ready" | "running" | "waiting_input" | "waiting_approval" | "review_needed" | "halted" | "complete";
  lastEventAt: string;
  filesChanged: number;
  queueCount: number;
  checkpointCount: number;
  preview: string;
  parentSessionId?: string;
}
```

### 14.3 Required actions

```text
resume
fork
archive
rename
filter
preview
```

### 14.4 Tasks

- Verify session list/resume/fork backend.
- Add session preview payload.
- Add session browser fixture.
- Add session tree/fork tests.

### 14.5 Acceptance criteria

- TUI can render sessions focus mode from summary list.
- Resume/fork produce correct events.
- Session preview has last tool, branch, status, queue.

---

## 15. Backend Phase 12 — Search, file, symbol attachment

### 15.1 Goal

Search/file/symbol surfaces must be lightweight and keyboard-first.

### 15.2 Models

```ts
interface SearchResult {
  filePath: string;
  line: number;
  text: string;
  ranges: HighlightRange[];
}

interface FileCandidate {
  path: string;
  type: string;
  status?: "modified" | "changed" | "test" | "ignored";
  preview?: string;
}

interface SymbolCandidate {
  name: string;
  kind: "function" | "class" | "type" | "test" | "module";
  filePath: string;
  line: number;
  signature?: string;
}
```

### 15.3 Tasks

- Verify grep/search payloads.
- Add file picker source.
- Add symbol picker source.
- Add attach-to-composer behavior.
- Add fixtures for search/file/symbol.

### 15.4 Acceptance criteria

- Search focus groups hits by file.
- File picker is composer-attached.
- Symbol picker is composer-attached.
- No IDE sidebar required.

---

## 16. Backend Phase 13 — Subagents as context firewalls

### 16.1 Goal

Subagents should not dump noisy transcript into parent context.

### 16.2 Required model

```ts
interface SubagentHandoff {
  id: string;
  subagentId: string;
  scope: string;
  filesInspected: string[];
  filesChanged: string[];
  summary: string;
  findings: string[];
  diffIds?: string[];
  confidence?: "low" | "medium" | "high";
}
```

### 16.3 Tasks

- Verify subagent tools and current return shape.
- Change parent-visible return to structured handoff artifact.
- Keep full subagent transcript available only on demand.
- Add command center subagent fixture.

### 16.4 Acceptance criteria

- Parent transcript gets summary/handoff, not full exploration log.
- Command center can show status and summary.
- Subagent result can be expanded only if requested.

---

## 17. Backend Phase 14 — LLM provider and local-model correctness

### 17.1 Goal

Fix harness weaknesses that block local models and reliable agent behavior.

### 17.2 Provider capability flags

```ts
interface LLMProviderCapabilities {
  supportsNativeToolUse: boolean;
  supportsThinking: boolean;
  supportsPromptCaching: boolean;
  maxContextWindow: number;
  reliableTokenCount: boolean;
  prefersXmlTools: boolean;
  supportsJsonMode?: boolean;
}
```

### 17.3 Tool-call extraction failure

If extraction fails:

```text
1. log warning
2. emit event to transcript/debug log
3. inject corrective system message
4. retry once
5. if retry fails, surface tool-call parsing failure visibly
```

### 17.4 Token counting

Replace `len(text)//4` fallback with provider-aware estimation.

### 17.5 Other harness improvements

- Test Tier 3 FullCompact at 90% context exhaustion.
- Make `todo_write` nudge configurable.
- Reduce spinner verbs to a smaller curated set.
- Make hook exceptions user-visible or warning-level.
- Add per-model presets.

### 17.6 Acceptance criteria

- Qwen/DeepSeek/Devstral-style providers do not silently fall into text-only loops.
- Compaction triggers at predictable thresholds.
- Emergency compaction path has tests.
- Local-model presets are selectable.

---

## 18. Backend Phase 15 — Evaluation and release gates

### 18.1 Goal

Turn “outshine Claude Code” into measurable claims.

### 18.2 Tasks

- Define one benchmark claim in `north-star.md`.
- Run same-model ablation: AutoCode vs Mini-SWE-Agent vs another harness on same model and budget.
- Add resource-constrained eval rig.
- Reframe 8 GB target as deterministic L1/L2 unless using gateway for L4.
- Define release gates for HR/TUI milestones.

### 18.3 Suggested definition

```text
AutoCode targets measurable scaffold advantage under fixed model, fixed budget, fixed local/hybrid constraints. V1 success means it beats simpler harnesses on the same model and proves user-visible advantages: editable queue, restore/recovery, and evidence-first review.
```

---

# PART II — TUI ROADMAP

## 19. TUI objective

The new TUI should feel:

```text
minimal
terminal-native
fast
lightweight
keyboard-first
flicker-free
Claude Code familiar
Codex approval-clear
Pi-rendering disciplined
```

It should not feel:

```text
dashboard-like
IDE-like
modal-heavy
overdesigned
panel-heavy
jittery
state-switcher demo
```

---

## 20. TUI doctrine

### 20.1 Default shell

```text
HUD
rule
transcript
optional drawer
optional one-line queue
composer
hint line
```

### 20.2 No overlays

Forbidden:

```text
centered overlays
dimmed modal backgrounds
floating restore/session/palette cards
modal queue editor
modal command palette
```

Allowed:

```text
focus modes
bottom drawers
inline panels
composer-attached pickers
rare decision rails
```

### 20.3 Side rail policy

Rail allowed only for:

```text
review approval
protected path escalation
command center
```

Rail forbidden by default for:

```text
ready
active
multitasking
queue drawer
file picker
symbol picker
search
plan inline
recovery
restore
sessions
transcript review
```

---

## 21. TUI Phase 0 — Product/demo split

### 21.1 Goal

Separate the real TUI from the mockup/storybook shell.

### 21.2 Tasks

Create or enforce:

```text
packages/tui          # product TUI
packages/tui-demo     # fixtures, screenshots, state switcher
fixtures/tui          # JSONL event fixtures
```

Remove from product build:

```text
brand-mark
state switcher
screen number controls
flow/panels/extra demo groups
overlay-backdrop
overlay-bg
modal classes
```

### 21.3 Acceptance criteria

- Product binary launches directly into terminal shell.
- Demo shell exists only in development/storybook/screenshot build.
- Product build contains no overlay/backdrop implementation.

---

## 22. TUI Phase 1 — Minimal renderer shell

### 22.1 Goal

Implement flicker-free shell before feature UI.

### 22.2 Core components

```text
Hud
Rule
TranscriptOrFocusRegion
Drawer
QueueStrip
Composer
HintLine
TmuxStrip
```

### 22.3 State enums

```rust
enum FocusMode {
    None,
    Diff,
    Restore,
    Sessions,
    CommandPalette,
    Search,
    TranscriptReview,
}

enum DrawerMode {
    None,
    Stdout,
    Stderr,
    Validation,
    Queue,
    Grep,
}

enum RailMode {
    None,
    Review,
    ProtectedPath,
    CommandCenter,
}

enum ComposerPicker {
    None,
    Slash,
    File,
    Symbol,
    Model,
}
```

### 22.4 Rendering requirements

- fixed composer allocation
- bounded drawer allocation
- stable queue strip height
- no full clear per token
- synchronized output
- ANSI-safe wrapping
- terminal width-aware truncation
- resize handling
- fake composer cursor
- real cursor restored on crash

### 22.5 Acceptance criteria

- Streaming output does not move composer.
- No visible flicker on token/tool streams.
- Resize does not corrupt layout.
- 80×24, 120×40, 200×50 snapshots pass.

---

## 23. TUI Phase 2 — Daily-use path

### 23.1 Goal

Build what users see 90% of the time.

### 23.2 Components

1. HUD
2. transcript
3. composer
4. hint line
5. live drawer
6. queue strip

### 23.3 Canonical active screen

```text
sonnet-4.7 · think(med) · ~/dev/compiler-rs · feat/parser-fix* · [accept-edits] · 47.2k/200k · $0.31 · ● working
sandbox:local · Δ2 · tasks:3 · q:0
────────────────────────────────────────────────────────────────────────────

> fix nested import extraction and run targeted parser tests

✻ Planning: inspect parser flow, patch extractImports, run targeted tests.

⏺ Read(src/utils/parser.ts)
⏺ Search("extractImports|ImportNode" src)
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

╭──────────────────────────────────────────────────────────────────────────╮
│ > Type a follow-up instruction...                                        │
╰──────────────────────────────────────────────────────────────────────────╯
Ctrl+Enter send · Alt+Enter queue · Esc interrupt · Ctrl+R history · / @ #
```

### 23.4 Acceptance criteria

- Active state has no rail.
- Queue absent if empty.
- Drawer absent if no stream.
- Composer remains live.

---

## 24. TUI Phase 3 — Composer and pickers

### 24.1 Goal

Make input feel as good as Pi and familiar to Claude Code/Codex users.

### 24.2 Composer features

- multiline input
- soft wrap
- Unicode-safe cursor
- history
- external editor handoff
- bracketed paste support
- `Alt+Enter` queue
- `Ctrl+Enter` send
- `Shift+Enter` newline

### 24.3 Composer-attached pickers

No modals.

#### Slash picker

```text
╭──────────────────────────────────────────────────────────────────────────╮
│ > /com                                                                   │
╰──────────────────────────────────────────────────────────────────────────╯
  /compact       summarize older messages and free context          Ctrl+K
  /compare       compare current patch against checkpoint
  /commit        draft commit message from staged diff
  /config        open settings
  /context       show context usage breakdown

↑↓ move · Enter run · Tab complete · Esc close
```

#### File picker

```text
╭──────────────────────────────────────────────────────────────────────────╮
│ > inspect @parser                                                        │
╰──────────────────────────────────────────────────────────────────────────╯
  @ attach file                                      cwd: ~/dev/compiler-rs
  ● src/utils/parser.ts                      TypeScript · modified · 14.2k
    function extractImports(nodes: ImportNode[] | undefined)
  ○ tests/parser.test.ts                     TypeScript · test · 8.1k
  ○ docs/parser.md                           Markdown · changed · 3.4k
```

#### Symbol picker

```text
╭──────────────────────────────────────────────────────────────────────────╮
│ > explain #extract                                                       │
╰──────────────────────────────────────────────────────────────────────────╯
  # jump to symbol
  FUNCTION
  ● extractImports(node: ImportNode): ResolvedImport[]
    src/utils/parser.ts:38
```

### 24.4 Acceptance criteria

- Pickers stay attached to composer.
- Pickers are 5–8 rows by default.
- No centered popups.
- Tab completion works.

---

## 25. TUI Phase 4 — Queue UX

### 25.1 Goal

Make queue visible but subtle.

### 25.2 Queue strip

```text
≡ queued (2)  [next] clean up null checks · [blocked:tests] run full suite   Alt+Q edit
```

### 25.3 Queue drawer

```text
QUEUE · editable drafts until submitted

1  [next]          clean up redundant null checks after tests pass
2  [blocked:tests] run full matrix suite once watch mode stabilizes
3  [draft]         write a concise PR summary

selected: 1 · queued messages stay editable until submitted

e edit · x remove · r reorder · Enter submit · Ctrl+Enter submit all · Esc collapse
```

### 25.4 Acceptance criteria

- One-line queue by default.
- Queue drawer max 30% height unless expanded explicitly.
- Selected queue draft can be edited.
- Queue persists across session reload.

---

## 26. TUI Phase 5 — Review and diff focus

### 26.1 Goal

Make approval evidence-first.

### 26.2 Review mode

- Main region: visible diff hunk.
- Rare rail: risk facts + approve/reject.
- Composer remains visible.

### 26.3 Diff focus

Focus mode, no overlay.

```text
files changed · 3
● src/utils/resolver.ts                                           +6 -2
○ src/utils/parser.ts                                             +2 -1
○ src/types.ts                                                    +1 -0

── src/utils/resolver.ts  lines 108–128 ───────────────────────── +6 -2
...

approval pattern · this hunk only
risk · parser only · network off · reversible yes · test delta +3 passing
```

### 26.4 Acceptance criteria

- User can approve/reject with keyboard.
- Diff renders from structured hunks.
- No modal approval.
- Risk facts are factual, not vague.

---

## 27. TUI Phase 6 — Recovery and protected path

### 27.1 Recovery inline panel

```text
✗ Run(bun test --matrix) failed — 3 of 72 shards

TypeError: cannot read properties of undefined (reading 'kind') · resolver.ts:118
last edit: src/utils/resolver.ts lines 116–122
agent paused safely before writing changelog

[1] retry with fix · inline null-check        [2] inspect stderr
[3] restore checkpoint · step 3               [4] rewind to step
[5] compact context · 51.8k → 14k             [6] return to planning

no files written since checkpoint · draft preserved below · agent awaiting your decision
```

### 27.2 Protected path escalation

Inline panel + rare rail.

```text
⚑ Permission escalation · protected path touched

Auto-accept was on, but this edit would modify:
.github/workflows/ci.yml

matched rule     .autocode/protect + ".github/**"
blast radius     CI for all branches
reversible       yes · local only until push
```

### 27.3 Acceptance criteria

- Recovery preserves draft.
- Protected path explains why now.
- Approval choices are keyboard-accessible.

---

## 28. TUI Phase 7 — Focus modes

### 28.1 Restore focus mode

```text
restore · 5 checkpoints · feat/parser-fix

TODAY
● step 3 · extractImports guard
  14:08 · 2 files · parser.ts + types.ts · 42 tests passed after

○ step 2 · ImportNode.visited added
  14:05 · 1 file · src/types.ts

selected · step 3 · restoring will keep current draft in composer
safe · local only · reversible
```

### 28.2 Session browser focus mode

```text
sessions · filter: parser                                      12 sessions · 3 projects

COMPILER-RS · FEAT/PARSER-FIX
● parser import patch                         feat/parser-fix* · 19m ago
  42 tests passed · 3 files · awaiting review

preview · parser import patch
last tool · Run(bun test ./tests/parser.test.ts) · 42 passing
queue · [next] inspect docs/parser.md
```

### 28.3 Search/grep focus

```text
⏺ Search("extractImports|ASTNode\\.kind" src) · 14 hits across 5 files

src/utils/parser.ts    4 hits
  12  import { extractImports, ASTNode } from "../types"
  71  const nodes = ast.imports ? extractImports(ast.imports) : []
```

### 28.4 Transcript review

```text
14:08  > fix nested import extraction and run targeted tests
14:08  ✻ Planning: inspect parser flow, patch extractImports, run targeted tests.
14:09  ⏺ Read(src/utils/parser.ts)

/search: resolver
match 2 of 5 · n next · N previous · Esc close search
```

### 28.5 Acceptance criteria

- Focus mode replaces transcript region.
- No floating modal.
- Composer remains visible unless transcript review uses review footer.
- `Esc` returns to previous mode.

---

## 29. TUI Phase 8 — Command center power mode

### 29.1 Goal

Support high-load work without making it default.

### 29.2 Trigger

```text
F8
/command-center
automatic only when multiple long-running concurrent tasks exist
```

### 29.3 Layout

- transcript still dominant
- rail allowed
- drawer allowed
- queue strip allowed
- composer visible

### 29.4 Rail content

```text
PLAN
VALIDATION
SUBAGENTS
RISK
```

### 29.5 Acceptance criteria

- Command center is never default.
- Rail does not overpower transcript.
- Subagents show structured summaries.

---

## 30. TUI Phase 9 — Testing and QA

### 30.1 Fixture tests

Render every fixture:

```text
ready
active
multitasking
queue-drawer
plan-inline
live-drawer
review
diff-focus
protected-path
recovery
restore-focus
session-browser
command-palette
slash-picker
file-picker
symbol-picker
search-focus
transcript-review
command-center
narrow
```

### 30.2 PTY tests

Run at:

```text
80×24
120×40
200×50
```

### 30.3 Terminal compatibility

Test:

```text
Windows Terminal
PowerShell
WSL
GNOME Terminal
Kitty
WezTerm
Ghostty
tmux
VS Code integrated terminal
Cursor integrated terminal
SSH session
```

### 30.4 Acceptance criteria

- No jitter.
- No flicker.
- No scroll jumps.
- Composer fixed.
- Queue one line by default.
- Drawer bounded.
- No overlay/backdrop code in product build.

---

# PART III — ROADMAP ORDER

## 31. Week-by-week execution plan

### Week 0 — Audit and cleanup

Backend:

- audit last 3 commits;
- normalize current architecture doc;
- create `docs/features/` contracts;
- identify old Go/BubbleTea docs to archive;
- audit overlay/modal usage.

TUI:

- split demo from product;
- remove product overlay/backdrop code;
- lock final shell and state enums.

Deliverables:

```text
docs/audits/tui_backend_readiness.md
docs/tui/current-architecture.md
docs/features/tui-rendering.md
```

---

### Week 1 — Backend contracts and fixtures

Backend:

- event stream contract;
- reducer snapshot contract;
- queue lifecycle;
- command registry;
- diff/review model;
- checkpoint/restore model.

TUI:

- JSONL fixtures for core states;
- fixture renderer harness.

Deliverables:

```text
fixtures/tui/*.jsonl
backend schema tests
queue lifecycle tests
```

---

### Week 2 — Renderer and shell

Backend:

- command/output stream payload hardening;
- bounded stdout/stderr tails;
- protected path risk facts.

TUI:

- Rust shell;
- HUD;
- transcript;
- composer;
- hint line;
- resize handling;
- PTY smoke.

Deliverables:

```text
minimal shell running with active fixture
no-jitter render test
80×24 / 120×40 / 200×50 snapshots
```

---

### Week 3 — Daily UX

Backend:

- queue persistence;
- command registry adapter;
- file/symbol candidate sources.

TUI:

- queue strip;
- queue drawer;
- slash picker;
- file picker;
- symbol picker;
- live drawer.

Deliverables:

```text
active + multitasking + queue drawer + picker fixtures pass
keyboard-only flow works
```

---

### Week 4 — Review/recovery

Backend:

- approval request hardening;
- diff hunk IDs;
- recovery state;
- checkpoint restore variants.

TUI:

- review rail;
- diff focus;
- protected path escalation;
- recovery inline panel;
- restore focus.

Deliverables:

```text
review/diff/protected/recovery/restore fixtures pass
approval and reject paths tested
```

---

### Week 5 — Session/search/transcript

Backend:

- session summary list;
- fork/resume/archive actions;
- search result grouping;
- transcript export/open-in-editor.

TUI:

- session browser focus;
- search focus;
- transcript review/search;
- command palette focus.

Deliverables:

```text
session/search/transcript fixtures pass
Ctrl+O transcript mode works
```

---

### Week 6 — Command center and polish

Backend:

- subagent structured handoff;
- task/subagent status cleanup;
- cost/detail integration.

TUI:

- command center power mode;
- narrow mode;
- terminal compatibility pass;
- visual polish pass.

Deliverables:

```text
20-state screenshot set
PTY + visual regression pass
release candidate
```

---

### Week 7+ — Harness improvements

Backend/harness:

- provider capability flags;
- tool-call extraction warn/retry;
- tokenizer accuracy;
- Tier 3 compact test;
- self-critique pre-action;
- lazy MCP loading;
- per-model presets;
- eval rig.

TUI:

- only polish after renderer stability;
- no new complexity until daily shell is excellent.

---

## 32. Release gates

### Backend gate

```text
All P0 feature contracts exist.
All event schemas have tests.
All 20 TUI fixtures can be generated from backend-shaped events.
Queue lifecycle tests pass.
Approval/recovery/checkpoint tests pass.
```

### TUI gate

```text
No overlay/backdrop code in product TUI.
Default active screen has no side rail.
Composer remains fixed during streaming.
Queue collapsed is one line.
Queue editor is a bottom drawer.
Slash/file/symbol pickers attach to composer.
Restore/session/search/transcript are focus modes.
Review is evidence-first.
Recovery preserves draft.
No flicker in PTY smoke.
```

### Release gate

```text
All fixtures render.
All PTY dimensions pass.
Manual test in tmux passes.
Manual test in Windows Terminal passes.
One live backend canary passes.
No placeholder/mockup text remains.
```

---

## 33. Final prioritized task list

### Backend P0

1. Current architecture doc.
2. Feature contracts under `docs/features/`.
3. Event stream schema.
4. Reducer snapshot/replay.
5. Editable queue lifecycle.
6. Shared command registry.
7. Permission/risk/protected-path model.
8. Structured diff/hunks.
9. Checkpoint/restore variants.
10. Recovery state.
11. Bounded stdout/stderr stream model.
12. 20 JSONL fixtures.

### TUI P0

1. Product/demo split.
2. Remove overlays/backdrops.
3. Build one Rust shell.
4. Implement no-flicker renderer.
5. Implement HUD/transcript/composer/hint.
6. Implement queue strip/drawer.
7. Implement slash/file/symbol pickers.
8. Implement live drawer.
9. Implement review/diff/recovery.
10. Implement restore/session/search/transcript focus modes.

### Harness P1

1. Provider capability flags.
2. Tool-call extraction warn/retry.
3. Better token counting.
4. Tier 3 compaction test.
5. Subagent structured handoff.
6. Lazy MCP tool loading.
7. Per-model presets.
8. Same-model benchmark ablations.

---

## 34. Final north-star sentence

AutoCode should become:

```text
A minimal, keyboard-first terminal coding agent harness with a fixed composer, structured transcript, editable queued drafts, safe restore/recovery, evidence-first review, and flicker-free Rust rendering.
```

It should not become:

```text
A dashboard, IDE clone, modal-heavy app, or command-center-first agent UI.
```

The roadmap is backend contracts first, TUI shell second, advanced focus modes third, and harness benchmark improvements after the daily terminal experience is stable.
