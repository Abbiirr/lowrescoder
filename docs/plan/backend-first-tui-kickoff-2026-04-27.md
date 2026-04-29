# AutoCode Backend-First + Minimal Rust TUI Kickoff — Program Brief

> **Status:** PROGRAM BRIEF — Packet 3 only is ACTIVE PREP SLICE under Backend Robustness Tranche 4 (kickoff AUTHORIZED 2026-04-27 late). Packets 1, 2, 4, 5 are PARKED for after Tranche 4 closes.
> **Source:** user-supplied "first implementation prompt" (2026-04-27).
> **Active Builder direction:** `AGENTS_CONVERSATION.MD` Entry 1604 (with Codex 1602 + Claude 1603 supporting).
> **Builder routing:** OpenCode primary; Codex fallback when OpenCode is unavailable.
> **Reviewer / Architect:** Claude default. Codex co-review available if user redirects.
> **Predecessor:** Stabilize-and-Release Tranche 3 closed via `990a52c` + `1700d66` (2026-04-26 / 2026-04-27).
> **Sibling active program:** Backend Robustness Tranche 4 (`docs/plan/backend-robustness-tranche-4-plan.md`) — kickoff AUTHORIZED. Packet 3 prep slice (this brief, Work packet 3 below) runs as G0 prep before C4.G1.

This document captures the user's verbatim kickoff prompt as the program-brief source-of-truth. Comms task-handoff entries reference this file rather than inline the full text.

---

## Operating principles (program-level)

