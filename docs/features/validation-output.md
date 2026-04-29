# Validation Output

## Purpose

Defines the contract for command-stream events emitted during build/test validation after edits. Covers stdout/stderr/diagnostics streaming and status transitions (running/passed/failed/cancelled). Designed to absorb Tranche 4 G4 (auto-verify-after-edit) shapes.

## User-visible TUI surfaces

- Validation drawer: bounded drawer at the bottom of the screen showing command output
- Status badge: running (spinner), passed (green), failed (red), cancelled (grey)
- stdout/stderr tail: last N lines of output
- Hidden-lines counter: "N lines hidden" indicator
- Drawer is dismissible but auto-opens on validation start

## Backend contract

### Typed model

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

### G4 auto-verify behavior (implemented backend shape)

After an edit operation:
1. Backend determines whether post-edit verification is enabled globally and for the edited file's language.
2. If the file has a registered LSP adapter, `verify_after_edit(...)` requests diagnostics through the subprocess LSP client.
3. Unsupported file types or disabled languages are skipped without failing the edit.
4. Diagnostics are normalized to `path:line:column [severity] message` and fed back through the tool result so the next agent iteration sees them.
5. Persistent failures after `agent.verify.max_iterations` surface a warning that no automatic rollback occurred and point the user at `/rollback`.
6. If the configured cost limit has been crossed, retry guidance is halted and the cost-limit state is surfaced.

Dedicated validation drawer events are still planned frontend work. The current backend shape is transcript/tool-result feedback rather than `CommandStartEvent` / `CommandOutputEvent` streaming.

### Status transitions

```
running → passed
running → failed
running → cancelled (user interrupt)
```

## Event types

- `VerificationResult` (implemented backend): carries checked files, skipped files, and normalized diagnostics.
- `VerificationDiagnostic` (implemented backend): carries path, one-based line/column, severity, and message.
- `CommandStartEvent` (planned frontend drawer): carries `commandId`, `command`, `startedAt`
- `CommandOutputEvent` (planned frontend drawer): carries `commandId`, stream (`stdout`|`stderr`), `text`
- `CommandEndEvent` (planned frontend drawer): carries `commandId`, `status`, `endedAt`
- `ValidationEvent` (planned frontend drawer): carries overall validation result

## State/reducer behavior

- Frontend maintains a map of `commandId → CommandStream` for active validations
- New output appends to `stdoutTail` or `stderrTail` (bounded, FIFO)
- `hiddenLines` counter tracks lines beyond the visible tail
- Drawer auto-opens when a `CommandStartEvent` arrives
- Drawer auto-closes when status transitions to `passed` (configurable)

## Persistence behavior

- Command output is not persisted to SQLite (transient, session-scoped)
- Validation results may be stored as checkpoint metadata (cross-reference `checkpoints-restore.md`)
- Previous validation results are not accessible after session close

## Commands/keybindings

| Key/Command | Context | Action |
|---|---|---|
| Validation drawer auto-open | On `CommandStartEvent` | Opens drawer |
| `Esc` | Validation drawer | Dismiss drawer (output continues in background) |
| `Ctrl+Q` | Global | Toggle validation drawer visibility |

## Failure/recovery behavior

- If validation command hangs: user can cancel via `Ctrl+C` → status transitions to `cancelled`
- If validation command crashes: status transitions to `failed` with error output
- On persistent validation failure with auto-verify: no automatic rollback occurs; `/rollback` is offered in the tool-result feedback
- Bounded output: if stdout/stderr exceeds tail buffer, older lines are dropped

## Tests and fixtures

- `S-TRUNCATE` verification: adaptive tool-result truncation preserves structure
- Artifact: `autocode/docs/qa/test-results/20260425-165646-s-truncate-verification.md`
- G4 auto-verify TDD evidence: `autocode/tests/unit/test_auto_verify.py`
- G4 auto-verify PTY smoke: `autocode/tests/pty/pty_smoke_auto_verify.py`

## Acceptance criteria

- [ ] `CommandStream` typed model embedded
- [ ] Status transitions documented (running → passed/failed/cancelled)
- [ ] stdout/stderr tail semantics documented (bounded, FIFO)
- [ ] Bounded drawer rendering rules documented
- [x] G4 auto-verify integration shape documented
- [ ] Cross-reference to `checkpoints-restore.md` for rollback-on-failure

## Open questions

- Default tail buffer size — how many lines of stdout/stderr to keep?
- Should validation results appear in the transcript/tool result only or also in a future drawer?
- How to handle concurrent validations (multiple commands running simultaneously)?
