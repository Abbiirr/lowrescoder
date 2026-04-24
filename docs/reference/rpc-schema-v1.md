# RPC Schema v1

Stage 0A source of truth for the Rust TUI <-> Python backend JSON-RPC contract.

## Envelope

- Notifications: `{"jsonrpc":"2.0","method":"<name>","params":{...}}`
- Requests: `{"jsonrpc":"2.0","id":<int>,"method":"<name>","params":{...}}`
- Responses: `{"jsonrpc":"2.0","id":<int>,"result":{...}}`

## Canonical backend -> TUI notifications

- `on_status`: `model`, `provider`, `mode`, optional `session_id`
- `on_error`: `message`
- `on_warning`: `message`
- `on_token`: `text`
- `on_thinking`: `text`
- `on_done`: `tokens_in`, `tokens_out`, optional `cancelled`, optional `layer_used`
- `on_tool_call`: `name`, `status`, optional `args`, optional `result`
- `on_task_state`: `tasks[]`, `subagents[]`
- `on_cost_update`: `cost`, `tokens_in`, `tokens_out`

## Canonical backend -> TUI requests

- `on_tool_request`: `tool`, `args` -> response `{approved, session_approve?}`
- `on_ask_user`: `question`, optional `options[]`, optional `allow_text` -> response `{answer}`

## Canonical TUI -> backend requests

- `chat`
- `cancel`
- `command`
- `command.list`
- `session.new`
- `session.list`
- `model.list`
- `provider.list`
- `session.resume`
- `task.list`
- `subagent.list`
- `subagent.cancel`
- `plan.status`
- `plan.set`
- `config.get`
- `config.set`
- `memory.list`
- `checkpoint.list`
- `checkpoint.restore`
- `plan.export`
- `plan.sync`
- `steer`
- `session.fork`
- `shutdown`

## Behavioral Guarantees

The method inventory above is only half the contract. The following
runtime behaviors are also part of schema v1.

### Chat liveness

- A backend that accepts a `chat` request must emit `on_chat_ack` quickly,
  before the request is allowed to look stale from the frontend. Current
  default frontend stale detection is `30s`, controlled by
  `AUTOCODE_STALE_REQUEST_TIMEOUT_SECS`.
- `on_chat_ack` may repeat as a heartbeat while the request is still alive
  and before first visible output arrives. Current default backend heartbeat
  cadence is `15s`.
- Any of `on_chat_ack`, `on_token`, or `on_thinking` counts as liveness for
  an active chat request and must prevent stale-request recovery while the
  turn is still progressing.
- A completed turn must eventually emit `on_done` exactly once for that
  request, even if the turn ended in cancellation or after an `on_error`.
- `on_warning` is a non-fatal visibility channel: it must never replace
  `on_error`, but it may be emitted during long retries or degraded upstream
  states so the frontend does not look silently hung.

### Session reset semantics

- A successful `session.new` or `session.resume` response represents a
  frontend-local reset boundary.
- After a successful session switch, the frontend must clear prior
  streaming state, pending chat requests, stale-request banners, task and
  subagent projections, token/cost counters, and any session-scoped local
  error state tied to the old session.
- The backend remains authoritative for durable session history; the
  frontend reset only applies to local runtime state.

### Ownership model

- Backend-authoritative state includes session identity, durable messages,
  task lists, subagent lists, checkpoints, memory, model/provider/config
  values, and slash-command execution semantics.
- Frontend-local state includes composer contents, palette state, picker
  cursor/filter state, history ranking, scroll offset, staged recovery UI,
  and other purely presentational interaction state.

### Task and subagent projection

- `on_task_state` is the canonical projection of current task/subagent
  state from backend to frontend.
- The frontend may render or temporarily cache that projection, but it
  must treat the backend payload as the source of truth.

## Historical note

Stage 4 removed the temporary Stage 0 compatibility aliases. The
canonical method names listed above are now the only supported RPC
surface.

## Stage 2 inventory sources declared in v1

Stage 0A explicitly declares `command.list`, `model.list`, `provider.list`, and `session.list` so Stage 2 can build backend-owned overlays without depending on Stage 0B.
