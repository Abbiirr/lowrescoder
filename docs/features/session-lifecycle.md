# Session Lifecycle

## Purpose

Defines the contract for session creation, resumption, forking, archival, and halt transitions. Sessions are the primary unit of conversation state, persisted in SQLite, and accessed through JSON-RPC methods.

## User-visible TUI surfaces

- Session picker (triggered by `/sessions` or session-picker UI) showing session list with title, model, provider
- `/new` command creating a fresh session
- `/resume <id-or-prefix>` restoring a previous session
- `/fork` (via `session.fork` RPC) creating a branch from the current session
- Status bar showing current session ID and model
- Recovery banner when a session encounters a halt

## Backend contract

### Session states

```
new → active → idle → active (resume)
                  ↘ archived
                  ↘ halted → recovered → active
```

### RPC methods

| Method | Direction | Params | Result | Notes |
|---|---|---|---|---|
| `session.new` | Frontend → Backend | `title?: string` | `session_id: string` | Creates fresh session |
| `session.list` | Frontend → Backend | _(none)_ | `sessions: SessionInfo[]` | Lists all sessions |
| `session.resume` | Frontend → Backend | `session_id: string` | `session_id: string, title?: string` | Resumes by exact or prefix match |
| `session.fork` | Frontend → Backend | _(none)_ | `new_session_id: string` | Branches current session |

### Session info schema

```ts
interface SessionInfo {
  id: string;
  title: string;
  model: string;
  provider: string;
}
```

### Current implementation

- SQLite-backed sessions in `autocode/src/autocode/session/`
- Session resume supports prefix matching with ambiguity errors
- Fork creates a new session copying the current message history
- Session teardown runs consolidation (deterministic + optional LLM enrichment)

## Event types

- `SessionStateEvent` (from `on_status`): emitted on session start/resume with model, provider, mode, session_id
- `RecoveryEvent` (from `on_error`): emitted on session halt
- `on_chat_ack`: emitted when a chat request is acknowledged for the session

## State/reducer behavior

- Frontend tracks `session_id` in `AppState`
- On `session.new`: clear transcript, reset cost counters, reset task/subagent state
- On `session.resume`: reload transcript from backend, restore scroll position
- On `session.fork`: keep current transcript, new session_id returned
- On session switch: all frontend-local state resets (scroll offset, composer buffer, stage)

## Persistence behavior

- Messages and tool-call rows are persisted per-session in SQLite
- Checkpoints preserve bounded recent message history plus assistant tool-call rows
- Episode retention creates summary rows before pruning old events
- Memory consolidation persists durable learnings into project memory store

## Commands/keybindings

| Command | Keybinding | Action |
|---|---|---|
| `/new` | — | Start a new session |
| `/sessions` (`/s`) | — | List sessions in picker |
| `/resume` | — | Resume a session by ID or prefix |
| `/exit` (`/quit`, `/q`) | `Ctrl+C` (double) | Exit application |

## Failure/recovery behavior

- If `session.resume` fails with ambiguous prefix, backend returns an error with matching IDs
- If session store is corrupted, backend returns error; frontend shows recovery options
- If backend crashes mid-session, frontend detects stale request and shows recovery banner
- Composer state (`preservedDraft`) survives session halt/recovery (see `recovery.md`)

## Tests and fixtures

- `autocode/tests/unit/test_backend_server.py` — session create/list/resume/fork
- `autocode/tests/unit/test_session_store.py` — SQLite persistence
- `autocode/tests/unit/test_checkpoint.py` — checkpoint save/restore
- Transport conformance tests in `autocode/tests/unit/test_backend_transport_conformance.py`

## Acceptance criteria

- [ ] All four session RPC methods documented with params and result shapes
- [ ] Session state machine transitions enumerated
- [ ] Prefix-match resume behavior documented
- [ ] Fork behavior documented (copies history, new ID)
- [ ] Session teardown consolidation documented

## Open questions

- Should session archival be explicit (`/archive`) or automatic after inactivity?
- What is the maximum session age before consolidation pruning?
- Should fork carry metadata linking to the parent session?
- Cross-reference: `subagents-tasks.md` for worktree-spawned sessions that may have independent lifecycles
