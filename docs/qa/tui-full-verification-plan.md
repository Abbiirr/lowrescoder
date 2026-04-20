# Full TUI Verification Plan

> Scope: verify the Go TUI end-to-end, including behavior, wire protocol, ANSI output, and visuals.
> Goal: catch regressions in all user-visible features, not just unit logic.

## 0. Priority Contract (Required)

1. **Primary gate:** core Phase 4 functionality must pass `docs/qa/phase4-vanilla-prompt-checklist.md` in inline mode.
2. **Secondary gate:** this TUI plan runs after primary gate pass, to verify rendering/parity and UX behavior.
3. If primary gate fails, stop TUI verification and fix functionality first.

## 1. Verification Layers

Use all layers together. No single layer is sufficient.

1. `L0` Unit/contract tests (Go): deterministic behavior in model/update/protocol.
2. `L1` Wire protocol checks (JSON-RPC): backend notifications/requests/responses are valid and complete.
3. `L2` ANSI transcript checks: terminal stream is captured and compared.
4. `L3` Screenshot checks: layout and visual regressions are detected.
5. `L4` Manual exploratory checks: real user flows and edge cases.

## 2. Feature Coverage Inventory

### Core Interaction

- Startup handshake (`stageInit -> stageInput`)
- Input/editing/submit behavior
- History navigation (`Up`/`Down`)
- Slash command parsing and dispatch
- Streaming and thinking display
- Queueing input while streaming
- Cancellation (`Esc`, `Ctrl+C`, `Ctrl+D`)
- Markdown rendering and separator behavior

### Workflow/Dialogs

- Approval dialog flow (allow/deny/session allow)
- Ask-user dialog flow (options/free text/escape)
- Session list and session picker resume flow
- Error surfaces and recovery

### Status/Indicators

- Status bar model/provider/mode
- Token/edit counters
- Layer indicator (`[L1]` / `[L2]` / `[L4]`)

### Commands (Current TUI Surface)

From `cmd/autocode-tui/commands.go`:
- `/exit`, `/quit`, `/q`
- `/new`
- `/sessions`, `/s`
- `/resume`
- `/help`, `/h`, `/?`
- `/model`, `/m`
- `/mode`, `/permissions`
- `/compact`
- `/init`
- `/shell`
- `/copy`, `/cp`
- `/freeze`, `/scroll-lock`
- `/thinking`, `/think`
- `/clear`, `/cls`
- `/index`

### Phase 4 UI Additions (When Implemented)

- Task/to-do visibility in TUI
- Subagent visibility/state transitions in TUI
- UI refresh correctness after task/subagent events

## 3. Artifact Bundle (Per Run)

Write all artifacts under:

`docs/qa/test-results/<timestamp>-tui-full/`

Required files:

1. `manifest.md` — run metadata (OS, terminal app, resolution, model, git commit).
2. `go-tests.log` — Go test output.
3. `wire.jsonl` — JSON-RPC stream capture (one message per line).
4. `session.ansi` — raw ANSI terminal capture.
5. `session.normalized.txt` — ANSI-normalized text view for diffing.
6. `screenshots/` — checkpoint PNGs (`S00`, `S01`, ...).
7. `assertions.md` — pass/fail table for each checkpoint and feature.

## 4. Standard Environment Profile

Lock the environment so diffs are meaningful:

1. Terminal size: `160x48` (or one team-standard size).
2. Font/line-height/theme fixed across baseline and candidate runs.
3. Same model/provider and approval mode.
4. Disable unrelated background output.

## 5. Execution Plan

### Step 0 — Functional Readiness Gate (Primary)

Run the vanilla prompt checklist first (inline mode) and require pass on core flows (tasks, plan mode, subagents, checkpoints, approvals) before continuing.

### Step A — Deterministic Test Lane (`L0`)

```bash
./scripts/store_test_results.sh tui-go-tests -- bash -lc "cd cmd/autocode-tui && go test ./... -v"
```

Pass gate:

- All tests pass.
- No skipped critical tests for update/protocol/view/session/approval/ask-user paths.

### Step B — Wire Protocol Lane (`L1`)

Run TUI with JSON-RPC capture enabled (stdout/stderr split if needed) and store `wire.jsonl`.

Assertions:

1. `on_status` arrives before first chat response.
2. `on_token` stream is ordered and non-corrupt.
3. `on_done` arrives after token stream for each turn.
4. approval/ask-user/session list messages decode into expected structs.
5. No malformed JSON-RPC frames.

### Step C — ANSI Capture Lane (`L2`)

Preferred tools:

1. `asciinema rec` (cross-platform where available).
2. `script` (Linux/WSL) as fallback.

Store raw output as `session.ansi`.

Normalization rules for `session.normalized.txt`:

1. Strip ANSI color/style sequences.
2. Normalize CRLF/LF.
3. Remove spinner-frame churn.
4. Keep semantic text (`You:`, tool lines, errors, command outputs, separators).

Diff baseline vs candidate on normalized output.

### Step D — Screenshot Lane (`L3`)

Capture screenshots at fixed checkpoints:

- `S00` Startup idle
- `S01` `/help` rendered
- `S02` Mid-stream response
- `S03` Post-stream response + separator
- `S04` Approval dialog
- `S05` Ask-user dialog
- `S06` Session picker
- `S07` Error state + recovery
- `S08` (Phase 4) task/subagent panel visible + live updates

Comparison:

1. Pixel diff (ImageMagick `compare`) with approved threshold.
2. Manual review for any diff in high-signal regions (status bar, dialog, panel, prompts).
3. Keep a `diff/` folder with visual diff overlays for failed checkpoints.

### Step E — Manual Flow Lane (`L4`)

Run high-value user flows:

1. New chat -> stream -> cancel -> continue.
2. Slash command batch (`/model`, `/mode`, `/shell`, `/copy`, `/clear`, `/resume`).
3. Approval and ask-user interactions.
4. Session resume from picker.
5. (Phase 4) to-do and subagent visibility + refresh behavior.

Record PASS/FAIL in `assertions.md`.

## 6. Baseline Management

Maintain golden artifacts for known-good TUI:

`docs/qa/tui-golden/<profile>/<checkpoint>.png`

`docs/qa/tui-golden/<profile>/session.normalized.txt`

Baseline update rules:

1. Only update goldens in explicit UX-change PRs.
2. Include rationale and before/after diffs.
3. Review by at least one non-author.

## 7. Release Gates

A TUI change is releasable only if:

1. `L0` Go tests pass.
2. `L1` wire protocol assertions pass.
3. `L2` normalized ANSI diff has no unexpected semantic regressions.
4. `L3` screenshot checkpoints pass threshold + manual review.
5. `L4` manual flows pass.

For Phase 4 readiness, add:

1. Task/to-do panel verified.
2. Subagent state rendering verified.
3. UI refresh verified for task/subagent events.

## 8. Suggested Cadence

Per PR:

1. `L0` + targeted `L1`.
2. Minimal screenshot set (`S00`, `S01`, `S03`).

Nightly/Pre-release:

1. Full `L0-L4` run.
2. Full screenshot set and ANSI diff.
3. Archive full artifact bundle under `docs/qa/test-results/`.
