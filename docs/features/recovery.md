# Recovery

## Purpose

Defines the recovery state contract when the backend halts, crashes, or encounters an error. The `preservedDraft` field is non-negotiable — composer state must survive halt/error/recovery. Recovery presents the user with options to continue, rollback, or start fresh.

## User-visible TUI surfaces

- Recovery banner: replaces the normal status area when recovery is needed
- Recovery options presented as numbered choices:
  1. Retry last action
  2. Rollback to last checkpoint
  3. Start new session
  4. Continue without recovery
  5. Preserved draft shown in composer
- Error summary displayed in the banner
- No centered modal — recovery uses the existing status/banner area

## Backend contract

### Typed model

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

```ts
interface RecoveryTimelineItem {
  eventId: string;
  timestamp: string;
  description: string;
  type: "action" | "error" | "checkpoint";
}

interface RecoveryOption {
  id: number;
  label: string;
  description: string;
  action: "retry" | "rollback" | "new_session" | "continue";
}
```

### `preservedDraft` semantics (non-negotiable)

When recovery is triggered:
1. The current composer text is captured into `RecoveryState.preservedDraft`
2. The recovery banner is shown with options
3. On any recovery action, `preservedDraft` is restored to the composer
4. The user never loses in-progress text

### Recovery triggers

- Backend crash (process dies)
- Backend error (`on_error` with fatal severity)
- Stale request detected (no response within timeout)
- Tool execution failure in critical path
- Session corruption detected

## Event types

- `RecoveryEvent` (from `on_error`): carries error summary and triggers recovery mode
- `RecoveryEvent` (from `on_warning`): non-fatal, shown as banner but no recovery mode

## State/reducer behavior

- Frontend tracks stage: `Idle` | `Active` | `Recovery`
- On recovery trigger: transition to `Recovery` stage
- Recovery keys:
  - `e` (1): retry last action
  - `r` (2): rollback to last checkpoint
  - `w` (3): start new session
  - `c` (4): continue without recovery
  - `p` (5): preserved draft action
- On recovery action: stage transitions back to `Idle`, preservedDraft restored to composer
- Composer is disabled during recovery stage (text is read-only in the preserved display)

## Persistence behavior

- `preservedDraft` is stored in frontend memory during recovery
- If the frontend process itself crashes, the draft is lost (no disk persistence for composer buffer)
- Recovery state is not persisted to SQLite — it is transient per-incident

## Commands/keybindings

| Key | Context | Action |
|---|---|---|
| `e` | Recovery | Retry last action |
| `r` | Recovery | Rollback to last checkpoint |
| `w` | Recovery | Start new session |
| `c` | Recovery | Continue without recovery |
| `p` | Recovery | Restore preserved draft |
| `Esc` | Recovery | Dismiss recovery banner (same as `c`) |

## Failure/recovery behavior

- If recovery itself fails (e.g., rollback target missing), offer a reduced option set
- If the backend is completely unreachable, only "start new session" and "continue" are available
- Double recovery (error during recovery) shows the original error plus the new one

## Tests and fixtures

- Track 4: `recovery` scene — recovery banner rendering
- Reducer tests for recovery key handling in `autocode/rtui/src/state/reducer.rs`
- `S-CKPTMSG` verification: checkpoint restore with message history
- Artifact: `autocode/docs/qa/test-results/20260425-193136-s-ckptmsg-verification.md`

## Acceptance criteria

- [ ] `RecoveryState` typed model embedded with `preservedDraft` field
- [ ] `preservedDraft` semantics explicitly stated: composer text survives halt/error
- [ ] Recovery options enumerated with keybindings
- [ ] Recovery triggers documented
- [ ] No centered modal for recovery UI
- [ ] Cross-reference to `checkpoints-restore.md` for rollback option

## Open questions

- Should `RecoveryTimelineItem` include the full event payload or just a summary?
- Maximum timeline length before truncation?
- Should recovery state persist across frontend restarts?
- How to handle recovery when both backend and checkpoint store are corrupted?
