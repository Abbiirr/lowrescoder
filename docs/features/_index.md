# Feature Contracts Index

> Cross-links the 16 feature-contract files, the backend features inventory, and the feature behavior inventory.
> Last updated: 2026-04-27.
> Source: Packet 3 prep slice per `AGENTS_CONVERSATION.MD` Entry 1604.

## Feature Contracts (16)

Each contract uses an 11-section structure: Purpose / User-visible TUI surfaces / Backend contract / Event types / State/reducer behavior / Persistence behavior / Commands/keybindings / Failure/recovery behavior / Tests and fixtures / Acceptance criteria / Open questions.

| Contract | File | Embedded typed models | Tranche 4 overlap |
|---|---|---|---|
| Agent Events | `agent-events.md` | `AgentEvent` union + `BaseEvent` interface | — |
| Session Lifecycle | `session-lifecycle.md` | `SessionInfo` | — |
| Transcript | `transcript.md` | `TranscriptMessage` | — |
| Composer | `composer.md` | `ChatParams` | — |
| Queue | `queue.md` | `QueueItem` + `QueueItemState` | — |
| Commands | `commands.md` | `CommandDefinition` + same-registry rule | — |
| Permissions | `permissions.md` | `PermissionMode` + `RiskFacts` | G2 / G7' |
| Protected Paths | `protected-paths.md` | (pattern matcher) | G2 / G7' |
| Diff Review | `diff-review.md` | `FileDiff` + `DiffHunk` + `DiffLine` | — |
| Checkpoints and Restore | `checkpoints-restore.md` | `Checkpoint` + `PerToolCheckpoint` | G1 |
| Recovery | `recovery.md` | `RecoveryState` (with `preservedDraft`) | — |
| Validation Output | `validation-output.md` | `CommandStream` | G4 |
| Subagents and Tasks | `subagents-tasks.md` | `TaskEntry` + `SubagentEntry` | G13 |
| Search, File, Symbol | `search-file-symbol.md` | `FileReference` + `SymbolEntry` | — |
| TUI Rendering | `tui-rendering.md` | (layout contract) | — |
| Terminal Compatibility | `terminal-compat.md` | (compatibility requirements) | — |

## Inventory Docs (pre-existing)

| Doc | File | Scope |
|---|---|---|
| Backend Features Inventory | `backend_features.md` | Current-state backend implementation inventory |
| Feature Behavior Inventory | `features_behavior.md` | Runtime decomposition, frontend/backend ownership, coupling seams |

## Cross-references

- Tranche 4 master plan: `docs/plan/backend-robustness-tranche-4-plan.md`
- Tranche 4 checklist: `docs/plan/backend-robustness-tranche-4-checklist.md`
- New TUI kickoff brief: `docs/plan/backend-first-tui-kickoff-2026-04-27.md`
- RPC schema v1: `docs/reference/rpc-schema-v1.md`
- Rust TUI architecture: `docs/reference/rust-tui-architecture.md`
- Track 4 PTY ratchet: `autocode/tests/tui-references/`
- Track 1 runtime invariants: `autocode/tests/tui-comparison/`
