# Phase 1: Log Parsers + Unified Store

Phase 1 implements Tier 1 capture — universal file/DB tailers that work regardless of how tools are launched.

---

## Parser Architecture

All parsers inherit from `BaseParser` ABC:

```python
# parsers/base.py
class BaseParser(ABC):
    """Base class for incremental log parsers with checkpoint support."""

    @abstractmethod
    async def discover_sources(self) -> list[SourceFile]:
        """Find all log files/databases for this source."""

    @abstractmethod
    async def parse_incremental(self, source: SourceFile, checkpoint: Checkpoint) -> AsyncIterator[AilogdEvent]:
        """Parse new events since last checkpoint."""

    @abstractmethod
    def checkpoint_strategy(self) -> CheckpointStrategy:
        """Return the checkpoint strategy for this source type."""
```

Two checkpoint strategies exist:

| Strategy | Used by | Checkpoint key | Dedup key |
|----------|---------|---------------|-----------|
| **File-based** | Claude Code, Codex, Copilot VS Code | `inode + byte_offset` per file | `source_file + byte_offset + content_hash` |
| **DB-based** | OpenCode, Copilot JetBrains | `max(timestamp)` per table/collection | Row PK (`message.id`, `NtTurn.id`) |

---

## Parser 1: Claude Code (`parsers/claude_code.py`)

**Source:** `~/.claude/projects/**/*.jsonl` (glob pattern)

### Implementation Details

1. Scan `~/.claude/projects/` recursively for `*.jsonl` files
2. Include `subagents/agent-*.jsonl` files
3. For each file, read JSONL lines incrementally from last checkpoint (inode + byte offset)
4. Parse each line as JSON, dispatch on `type` field

### Mapping Logic

```python
def normalize(line: dict) -> list[AilogdEvent]:
    events = []
    if line["type"] == "user":
        events.append(AilogdEvent(
            event="user_prompt",
            session_id=line["sessionId"],
            role="user",
            data={
                "prompt": line["message"]["content"],
                "cwd": line.get("cwd"),
                "git_branch": line.get("gitBranch"),
                "permission_mode": line.get("permissionMode"),
            },
            project_root=line.get("cwd"),
        ))
    elif line["type"] == "assistant":
        for block in line["message"]["content"]:
            if block["type"] == "text":
                events.append(AilogdEvent(event="assistant_message", ...))
            elif block["type"] == "tool_use":
                events.append(AilogdEvent(
                    event="tool_call",
                    tool_name=block["name"],
                    data={"tool_input": block["input"], "tool_use_id": block["id"]},
                ))
            elif block["type"] == "tool_result":
                events.append(AilogdEvent(
                    event="tool_result",
                    data={"tool_use_id": block["tool_use_id"], "tool_response": block["content"]},
                ))
            elif block["type"] == "thinking":
                events.append(AilogdEvent(
                    event="reasoning_exposed",
                    data={"thinking": block["thinking"]},
                ))
    # Skip "file-history-snapshot" events
    return events
```

### Fields Extracted

- `sessionId` → `session_id`
- `cwd` → `project_root`
- `gitBranch` → `data.git_branch`
- `slug` → `data.slug`
- `permissionMode` → `data.permission_mode`
- `requestId` → `data.request_id`
- `timestamp` → `ts`

### Caveats

- Files can be very large (560MB total). Must use incremental reading with byte offset tracking.
- Subagent files are in `subagents/` subdirectory with `agent-*.jsonl` naming.
- `file-history-snapshot` events should be skipped (not useful for logging purposes).
- Content blocks within assistant messages are an array — must iterate and handle each type.

---

## Parser 2: Codex CLI (`parsers/codex.py`)

**Source:** `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`

### Implementation Details

1. Scan `~/.codex/sessions/` recursively for `rollout-*.jsonl` files
2. Read incrementally from last checkpoint
3. Each line is `{timestamp, type, payload}` — dispatch on `type` + `payload.type`

### Mapping Logic

Uses the normalization table from [02-schema.md](02-schema.md). Key conversions:

