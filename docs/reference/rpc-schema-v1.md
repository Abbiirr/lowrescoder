# RPC Schema v1

Stage 0A source of truth for the Rust TUI <-> Python backend JSON-RPC contract.

## Envelope

- Notifications: `{"jsonrpc":"2.0","method":"<name>","params":{...}}`
- Requests: `{"jsonrpc":"2.0","id":<int>,"method":"<name>","params":{...}}`
- Responses: `{"jsonrpc":"2.0","id":<int>,"result":{...}}`

## Canonical backend -> TUI notifications

- `on_status`: `model`, `provider`, `mode`, optional `session_id`
- `on_error`: `message`
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

## Historical note

Stage 4 removed the temporary Stage 0 compatibility aliases. The
canonical method names listed above are now the only supported RPC
surface.

## Stage 2 inventory sources declared in v1

Stage 0A explicitly declares `command.list`, `model.list`, `provider.list`, and `session.list` so Stage 2 can build backend-owned overlays without depending on Stage 0B.
