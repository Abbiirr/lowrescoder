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
- `on_tool_call`: `name`, `status`, optional `args`, optional `result`,
  optional `result_payload`
  - `result` remains the human-readable transcript string.
  - `result_payload` is structured UI data emitted on completed/successful
    search/diff/edit tools.
  - Search payload:
    `{"kind":"search","query":"...","hits":[{"path":"...","line":1,"snippet":"..."}]}`
    for `search_text`, `grep_content`, `search_code`, and `semantic_search`.
  - Diff payload:
    `{"kind":"diff","source":"...","files":[{"path":"...","added":1,"removed":0,"hunks":["..."]}]}`
    for `git_diff`, `write_file`, `edit_file`, `apply_patch`, and `multi_edit`.
- `on_task_state`: `tasks[]`, `subagents[]`
- `on_cost_update`: `cost`, `tokens_in`, `tokens_out`

## Canonical backend -> TUI requests

- `on_tool_request`: `tool`, `args` -> response `{approved, session_approve?}`
- `on_ask_user`: `question`, optional `options[]`, optional `allow_text` -> response `{answer}`

## Canonical TUI -> backend requests

- `chat`
- `kairos.tick`
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

### Transport hosts

- Stdio and TCP carry the same newline-delimited JSON-RPC envelope.
- Host adapters target the public `RpcApplication` protocol:
  `dispatch_rpc_request`, `route_rpc_response`, and `emit_response`.
  Private `BackendServer` methods are not part of the adapter contract.
- TCP attach mode is local-loopback only by default. Non-loopback bind hosts
  are refused by the CLI and host adapter unless a future explicit remote mode
  is added.
- The TCP host supports one active frontend client at a time. Additional
  connections wait behind the active connection rather than sharing backend
  state concurrently.
- TCP outbound messages are serialized through one writer/drain path so slow
  clients apply back-pressure without spawning concurrent drain tasks.

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

### KAIROS tick semantics

- `kairos.tick` accepts `message`, optional `session_id`, `tick_id`, and
  `read_only` params. It is the dedicated proactive-tick entrypoint used by
  `autocode daemon --watch` when KAIROS is enabled.
- `read_only=true` is backend-enforced by temporarily running the tick turn in
  `AgentMode.REVIEW`, which blocks tools marked as filesystem-mutating or
  shell-executing, then restoring the prior session mode after the turn.
- `read_only=false` preserves the current session mode and is exposed through
  the daemon as `--allow-mutations`.
- A KAIROS tick follows the same liveness contract as `chat`: accepted requests
  must emit `on_chat_ack`, stream visible output when available, and eventually
  emit `on_done`.

### Thinking mode

- `/thinking` toggles the backend session's model-reasoning gate for future
  chat turns, not just frontend rendering. `/thinking on` and `/thinking off`
  are deterministic forms; bare `/thinking` still toggles.
- When thinking mode is on, `AgentLoop.run()` may still reduce provider
  reasoning per iteration via middleware. When thinking mode is off,
  middleware cannot re-enable provider reasoning for that turn.
- OpenRouter requests sent to `openrouter.ai` include
  `reasoning.enabled=true|false`. OpenAI-compatible gateways that do not expose
  OpenRouter's reasoning extension omit the provider-specific field and emit a
  single `on_warning` if the backend cannot enforce a disabled-thinking request.
- Ollama tool-chat requests include `think=true|false` when the installed SDK
  accepts that request parameter. Older SDKs fall back without the parameter
  and emit at most one `on_warning` per provider instance.
- `on_thinking` remains the streaming notification for reasoning text when a
  provider produces it.

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

### Checkpoint restore

- `checkpoint.restore` restores the checkpoint's task snapshot and, when the
  checkpoint was saved with a session-store snapshot, replaces durable message
  history and assistant tool-call rows before adding the restore marker.

## Historical note

Stage 4 removed the temporary Stage 0 compatibility aliases. The
canonical method names listed above are now the only supported RPC
surface.

## Stage 2 inventory sources declared in v1

Stage 0A explicitly declares `command.list`, `model.list`, `provider.list`, and `session.list` so Stage 2 can build backend-owned overlays without depending on Stage 0B.