- `session_meta` → `session_start`: extract `cwd`, `cli_version`, `model_provider`, `base_instructions`
- `response_item/function_call` → `tool_call`: extract `name`, `arguments`
- `response_item/function_call_output` → `tool_result`: pair with preceding `function_call` by turn order
- `event_msg/token_count` → `token_usage`: extract `total_usage_tokens`, `estimated_token_count`

### Tool Call Pairing

Codex separates `function_call` and `function_call_output` into distinct lines. They must be paired by turn order (not by ID — Codex doesn't provide explicit pairing IDs).

```python
# Track pending tool calls in order
pending_calls = []

for line in lines:
    if line["type"] == "response_item" and line["payload"]["type"] == "function_call":
        pending_calls.append(line)
    elif line["type"] == "response_item" and line["payload"]["type"] == "function_call_output":
        if pending_calls:
            call = pending_calls.pop(0)
            # Emit paired tool_call + tool_result
```

### Caveats

- Date-based directory structure (`YYYY/MM/DD/`) — scanner must handle date directories
- `response_item` is overloaded — must sub-dispatch on `payload.type`
- `developer` role messages are system prompts, not user messages
- Secondary log `~/.codex/log/codex-tui.log` is Rust tracing format (not JSONL) — useful for token timing but harder to parse

---

## Parser 3: OpenCode (`parsers/opencode.py`)

**Source:** `~/.local/share/opencode/opencode.db` (SQLite)

### Implementation Details

1. Open SQLite connection with `PRAGMA journal_mode=WAL` (read-only)
2. Query `message` table for new rows: `SELECT * FROM message WHERE time_created > ? ORDER BY time_created`
3. For each message, query related parts: `SELECT * FROM part WHERE message_id = ? ORDER BY id`
4. Normalize each part based on its `type` field

### Checkpoint Strategy

- **Key:** `max(time_created)` per table
- **NOT** inode/offset (this is a database, not a file)
- **Dedup:** `message.id` / `part.id` (stable primary keys)

### Mapping Logic

Message-level:
- User messages → `user_prompt` (extract `role`, `agent`, `model`, `tools`)
- Assistant messages → container for parts (extract `modelID`, `providerID`, `mode`, `tokens`, `cost`)

Part-level (see normalization table in [02-schema.md](02-schema.md)):
- `text` → `assistant_message`
- `reasoning` → `reasoning_exposed` (with `time.start`, `time.end`)
- `tool` → `tool_call` + `tool_result` (single part contains both input and output via `state.input` and `state.output`)
- `step-finish` → `token_usage` (contains cost and token breakdown)
- `patch` → `tool_result` with `tool_name: "patch"` and `files` list

### Caveats

- **DB locking:** OpenCode may be writing while we read. Use WAL mode and retry on `SQLITE_BUSY`.
- **Connection:** Must be read-only. Never write to this database.
- **Polling interval:** Every 5 seconds (not file watching — SQLite doesn't support inotify).
- **Part types are comprehensive:** 6 types verified with counts. The `tool` part embeds both call and result — unlike Codex which separates them.
- **Models observed:** `kimi-k2.5-free`, `glm-5-free` (free model providers)

---

## Parser 4: Copilot VS Code (`parsers/copilot_vscode.py`)

**Source:** `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

### Implementation Details

1. Scan workspace storage directories for `chatSessions/*.jsonl`
2. Process `kind:0` entries first for initial session state
3. Apply `kind:1` patches for incremental property updates
4. Process `kind:2` response arrays for tool invocations + thinking

### Multi-Kind Processing

The Copilot VS Code format is the most complex — it uses an incremental patch system:

**`kind: 0`** — Full session state. Process `v.requests[]` to get all request/response pairs. Each request has:
- `message.text` → user prompt
- `response[]` → array of response parts (see response part mapping in [02-schema.md](02-schema.md))
- `variableData.variables[]` → attached context (files, terminal, workspace)
- `modelState.completedAt` → completion timestamp
- `modelId` → model identifier

**`kind: 1`** — Incremental patch. `k` is a key path array, `v` is the new value. Example:
```json
{"kind": 1, "k": ["requests", 0, "response", 5], "v": {"kind": "thinking", "value": "..."}}
```
Must apply patches in order to reconstruct current state.

**`kind: 2`** — Array replacement. Replaces entire arrays at the specified key path.

### Tool Extraction from `toolInvocationSerialized`

```python
def extract_tool_events(part: dict) -> list[AilogdEvent]:
    events = []
    tool_id = part.get("toolId")  # e.g., "run_in_terminal", "copilot_readFile"

    # Tool call event
    events.append(AilogdEvent(
        event="tool_call",
        tool_name=tool_id,
        data={
            "tool_call_id": part.get("toolCallId"),
            "invocation_message": part.get("invocationMessage"),
            "is_confirmed": part.get("isConfirmed"),
            "source": part.get("source"),
            "tool_specific_data": part.get("toolSpecificData"),
        },
    ))

    # Tool result event (if complete)
    if part.get("isComplete"):
        events.append(AilogdEvent(
            event="tool_result",
            tool_name=tool_id,
            data={
                "tool_call_id": part.get("toolCallId"),
                "past_tense_message": part.get("pastTenseMessage"),
                "result_details": part.get("resultDetails"),
            },
        ))
    return events
```

### Caveats

- **Incremental patches:** Must maintain in-memory session state and apply patches in order. Cannot just read latest lines.
- **Response part kinds are extensive:** 11+ distinct kinds. Only `thinking`, `toolInvocationSerialized`, plain text, and `textEditGroup` produce ailogd events. Others are metadata.
- **Model family extraction:** `inputState.selectedModel.metadata.family` gives the actual model (e.g., `gpt-5.3-codex`, `claude-haiku-4.5`).
- **Variable kinds:** `workspace`, `file`, `terminal`, `agent` — these represent attached context, not separate events.
- **Files can grow large** and patches are frequent — efficient incremental processing is important.

---

## Parser 5: Copilot JetBrains (`parsers/copilot_jetbrains.py`)

**Source:** `~/.config/github-copilot/db/` (Nitrite/H2 MVStore databases)

### Implementation Details

1. Copy DB file to temp location (avoid lock conflicts with running IDE)
2. Call Java subprocess: `java -cp <classpath> NitriteExtractor <temp_copy>`
3. Parse stdout JSONL lines
4. Map `NtTurn.request/response` → `user_prompt`/`assistant_message`

See [09-nitrite-extractor.md](09-nitrite-extractor.md) for full Java extractor details.

### Checkpoint Strategy

- **Key:** `max(modifiedAt)` per collection from extracted data
- **Dedup:** `NtTurn.id` / `NtAgentTurn.id`
- **Polling interval:** Every 60 seconds (slower due to Java subprocess overhead)

### Mapping Logic

```python
def normalize_turn(turn: dict, session_type: str) -> list[AilogdEvent]:
    events = []

    # Request → user_prompt
    if "request" in turn:
        req = turn["request"]
        events.append(AilogdEvent(
            event="user_prompt",
            role="user",
            data={"content": req.get("content"), "agent": req.get("agent")},
            model=req.get("model"),
        ))

    # Response → assistant_message
    if "response" in turn:
        resp = turn["response"]
        events.append(AilogdEvent(
            event="assistant_message",
            role="assistant",
            data={"content": resp.get("content"), "status": resp.get("status")},
            model=resp.get("model"),
        ))

    return events
```

### Caveats

- **DB locked while IDE running.** Must copy to temp file before extraction. Use `shutil.copy2()` then `os.unlink()` after.
- **Java subprocess overhead.** ~1-2 seconds per extraction. Hence 60s polling interval.
- **h2-mvstore 2.2.224 exactly.** Version 2.4.x uses format version 4 and cannot read format 3 files.
- **Entity classes from `core.jar` needed** on classpath for proper NitriteDocument deserialization.
- **Small databases** (~92KB total across 3 files). Data volume is low compared to other sources.

---

## Unified Merger

The merger tails all per-source JSONL sinks and writes to `~/logs/unified.jsonl`:

1. Watch all `~/logs/<source>/*.jsonl` files with inotify
2. Read new lines from each source
3. Validate each event against `ailogd.v1` schema
4. Write to `~/logs/unified.jsonl` in timestamp order (best-effort — sources may have clock skew)
5. On validation failure: log warning, skip event, continue

The unified stream is the primary query target for `analyze.py`.
