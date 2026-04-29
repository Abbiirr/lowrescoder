# Checkpoints and Restore

## Purpose

Defines the contract for checkpoint creation, listing, restore, and rollback semantics. Checkpoints capture session state at specific points, enabling undo and recovery. This contract is designed to absorb Tranche 4 G1 (per-tool-call atomic checkpoint with diff-rollback) shapes.

## User-visible TUI surfaces

- `/checkpoint` command: list saved checkpoints
- `/checkpoint save <label>`: save a named checkpoint
- `/undo`: restore the most recent checkpoint
- `/rollback` (G1): list per-tool checkpoints with diff preview; restore only via explicit `restore <id>`
- Checkpoint list showing: ID, label, timestamp, files changed, tests passed
- Diff preview in rail-mode surface during rollback review

## Backend contract

### Typed model

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

### G1 extension

Per-tool-call atomic checkpoints extend the base model:

```ts
interface PerToolCheckpoint extends Checkpoint {
  parentToolCallId: string;
  toolCallIdx: number;
  kind: "session" | "pre_tool" | "post_tool";
}
```

### Snapshot mechanism (G1)

- Local file copies under `~/.autocode/snapshots/<session_id>/<tool_call_id>/` ONLY
- No `git stash` (per AGENTS.md "no tree-mutating git commands")
- Snapshot dir layout: `<session_id>/<tool_call_id>/<relative-path-of-touched-file>`
- Bounded retention: last N=50 per-tool checkpoints per session
- Configurable via `agent.checkpoints.per_tool_retention`

### Rollback execution (G1)

- `/rollback` with no args: list last N pre-tool checkpoints with diff preview
- `/rollback <id>`: preview that checkpoint and show the explicit restore command
- `/rollback --last`: preview the most recent pre-tool checkpoint and show the explicit restore command
- `/rollback restore <id>`: restore that checkpoint from its local snapshot
- Rollback mechanism: agent overwrites working-tree files from local snapshot directory
- No `git checkout`/`git restore` — user may run those manually if preferred

### RPC methods

| Method | Direction | Params | Result |
|---|---|---|---|
| `checkpoint.list` | Frontend → Backend | _(none)_ | List of `Checkpoint` objects |
| `checkpoint.restore` | Frontend → Backend | checkpoint ID | Restored session state |
| `/undo` | Frontend → Backend | _(none)_ | Restores most recent checkpoint |
| `/rollback` | Frontend → Backend | no args, ID, `--last`, or `restore <id>` | Lists, previews, or restores per-tool checkpoint |

## Event types

- `CheckpointEvent` (planned): emitted on checkpoint save/restore
- `on_tool_call` with status transitions during checkpoint creation

## State/reducer behavior

- Checkpoint list is fetched on demand (not cached in frontend)
- Restore clears current transcript to the checkpoint point
- Per-tool checkpoints appear in a dedicated list view with diff summaries
- Rollback confirmation is always required (never auto-rollback)

## Persistence behavior

- Checkpoints stored in SQLite via `autocode/src/autocode/session/checkpoint_store.py`
- Checkpoint data includes: task DAG state, bounded message history, assistant tool-call rows
- Per-tool snapshots stored on disk under `~/.autocode/snapshots/`
- Retention overflow deletes oldest snapshot directories

## Commands/keybindings

| Command | Aliases | Action |
|---|---|---|
| `/checkpoint` | `/ckpt` | List checkpoints |
| `/checkpoint save <label>` | — | Save named checkpoint |
| `/undo` | — | Restore most recent checkpoint |
| `/rollback` | `/rb` | List per-tool checkpoints |
| `/rollback --last` | — | Preview most recent per-tool checkpoint |
| `/rollback <id>` | — | Preview specific per-tool checkpoint |
| `/rollback restore <id>` | — | Restore specific per-tool checkpoint |

## Failure/recovery behavior

- If checkpoint restore fails, session state is unchanged (atomic restore)
- If snapshot directory is missing, rollback restores task state and reports that file snapshot restoration was unavailable
- If disk is full during snapshot, the tool call still proceeds but checkpoint is skipped with a warning
- Restore is user-confirmable — never automatic

## Tests and fixtures

- `autocode/tests/unit/test_checkpoint.py` — checkpoint save/restore tests
- `S-CKPTMSG` verification: checkpoint includes bounded message history
- Artifact: `autocode/docs/qa/test-results/20260425-193136-s-ckptmsg-verification.md`
- G1 TDD evidence: `autocode/tests/unit/test_commands.py` rollback parser tests
- G1 smoke evidence: `autocode/tests/pty/pty_smoke_rollback.py`

## Acceptance criteria

- [ ] `Checkpoint` typed model embedded
- [ ] Per-tool-checkpoint extension model documented (G1 shape)
- [ ] Snapshot mechanism documented (local file copies, no git stash)
- [ ] Rollback semantics: user-confirmable, never auto
- [ ] Retention behavior documented (N=50, configurable)
- [ ] All checkpoint-related commands enumerated
- [ ] Cross-reference to `recovery.md` for recovery flow using checkpoints

## Open questions

- Should checkpoint labels be unique per session?
- How should the UI present a diff preview during rollback confirmation?
- Should per-tool checkpoints be automatically pruned on session close?
- Cross-reference: `validation-output.md` for auto-verify triggering checkpoint save (G4)
