# Tier 2 — Codex-style App Server Protocol

**Goal:** decouple the agent harness from the TUI so a future Tauri/Electron desktop client, web client, or IDE extension can reuse the backend without re-implementing conversation state.

**Total cost:** ~3 weeks engineering, ~1100 LOC across Rust + Python.

**Why this is the highest-leverage architectural move:** today, AutoCode's RPC has 44 ad-hoc structs (`TokenParams`, `ToolCallParams`, `ApprovalRequestParams`, etc.) tightly coupled to the Rust TUI. Every new client surface would have to reverse-engineer the wire format. Codex moved from this exact mess to Item/Turn/Thread in early 2026 and now powers their CLI, VS Code extension, web app, macOS desktop app, JetBrains and Xcode plugins from one server. We follow the same playbook.

---

## Tier 2.1 — Item / Turn / Thread primitive refactor

### Files touched

- `rtui/src/rpc/protocol.rs` — replace 44 structs with 3 primitives + their wrappers (~700 LOC delta)
- `rtui/src/rpc/codec.rs` — adjust serialization (~30 LOC)
- `rtui/src/state/reducer.rs` — handle new Item/Turn/Thread events (~200 LOC)
- `src/autocode/backend/server.py` — add thread/turn/item dispatch + emit (~250 LOC)
- `src/autocode/backend/dispatcher.py` — route new method names
- `docs/reference/rpc-schema-v2.md` — NEW canonical schema doc
- `tests/rpc-conformance/` — update fixtures

### The three primitives — exact specs

#### `Item` — atomic input/output unit

```rust
// rtui/src/rpc/protocol.rs

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ItemKind {
    /// User text input (verbatim what the user typed)
    UserMessage { text: String },

    /// Agent text output (model's response, streamed)
    AgentMessage { text: String },

    /// Tool execution (started → optional progress → completed)
    ToolExecution {
        tool_name: String,
        args: serde_json::Value,
        result: Option<String>,
        status: ToolStatus,
    },

    /// Approval request (server-initiated, blocks turn until client responds)
    Approval {
        tool_name: String,
        args: serde_json::Value,
        risk_level: String,
    },

    /// File diff (multi-file edit results)
    Diff {
        files: Vec<DiffFileEntry>,
    },

    /// Thinking / reasoning trace (for thinking models)
    Reasoning { text: String },

    /// Subagent delegation (task decomposed and farmed out)
    SubagentDelegation {
        subagent_id: String,
        task: String,
        status: SubagentStatus,
    },

    /// Plan/todo update (todo_write tool result)
    PlanUpdate {
        todos: Vec<TodoEntry>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    pub id: String,                // ULID, server-generated
    pub turn_id: String,
    pub thread_id: String,
    pub kind: ItemKind,
    pub status: ItemStatus,        // pending | streaming | completed | failed
    pub created_at: String,        // ISO 8601 UTC
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ItemStatus {
    Pending,
    Streaming,
    Completed,
    Failed,
    Cancelled,
}
```

#### Item lifecycle notifications

The server emits these in order:

```
item/started        — { item_id, turn_id, thread_id, kind, status: "pending" }
item/<kind>/delta   — { item_id, delta: "..." }   (only for streaming items)
item/completed      — { item_id, status: "completed" | "failed", result?, completed_at }
```

Specific delta channels by item kind:
- `item/agentMessage/delta` — `{ delta: string }` for streamed text
- `item/reasoning/delta` — `{ delta: string }` for thinking tokens
- `item/toolExecution/progress` — `{ progress: string }` for long-running tools

