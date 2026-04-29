# Agent Events

## Purpose

Defines the canonical discriminated-union event taxonomy that the backend emits and the TUI consumes. Every backend-to-frontend notification is a typed `AgentEvent`; human-text parsing for backend state is forbidden.

## User-visible TUI surfaces

- Transcript lines rendered from `AssistantTextEvent` and `UserMessageEvent`
- Tool-activity spinner and tool-call detail from `ToolStartEvent` / `ToolResultEvent`
- Thinking section toggled by thinking events
- Task/subagent panel from `SubagentEvent` and `SessionStateEvent`
- Approval modal from `ApprovalRequestEvent`
- Recovery banner from `RecoveryEvent`
- Plan/task board from `PlanEvent`
- Validation drawer from `ValidationEvent` / `CommandStartEvent` / `CommandOutputEvent` / `CommandEndEvent`

## Backend contract

### Typed model

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

### Current RPC methods that carry these events

| RPC notification | Event mapping | Notes |
|---|---|---|
| `on_token` | `AssistantTextEvent` (streamed) | Text appended to transcript |
| `on_thinking` | `AssistantTextEvent` (thinking variant) | Gated by `/thinking` toggle |
| `on_tool_call` | `ToolStartEvent` / `ToolResultEvent` | Status field: `pending`, `running`, `done`, `failed`, `cancelled` |
| `on_done` | `SessionStateEvent` (turn complete) | Carries `tokens_in`, `tokens_out`, `cancelled`, `layer_used` |
| `on_status` | `SessionStateEvent` (metadata) | Model, provider, mode, session_id |
| `on_error` | `RecoveryEvent` (error) | Error message string |
| `on_warning` | `RecoveryEvent` (warning) | Non-fatal upstream issue |
| `on_cost_update` | `SessionStateEvent` (cost) | Cost, tokens_in, tokens_out |
| `on_task_state` | `SubagentEvent` | Tasks + subagents list |
| `on_chat_ack` | `SessionStateEvent` (ack) | Request acknowledged |
| `on_tool_request` | `ApprovalRequestEvent` | Tool name + args, awaiting approval |
| `on_ask_user` | `ApprovalRequestEvent` (ask-user variant) | Question + options + allow_text |

### Events not yet emitted (planned)

| Event | Status | Notes |
|---|---|---|
| `EditEvent` | planned | Will carry file path + edit description |
| `DiffEvent` | planned | Will carry structured diff payload |
| `PlanEvent` | planned | Will signal plan mode transitions |
| `QueueEvent` | planned | Will signal queue state changes |
| `CheckpointEvent` | planned | Will signal checkpoint save/restore |
| `CommandStartEvent` | planned | Will carry validation command start |
| `CommandOutputEvent` | planned | Will carry stdout/stderr tail |
| `CommandEndEvent` | planned | Will carry exit status |
| `ValidationEvent` | planned | Will carry pass/fail/cancelled status |

## Event types

All event types inherit `BaseEvent`. The `type` discriminator string maps to the union variant name (e.g., `"UserMessageEvent"`, `"ToolStartEvent"`). The backend must emit typed JSON objects; the frontend must never parse free-form text to infer event type.

## State/reducer behavior

- Frontend reducer accumulates events into a chronological transcript
- `status` field drives stage transitions: `pending` → `running` → `done`/`failed`/`cancelled`
- `parentId` links tool results to their originating tool start
- Duplicate event IDs must be silently deduplicated by the frontend

## Persistence behavior

- Events are persisted as rows in the SQLite session store
- Episode retention prunes old events but preserves deterministic summary rows
- Event replay from storage must produce identical transcript state

## Commands/keybindings

No direct keybindings. Events are backend-emitted; the frontend renders them.

## Failure/recovery behavior

- If a malformed event arrives, the frontend logs a warning and skips it (never crashes)
- If event ordering is disrupted, `timestamp` is the authoritative sort key
- If `on_error` fires, the frontend enters recovery mode (see `recovery.md`)

## Tests and fixtures

- Unit tests: `autocode/tests/unit/test_backend_server.py`, `autocode/tests/unit/test_backend_chat.py`
- RPC schema conformance: `autocode/tests/pty/fixtures/rpc-schema-v1/`
- Rust schema round-trip: `autocode/rtui/src/rpc/schema.rs` tests
- Transport conformance: `autocode/tests/unit/test_backend_transport_conformance.py`

## Acceptance criteria

- [ ] Every backend notification maps to a named `AgentEvent` variant
- [ ] No frontend code parses event text to infer type
- [ ] All current RPC methods enumerated in this contract
- [ ] Planned events marked as `planned` (not implemented)

## Open questions

- Should `EditEvent` and `DiffEvent` be merged into a single `FileChangeEvent` with a `kind` discriminator?
- What is the exact schema for `PlanEvent` — does it mirror `PlanSetResult` or carry additional fields?
- Should `QueueEvent` be emitted on every state transition or only on user-initiated actions?
- How should the frontend handle events from a different session (e.g., cross-session subagent events)?
