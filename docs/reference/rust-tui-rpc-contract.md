# Rust TUI RPC Contract

## Framing Invariants

- One JSON object per line
- UTF-8 encoding, LF-terminated (`\n`)
- `"jsonrpc": "2.0"` required on every message
- Notification: `id` absent or null, `method` set
- Request: `id` set (integer), `method` set
- Response: `id` set, `method` absent
- Error response: `{"jsonrpc":"2.0","id":N,"error":{"code":C,"message":"..."}}`

## Notifications (Python → Rust, id=null)

| Method | Params | Description |
|---|---|---|
| `on_token` | `{text: string}` | Streaming token text |
| `on_thinking` | `{text: string}` | Thinking/reasoning text |
| `on_done` | `{tokens_in: u32, tokens_out: u32, cancelled: bool, layer_used: u32}` | Response complete |
| `on_tool_call` | `{name: string, status: string, result?: string, args?: string}` | Tool execution status |
| `on_error` | `{message: string}` | Error notification |
| `on_status` | `{model: string, provider: string, mode: string, session_id?: string}` | Backend status |
| `on_tasks` | `{tasks: TaskEntry[], subagents: SubagentEntry[]}` | Task state updates |
| `on_cost_update` | `{cost: string, tokens_in: u32, tokens_out: u32}` | Cost/tokens update |

## Inbound Requests (Python → Rust, id set — Rust must respond)

| Method | Params | Response |
|---|---|---|
| `approval` | `{tool: string, args: string}` | `ApprovalResult {approved: bool, session_approve?: bool}` |
| `ask_user` | `{question: string, options: string[], allow_text: bool}` | `AskUserResult {answer: string}` |

## Outbound Requests (Rust → Python, id set — Python responds)

| Method | Params | Response |
|---|---|---|
| `chat` | `{message: string, session_id?: string}` | ack |
| `cancel` | `{}` | ack |
| `command` | `{cmd: string}` | ack |
| `session.new` | `{title?: string}` | — |
| `session.list` | `{}` | `SessionListResult {sessions: SessionInfo[]}` |
| `session.resume` | `{session_id: string}` | ack |
| `session.fork` | `{session_id?: string}` | `ForkSessionResult {new_session_id: string}` |
| `config.set` | `{key: string, value: string}` | — |
| `steer` | `{message: string}` | ack |

## Request-Response Correlation

Rust maintains a `pending_requests: HashMap<i64, PendingRequest>` in AppState:

1. Increment `next_request_id`
2. Insert `(id, PendingRequest { method, sent_at: Instant::now() })`
3. Send `RPCMessage { jsonrpc: "2.0", id: Some(id), method: Some(method), params: ... }`

When a response arrives (id set, method absent):
1. Look up `id` in `pending_requests`
2. Remove the pending entry
3. Dispatch result to the appropriate handler

Stale requests (no response within 30s): log warning, remove from pending, surface `error_banner`.

## Struct Definitions

See `autocode/rtui/src/rpc/protocol.rs` for the complete serde struct definitions.