- **No implementation kicks off until user authorizes Packet 1.** Audit first.
- **Per-packet exit gate (inherited from Tranche 4 Constraint #8):** every packet must update an inventory doc AND store a verification artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<packet-id>-<short-description>.md` BEFORE the Builder posts a Review Request.
- **Git policy (strict per `AGENTS.md`):** no tree-mutating ops. Permitted: `git status`, `git diff`, `git log`, `git show`, `git fetch`, `git stash list/show` (read-only), `git worktree add/list/remove`, `git config` (read-only), `git add`. Forbidden: `commit`, `push`, `tag`, `reset`, `rebase`, `merge`, `pull`, `checkout` (any), `restore`, `stash push|pop|apply`, `apply`, `clean`. User commits.
- **Hard constraints from product doctrine** (from prompt, do NOT violate):
  - Forbidden in product TUI: centered overlays, dimmed modal backdrops, floating modal windows, permanent sidebars, default-state right rail, state switcher in product, demo screen-number controls, Mac-specific Cmd/Option glyphs, dashboard/card-heavy UI, command center as default UI.
  - Side rail is allowed only for: review approval, protected-path escalation, explicit command-center power mode.
  - Old Go/BubbleTea TUI is historical migration reference only — never the target architecture for new work.

## External behavior baselines (conceptual, not branding)

- Claude Code fullscreen: fixed bottom input, transcript review/search, no flicker, no scroll jumps, tmux/integrated-terminal compatibility.
- Claude Code command behavior: typing `/` shows commands and filters them in-session.
- Codex CLI: terminal-first local coding agent with clear approval modes.
- Pi TUI: differential rendering, synchronized output, editor components, slash/file autocomplete, stable terminal rendering.

## Existing assets that constrain the audit

- `autocode/tests/tui-references/` — Track 4 design-target ratchet. 14 named scenes (`ready`, `active`, `multi`, `plan`, `review`, `cc`, `recovery`, `restore`, `sessions`, `palette`, `diff`, `grep`, `escalation`, `narrow`) all live as PTY gates with deterministic triggers; manifest auto-generated from `tui-references/AutoCode TUI _standalone_.html`. Scene presets in `scene_presets.py`. Predicates in `predicates.py`. Run via `make tui-references`.
- `autocode/tests/tui-comparison/` — Track 1 runtime invariants (no crash, composer visible, etc.).
- `autocode/tests/vhs/` — self-vs-self PNG regression.
- `autocode/tests/pty/` — live PTY smoke harnesses.
- `autocode/rtui/` — current Rust TUI (sole interactive frontend; Go BubbleTea + Python inline deleted 2026-04-19).
- `docs/reference/rust-tui-architecture.md`, `docs/reference/rust-tui-rpc-contract.md`, `docs/reference/rpc-schema-v1.md` — current contracts.
- User-locked render contract (2026-04-22): default inline TUI must render full-screen, terminal resizing must keep working, multiple terminal sizes validated, native scrollback preserved. Codified in `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`.

---

# Program brief (verbatim, user-supplied)

You are working in the `Abbiirr/lowrescoder` repository.

We are starting the next AutoCode implementation phase. Do not jump straight into visual TUI coding. First establish the backend/TUI contracts, audit the current implementation, remove ambiguity from old Go/BubbleTea or overlay-era artifacts, and create deterministic fixtures for the new Rust TUI.

## Product direction

AutoCode is a terminal user interface for an AI coding agent.

It must feel familiar to Claude Code, Codex CLI, and Pi-style terminal agents, but better in a few specific areas:

- editable queued follow-ups while the agent is working
- safe evidence-first review
- clear protected-path escalation
- checkpoint/restore focus mode
- session resume/fork focus mode
- recovery with preserved draft
- bounded live output drawer
- no flicker, no jitter, no scroll jumps
- keyboard-first operation

The final TUI must be minimal by default:

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

Everything else must be one of:

```text
focus mode
bottom drawer
inline panel
composer-attached picker
rare decision rail
```

Forbidden in product TUI:

```text
centered overlays
dimmed modal backgrounds
floating modal windows
permanent sidebars
permanent right rail in default active state
state switcher in product
demo screen-number controls in product
Mac-specific Cmd/Option glyphs
dashboard/card-heavy UI
command center as default UI
```

The side rail is allowed only for:

```text
review approval
protected-path escalation
explicit command center power mode
```

## External behavior baseline

Use these baselines conceptually:

- Claude Code fullscreen behavior: fixed bottom input, transcript review/search, no flicker, no scroll jumps, tmux/integrated terminal compatibility.
- Claude Code command behavior: typing `/` shows commands and filters them inside the session.
- Codex CLI: terminal-first local coding agent with clear approval modes.
- Pi TUI: differential rendering, synchronized output, editor components, slash/file autocomplete, stable terminal rendering.

Do not copy branding or UI art. Copy the behavioral lessons.

---

# Work packet 1: repo audit and architecture freeze

## Goal

Before implementing the new TUI, produce a repo-grounded audit showing what backend/TUI features are already implemented, what is partial, and what is missing.

## Required commands to run first

Run from repo root:

```bash
git log --oneline --decorate -n 3
git show --stat --name-status HEAD
git show --stat --name-status HEAD~1
git show --stat --name-status HEAD~2

find docs -maxdepth 3 -type f | sort
find autocode -maxdepth 4 -type f | sort | sed -n '1,250p'

rg "overlay|modal|popup|backdrop|dim|centered|dialog" autocode docs -n || true
rg "queue|queued|followup|draft|submitted|steer|pending" autocode docs -n || true
rg "restore|checkpoint|rewind|diff|review|escalation|approval|permission|protected" autocode docs -n || true
rg "tui|rtui|fullscreen|renderer|drawer|composer|slash|palette|focus|transcript" autocode docs -n || true
rg "subagent|task|delegate|agent" autocode docs -n || true
rg "stdout|stderr|validation|command stream|tool result|result_payload" autocode docs -n || true
```

## Deliverable 1

Create:

```text
docs/audits/tui_backend_readiness.md
```

It must include:

```text
1. Last 3 commits summary
2. Current architecture summary
3. Rust TUI vs old Go/BubbleTea status
4. Backend feature inventory table
5. TUI feature inventory table
6. P0 blockers
7. P1 follow-ups
8. Files inspected
9. Tests discovered
10. Recommended first implementation sequence
```

Use this status vocabulary:

```text
ready
partial
missing
blocked
historical
demo-only
```

Feature inventory table must include at least:

```text
agent events
session reducer/replay
transcript persistence/review
composer/editor state
editable queue drafts
command registry
permissions/modes
protected paths
approval requests
structured diffs/hunks
checkpoint/restore/rewind
recovery state
validation stdout/stderr streams
session list/resume/fork/archive
search/file/symbol attachment
subagents/tasks
terminal renderer/no-flicker behavior
fixtures/tests
```

For each feature, answer:

```text
docs exist?
types/events exist?
reducer/state exists?
persistence exists?
tests exist?
TUI-ready?
issues
```

---

# Work packet 2: current architecture document

## Goal

Remove ambiguity about old Go/BubbleTea TUI vs current Rust TUI.

## Deliverable 2

Create:

```text
docs/tui/current-architecture.md
```

It must explicitly say:

```text
Current interactive TUI: Rust.
Backend: Python JSON-RPC backend.
Old Go/BubbleTea TUI: historical migration reference only.
New minimal shell work targets Rust only.
Product TUI must not use centered overlays or demo switchers.
```

Include:

```text
- current TUI entrypoint(s)
- backend server / transport entrypoint(s)
- JSON-RPC protocol files
- current test commands
- current PTY/snapshot commands if present
- known historical directories/docs that should not be used for new work
```

---

# Work packet 3: normalize feature contracts

## Goal

Create `docs/features/` contracts if missing or incomplete. Do not over-write existing good docs; extend or create missing files.

## Required files

Ensure these exist:

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

Each file must use this structure:

```text
# Feature name

## Purpose
## User-visible TUI surfaces
## Backend contract
## Event types
## State/reducer behavior
## Persistence behavior
## Commands/keybindings
## Failure/recovery behavior
## Tests and fixtures
## Acceptance criteria
## Open questions
```

## Important contracts to define

### Agent event base model

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

### Queue model

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

Queue behavior:

```text
Alt+Enter queues current composer draft.
Queued drafts remain editable until submitted.
Submitted queue items become transcript entries and read-only.
Collapsed queue is one row.
Expanded queue is a bottom drawer, not an overlay.
```

### Command registry

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

Registry rule:

```text
/ slash picker, Ctrl+Shift+P command focus mode, keybindings, and custom commands must all use the same command registry.
```

### Permission/risk model

```ts
type PermissionMode =
  | "suggest"
  | "accept-edits"
  | "auto"
  | "full-auto"
  | "review-needed"
  | "halted";

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

### Diff model

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

### Checkpoint model

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

### Recovery model

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

### Validation stream model

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

---

# Work packet 4: deterministic TUI fixtures

## Goal

Create JSONL fixtures the Rust TUI can render before live backend integration. These must be deterministic and small enough for PTY/snapshot tests.

## Deliverable 4

Create:

```text
fixtures/tui/ready.jsonl
fixtures/tui/active.jsonl
fixtures/tui/multitasking.jsonl
fixtures/tui/queue-drawer.jsonl
fixtures/tui/plan-inline.jsonl
fixtures/tui/live-drawer.jsonl
fixtures/tui/review.jsonl
fixtures/tui/diff-focus.jsonl
fixtures/tui/protected-path.jsonl
fixtures/tui/recovery.jsonl
fixtures/tui/restore-focus.jsonl
fixtures/tui/session-browser.jsonl
fixtures/tui/command-palette-focus.jsonl
fixtures/tui/slash-picker.jsonl
fixtures/tui/file-picker.jsonl
fixtures/tui/symbol-picker.jsonl
fixtures/tui/search-focus.jsonl
fixtures/tui/transcript-review.jsonl
fixtures/tui/command-center.jsonl
fixtures/tui/narrow.jsonl
```

Each fixture should represent backend events/state, not raw terminal text.

Each fixture should be renderable into the final UI shell:

```text
HUD
Transcript or focus region
Optional drawer
Optional queue strip
Composer
Hint line
```

---

# Work packet 5: TUI architecture plan, no implementation yet unless audit is complete

## Goal

Create the technical plan for the new Rust TUI shell.

## Deliverable 5

Create:

```text
docs/tui/minimal-rust-tui-implementation-plan.md
```

It must define these TUI modes:

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

It must define components:

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

It must define rendering constraints:

```text
fixed composer allocation
bounded drawer allocation
stable queue strip height
no full clear per token
synchronized output if supported
ANSI-safe wrapping
terminal width-aware truncation
resize handling
fake composer cursor
real cursor restored on crash
no scroll jumps
```

It must define the default visual grammar:

```text
model · effort · cwd · branch · permission · context · cost · state
sandbox · Δ/files · tasks · agents · q · checkpoint
```

It must define the canonical tool-call grammar:

```text
⏺ Read(path)
⏺ Search("pattern" scope)
⏺ Edit(path)
⏺ Run(command)
```

---

# Hard constraints

Do not:

```text
implement centered overlays
implement dimmed modal backgrounds
make command center the default UI
show side rail in default active session
show queue drawer by default
hide composer while streaming
parse human text to infer backend state
use old Go/BubbleTea TUI as target architecture
add new decorative spinner verb work
add new dashboard/card UI
```

Do:

```text
preserve current backend work if already implemented
audit before replacing
prefer typed events over string parsing
prefer fixtures before live integration
keep new TUI minimal
make keyboard controls explicit
write tests for contracts and fixtures
```

---

# Expected final output from this first run

At the end, report:

```text
1. Files changed
2. What was created
3. Backend readiness summary
4. Missing P0 items
5. TUI readiness summary
6. Whether implementation can begin
7. Exact next PR/task recommendation
8. Tests/checks run
```

If you discover that some required docs or contracts already exist under different names, do not duplicate blindly. Reference the existing docs, add missing sections, and create a small index file linking them.

Do not do a broad TUI rewrite in this first run unless the audit proves the contracts and fixtures are already present.

---

# Sequencing recommendation (Reviewer/Architect)

- Packet 1 (audit) lands first.
- Packets 2 and 3 may parallelize after Packet 1 closes (they share audit findings but don't depend on each other).
- Packet 4 depends on Packet 3 (fixtures realize the contracts).
- Packet 5 depends on Packets 1-4 (it synthesizes the plan from audit + contracts + fixtures).

# Reconciliation with Backend Robustness Tranche 4

**RESOLVED 2026-04-27 late.** User chose **Tranche 4 first, with Packet 3 (16 feature contracts) promoted to active prep slice (G0)** before C4.G1. Packets 1, 2, 4, 5 are **PARKED** for after Tranche 4 closes. Packet 3 contracts are designed to absorb Tranche 4's emitted typed shapes — 4 high-overlap contracts: `checkpoints-restore` ↔ G1, `permissions` + `protected-paths` ↔ G2 / G7', `validation-output` ↔ G4, `subagents-tasks` ↔ G13. C4.G1 auto-flows after Packet 3 reviewer APPROVE unless contracts expose a gap.

Builder routing: OpenCode primary, Codex fallback. Active Builder direction: `AGENTS_CONVERSATION.MD` Entry 1604.

---

_End of program brief._