#### `Turn` — one user request + all agent work

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Turn {
    pub id: String,                // ULID
    pub thread_id: String,
    pub status: TurnStatus,
    pub started_at: String,
    pub completed_at: Option<String>,
    pub items: Vec<String>,        // ordered list of item IDs
    pub interrupted: bool,
    pub interruption_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TurnStatus {
    Pending,        // turn/start called, not yet running
    Running,        // turn/started emitted
    AwaitingApproval,
    Completed,
    Failed,
    Cancelled,
}
```

#### `Thread` — durable conversation container

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Thread {
    pub id: String,                // ULID
    pub title: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub model_provider: String,
    pub model: String,
    pub cwd: String,
    pub permission_profile: String,
    pub ephemeral: bool,
    pub path: Option<String>,      // null for ephemeral
    pub git_info: Option<GitInfo>,
    pub turn_count: u64,
    pub archived: bool,
}
```

### Method namespace

Replace current ad-hoc methods with the standardized namespace:

| Old method | New method | Notes |
|---|---|---|
| `chat` | `turn/start` | Returns turn obj immediately, emits `turn/started` |
| `chat/cancel` | `turn/interrupt` | |
| (new) | `turn/steer` | Append user input to in-flight turn without new turn |
| `session_new` | `thread/start` | |
| `session_resume` | `thread/resume` | |
| (new) | `thread/fork` | Branch with copied history; `ephemeral: true` for in-mem |
| `session_list` | `thread/list` | Cursor pagination, filters |
| (new) | `thread/read` | Read without resuming; `includeTurns: true` for full history |
| (new) | `thread/turns/list` | Page through stored turn history |
| (new) | `thread/loaded/list` | List threads currently in-memory |
| (new) | `thread/name/set` | Update title, emits `thread/name/updated` |
| (new) | `thread/metadata/update` | Patch SQLite metadata |
| (new) | `thread/archive` | Soft-delete, emits `thread/archived` |
| (new) | `thread/unarchive` | Restore, emits `thread/unarchived` |

Keep these unchanged for backward compat:
- `command_list`, `command/<name>`
- `provider_list`, `model_list`
- `task_list`, `subagent_list`, `subagent_cancel`
- `plan_status`, `plan_set`, `plan_export`
- `config_get`, `config_set`
- `memory_list`
- `checkpoint_list`, `checkpoint_restore`

### Initialize handshake (NEW — required for transport)

Codex requires a single `initialize` request before any other method. Add this:

**Client → Server:**
```json
{
  "id": 1,
  "method": "initialize",
  "params": {
    "client_name": "autocode-rtui",
    "client_version": "0.2.0",
    "protocol_version": "2.0",
    "capabilities": {
      "supports_approval_response": true,
      "supports_streaming_deltas": true,
      "supports_diff_artifact": true
    }
  }
}
```

**Server → Client (response):**
```json
{
  "id": 1,
  "result": {
    "server_name": "autocode-backend",
    "server_version": "0.4.0",
    "protocol_version": "2.0",
    "capabilities": {
      "supports_thread_fork": true,
      "supports_ephemeral_threads": true,
      "supports_turn_steer": true,
      "max_concurrent_threads": 4,
      "supported_item_kinds": [
        "user_message", "agent_message", "tool_execution",
        "approval", "diff", "reasoning", "subagent_delegation",
        "plan_update"
      ]
    },
    "providers": [...],   // initial list of providers
    "models": {...}       // map of provider -> models
  }
}
```

**Client → Server (notification):**
```json
{ "method": "initialized" }
```

After this, any other method may be called. Calling other methods before `initialized` returns error `-32002 "Server not yet initialized"`.

### Turn flow — the canonical sequence

```
[Client]                                [Server]
   |                                       |
   |--- turn/start(thread_id, input) ----->|
   |                                       | (validate, allocate turn_id, persist)
   |<--- response: { turn: Turn { ... } } -|
   |                                       |
   |<--- notif: turn/started(turn_id) -----|
   |                                       |
   |<--- notif: item/started(user_message) | (echo user input as item)
   |<--- notif: item/completed             |
   |                                       |
   |<--- notif: item/started(reasoning) ---| (if thinking model)
   |<--- notif: item/reasoning/delta ------|
   |<--- notif: item/reasoning/delta ------|
   |<--- notif: item/completed             |
   |                                       |
   |<--- notif: item/started(agent_message)|
   |<--- notif: item/agentMessage/delta ---|  (streamed)
   |<--- notif: item/agentMessage/delta ---|
   |<--- notif: item/completed             |
   |                                       |
   |<--- notif: item/started(tool_exec) ---|  (model called a tool)
   |<--- request: approval { ... } -------←|  (server-initiated)
   |--- response: { decision: "allow" } -->|  (client responds)
   |<--- notif: item/toolExecution/progress|
   |<--- notif: item/completed(tool_exec)  |
   |                                       |
   |<--- notif: item/started(agent_message)|
   |<--- notif: item/agentMessage/delta ---|
   |<--- notif: item/completed             |
   |                                       |
   |<--- notif: turn/completed -----------|
```

### Thread persistence

Use existing SQLite session store. Add columns:

```sql
ALTER TABLE sessions ADD COLUMN ephemeral INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN archived INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN permission_profile TEXT DEFAULT 'default';
ALTER TABLE sessions ADD COLUMN git_info_json TEXT;
ALTER TABLE sessions ADD COLUMN turn_count INTEGER DEFAULT 0;

-- Items table (new)
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (turn_id) REFERENCES turns(id),
    FOREIGN KEY (thread_id) REFERENCES sessions(id)
);
CREATE INDEX idx_items_turn ON items(turn_id);
CREATE INDEX idx_items_thread ON items(thread_id);

-- Turns table (new)
CREATE TABLE turns (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    interrupted INTEGER DEFAULT 0,
    interruption_reason TEXT,
    FOREIGN KEY (thread_id) REFERENCES sessions(id)
);
CREATE INDEX idx_turns_thread ON turns(thread_id);
```

Ephemeral threads bypass these tables entirely — kept in-memory only.

### Migration mapping

For backward compatibility, the old methods get aliases. In `dispatcher.py`:

```python
LEGACY_METHOD_ALIASES = {
    "chat": "turn/start",  # but with arg adaptation
    "chat/cancel": "turn/interrupt",
    "session_new": "thread/start",
    "session_resume": "thread/resume",
    "session_list": "thread/list",
}

async def dispatch(self, method: str, params: dict, request_id: int):
    # Check legacy alias
    if method in LEGACY_METHOD_ALIASES:
        method = LEGACY_METHOD_ALIASES[method]
        params = self._adapt_legacy_params(method, params)

    # Then dispatch normally
    handler = self._handlers.get(method)
    ...
```

The aliases stay for one minor version (0.4.x), removed in 0.5.0 with deprecation warnings emitted in 0.4.x.

### Acceptance tests

```python
async def test_initialize_handshake():
    """Other methods return -32002 before initialize."""
    r = await server.handle({"method": "thread/start", "id": 1})
    assert r["error"]["code"] == -32002

    r = await server.handle({
        "method": "initialize",
        "id": 1,
        "params": {"client_name": "test", "protocol_version": "2.0"}
    })
    assert "result" in r
    assert "capabilities" in r["result"]


async def test_turn_lifecycle_emits_correct_notifications():
    """Full turn: start → items streamed → completed."""
    notifications = []
    server.on_notification(lambda m, p: notifications.append((m, p)))

    # Initialize
    await server.handle({"method": "initialize", "id": 1, "params": {...}})
    await server.handle({"method": "initialized"})

    # Start thread
    r = await server.handle({"method": "thread/start", "id": 2, "params": {}})
    thread_id = r["result"]["thread"]["id"]

    # Start turn
    r = await server.handle({
        "method": "turn/start",
        "id": 3,
        "params": {"thread_id": thread_id, "input": "What's 2+2?"}
    })
    turn_id = r["result"]["turn"]["id"]

    # Wait for completion
    await server.wait_for_notification("turn/completed")

    # Verify notification sequence
    methods = [n[0] for n in notifications]
    assert "turn/started" in methods
    assert "item/started" in methods
    assert "item/completed" in methods
    assert methods[-1] == "turn/completed"


async def test_thread_fork_ephemeral_returns_null_path():
    parent = await server.start_thread()
    fork = await server.handle({
        "method": "thread/fork",
        "params": {"thread_id": parent["id"], "ephemeral": True}
    })
    assert fork["result"]["thread"]["ephemeral"] is True
    assert fork["result"]["thread"]["path"] is None
```

### Risks

| Risk | Mitigation |
|---|---|
| Existing clients break | Keep legacy method aliases for one minor version |
| Performance regression from extra Item events | Batch deltas: emit max 30/sec per stream |
| Item table grows unbounded | Background prune: delete items from turns > 90 days old |
| Concurrent turns on same thread | Reject with `-32004 "Thread busy: turn <id> in progress"` |

---

## Tier 2.2 — Unix socket and WebSocket transports

### Files touched

- `src/autocode/backend/transport.py` — abstract base for transports (~150 LOC)
- `src/autocode/backend/stdio_host.py` — already exists, refactor to use base
- `src/autocode/backend/unix_socket_host.py` — NEW (~120 LOC)
- `src/autocode/backend/websocket_host.py` — NEW (~200 LOC)
- `rtui/src/main.rs` — add `--connect=unix:///tmp/autocode.sock` and `--connect=ws://...` (~80 LOC)
- `src/autocode/cli.py` — add `autocode serve --listen` modes (~40 LOC)

### Why three transports

| Transport | Use case |
|---|---|
| stdio (existing) | TUI launches backend as child process — current default |
| Unix socket | Multiple clients connect to one persistent backend on same host (best for IDE plugins + TUI sharing one agent state) |
| WebSocket | Remote clients (web app, mobile, cross-machine) |

### CLI surface

```bash
# Default: stdio (TUI spawns Python backend)
autocode chat

# Unix socket — start standalone backend, connect with TUI
autocode serve --listen unix:///tmp/autocode.sock
autocode-tui --connect=unix:///tmp/autocode.sock

# WebSocket — remote/web access
autocode serve --listen ws://127.0.0.1:4500 --auth-token-file /etc/autocode/token
autocode-tui --connect=ws://localhost:4500 --auth-token=$(cat /etc/autocode/token)
```

### Auth — capability token first, JWT later

For v1, file-based shared secret:

```python
# autocode/backend/auth.py

import hmac, hashlib, secrets

def generate_capability_token() -> str:
    """Generate a 32-byte random token; URL-safe base64."""
    return secrets.token_urlsafe(32)


def verify_capability_token(provided: str, expected: str) -> bool:
    """Constant-time comparison."""
    return hmac.compare_digest(provided, expected)
```

Server reads token from file on startup. Client passes via:
- WebSocket: `Authorization: Bearer <token>` header on connect
- Unix socket: filesystem permissions (only owner can read socket file) — no token needed

For v2 (post Tier 2.2), upgrade WebSocket to signed JWT (HS256, validates exp/nbf/iss/aud). Same shared secret, but bounded lifetime.

### WebSocket bounded queue

Match Codex behavior: when message queue is full, return `-32001 "Server overloaded; retry later"`. Don't block.

```python
# src/autocode/backend/websocket_host.py

class WebSocketHost:
    MAX_QUEUE_DEPTH = 64

    async def receive_message(self, ws):
        try:
            await asyncio.wait_for(self._queue.put(msg), timeout=0.1)
        except asyncio.TimeoutError:
            await ws.send_json({
                "id": msg.get("id"),
                "error": {
                    "code": -32001,
                    "message": "Server overloaded; retry later",
                },
            })
```

Client retry policy: exponential backoff with jitter, starting at 100ms.

### Multi-client semantics

When two clients are connected to the same Unix socket / WebSocket:
- Both can read all notifications (broadcast)
- Only one client owns a turn at a time (the one that called `turn/start`)
- Other clients see read-only view of the turn
- Approval requests go to the turn owner; they have a deadline (60 sec); if deadline passes, fall back to "deny" or "ask the next connected client" (config flag)

### Acceptance tests

```python
async def test_unix_socket_round_trip():
    sock = "/tmp/autocode-test.sock"
    server = await UnixSocketHost.start(sock)

    async with UnixSocketClient(sock) as client:
        r = await client.call("initialize", {...})
        assert r["result"]["server_name"] == "autocode-backend"


async def test_websocket_overload_returns_32001():
    server = await WebSocketHost.start("ws://127.0.0.1:4500")
    # Saturate queue
    async with WebSocketClient("ws://127.0.0.1:4500") as client:
        for _ in range(100):
            client.send_no_wait({"method": "ping"})
        # Eventually one returns -32001
        responses = await client.drain(timeout=5.0)
        assert any(r.get("error", {}).get("code") == -32001 for r in responses)


async def test_capability_token_required_for_websocket():
    server = await WebSocketHost.start(
        "ws://127.0.0.1:4500",
        auth_token="secret123",
    )
    with pytest.raises(WebSocketRejectionError):
        async with WebSocketClient(
            "ws://127.0.0.1:4500", auth_token="wrong"
        ):
            pass
```

---

## Tier 2.3 — `turn/steer` for mid-flight input

### Files touched

- `src/autocode/agent/loop.py` — message queue inspection (~80 LOC)
- `rtui/src/state/reducer.rs` — handle steer key binding (~30 LOC)
- `rtui/src/ui/composer.rs` — visual indicator that steer is active

### Behavior

While a turn is running, the user can type more input and press a special keybind (suggest `Ctrl+J` since Enter sends a new turn). The new input is appended to the running turn's message queue. The model sees it on its next iteration without the turn restarting.

This matches Codex's `turn/steer`. It's the "wait, also do X" pattern users expect.

### Implementation

**Backend:**

```python
# src/autocode/agent/loop.py

class AgentLoop:
    def __init__(self, ...):
        self._steer_queue: asyncio.Queue[str] = asyncio.Queue()

    async def handle_steer(self, additional_input: str) -> None:
        """Append additional input to the in-flight turn."""
        await self._steer_queue.put(additional_input)

    async def run(self, ...):
        for iteration in range(self.MAX_ITERATIONS):
            # ... existing loop body ...

            # Drain steer queue — append as user message before next LLM call
            steer_inputs = []
            while not self._steer_queue.empty():
                steer_inputs.append(self._steer_queue.get_nowait())

            if steer_inputs:
                steer_text = "\n\n".join(
                    f"[Additional input from user mid-turn] {s}"
                    for s in steer_inputs
                )
                messages.append({"role": "user", "content": steer_text})
                # Emit item/started for the steer input as well
                await self._emit_item_started(
                    kind="user_message",
                    metadata={"steered": True},
                    text=steer_text,
                )
```

**Server dispatcher:**

```python
async def handle_turn_steer(
    self, thread_id: str, turn_id: str, input: str, request_id: int,
) -> None:
    agent_loop = self._loops.get((thread_id, turn_id))
    if not agent_loop:
        self.emit_error(
            request_id,
            code=-32005,
            message=f"No active turn {turn_id} on thread {thread_id}",
        )
        return
    await agent_loop.handle_steer(input)
    self.emit_response(request_id, {"accepted": True})
```

**TUI keybind:**

While in `Stage::Streaming`:
- `Enter` queues a new chat (existing behavior)
- `Ctrl+J` sends `turn/steer` with current composer text
- Status bar shows `· steered ↳` indicator while the steer queue is non-empty

### Acceptance test

```python
async def test_turn_steer_appends_to_running_turn():
    thread = await server.start_thread()

    # Start a long-running turn
    turn_task = asyncio.create_task(
        server.start_turn(thread.id, "Explain the entire codebase")
    )
    await asyncio.sleep(0.5)  # let it start

    # Steer mid-flight
    await server.handle({
        "method": "turn/steer",
        "params": {
            "thread_id": thread.id,
            "turn_id": (await turn_task).id,
            "input": "Actually, just explain the auth module"
        }
    })

    completed = await server.wait_for_notification("turn/completed")
    # Verify the additional input was processed (response mentions auth)
    final = await server.get_turn_final_message(thread.id, completed["turn_id"])
    assert "auth" in final.lower()
```
