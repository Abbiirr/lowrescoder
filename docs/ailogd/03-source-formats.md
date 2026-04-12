# Verified Source Formats (Ground Truth)

All formats verified against actual files on this machine. This is the canonical reference for each tool's log format.

---

## 1. Claude Code — `~/.claude/projects/**/*.jsonl` (560MB)

**Path pattern:** `~/.claude/projects/-<encoded-path>/<session-uuid>.jsonl` + `subagents/agent-*.jsonl`

### Event types

**`file-history-snapshot`** — file state snapshots (skip for logging)

**`user`** — user turns:
```json
{
  "type": "user",
  "message": {"role": "user", "content": "..."},
  "cwd": "/path/to/project",
  "sessionId": "uuid",
  "gitBranch": "main",
  "slug": "project-slug",
  "timestamp": "2026-01-15T10:30:00.000Z",
  "permissionMode": "default"
}
```

**`assistant`** — assistant turns:
```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "..."},
      {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}, "id": "toolu_..."},
      {"type": "tool_result", "tool_use_id": "toolu_...", "content": "..."},
      {"type": "thinking", "thinking": "..."}
    ]
  },
  "requestId": "req_...",
  "timestamp": "2026-01-15T10:30:05.000Z"
}
```

### Content block types within messages

| Type | Structure | Description |
|------|-----------|-------------|
| `text` | `{type: "text", text: "..."}` | Markdown response text |
| `tool_use` | `{type: "tool_use", name: "Bash"\|"Read"\|..., input: {command: ...}, id: "..."}` | Tool invocation |
| `tool_result` | `{type: "tool_result", tool_use_id: "...", content: "..."}` | Tool execution result |
| `thinking` | `{type: "thinking", thinking: "..."}` | Extended thinking block |

**Secondary:** `~/.claude/history.jsonl` — prompt-only index: `{display, timestamp, project, sessionId}`

---

## 2. Codex CLI — `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (51MB)

Each line: `{timestamp, type, payload}`

### Event types (verified)

**`session_meta`** — session initialization:
```json
{
  "timestamp": "...",
  "type": "session_meta",
  "payload": {
    "id": "sess_...",
    "timestamp": "...",
    "cwd": "/path",
    "originator": "cli",
    "cli_version": "0.1.0",
    "source": "codex",
    "model_provider": "openai",
    "base_instructions": "..."
  }
}
```

**`response_item/message`** — roles: `developer` (system), `user`, `assistant`:
```json
{
  "type": "response_item",
  "payload": {
    "type": "message",
    "role": "assistant",
    "content": [{"type": "output_text", "text": "..."}]
  }
}
```

**`response_item/function_call`** — tool calls:
```json
{
  "type": "response_item",
  "payload": {
    "type": "function_call",
    "name": "shell",
    "arguments": "{\"command\": \"ls -la\"}"
  }
}
```

**`response_item/function_call_output`** — tool results

**`response_item/reasoning`** — model reasoning/thinking

**`response_item/custom_tool_call`** / **`custom_tool_call_output`** — custom tool calls

**`event_msg/task_started`** — turn start with `model_context_window`, `collaboration_mode_kind`

**`event_msg/task_complete`** — turn end

**`event_msg/token_count`** — token usage per turn:
```json
{
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "total_usage_tokens": 15000,
    "estimated_token_count": 12000
  }
}
```

**`event_msg/user_message`** — user input text

**`event_msg/agent_message`** — agent response text

**`event_msg/agent_reasoning`** — agent reasoning text

**`turn_context`** — turn boundary context

**Secondary:** `~/.codex/log/codex-tui.log` — Rust tracing: token usage, tool call JSON payloads, timing

---

## 3. OpenCode — `~/.local/share/opencode/opencode.db` (SQLite, ~5.6MB)

### Tables

`session`, `message` (63 rows), `part` (301 rows), `project`, `permission`, `todo`, `session_share`, `control_account`

### Message `data` JSON — user

```json
{
  "role": "user",
  "time": {"created": "<ms>"},
  "summary": {"title": "...", "diffs": []},
  "agent": "plan|general|explore",
  "model": {"providerID": "opencode", "modelID": "kimi-k2.5-free|glm-5-free"},
  "tools": {"todowrite": true, "todoread": true, "task": true}
}
```

### Message `data` JSON — assistant

```json
{
  "role": "assistant",
  "time": {"created": "<ms>", "completed": "<ms>"},
  "parentID": "msg_...",
  "modelID": "kimi-k2.5-free|glm-5-free",
  "providerID": "opencode",
  "mode": "plan|general|explore",
  "agent": "plan|general|explore",
  "path": {"cwd": "...", "root": "..."},
  "cost": 0.0,
  "tokens": {"total": 0, "input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}},
  "finish": "tool-calls|stop"
}
```

### Part `data` JSON — 6 types (verified with counts)

| Part type | Count | Key fields |
|-----------|------:|------------|
| `text` | 26 | `{type, text}` |
| `step-start` | 54 | `{type, snapshot}` |
| `step-finish` | 53 | `{type, reason, snapshot, cost, tokens}` |
| `reasoning` | 54 | `{type, text, time: {start, end}}` |
| `tool` | 104 | `{type, callID, tool: "read\|bash\|task\|grep\|glob\|question", state: {status, input, output, title, metadata, time}}` |
| `patch` | 10 | `{type, hash, files: [...]}` |

**Secondary files:**
- `~/.local/state/opencode/prompt-history.jsonl` — `{input, parts, mode}`
- `~/.local/share/opencode/log/` — structured text logs
- `~/.local/share/opencode/snapshot/` — git repo snapshots per project

---

## 4. Copilot (VS Code) — `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

Multi-kind JSONL format with rich nested structures.

### Top-level entry kinds

**`kind: 0`** — Session initialization (once per file):
```json
{
  "kind": 0,
  "v": {
    "version": 3,
    "creationDate": "2026-01-15T10:00:00.000Z",
    "customTitle": "Session Title",
    "sessionId": "uuid",
    "requests": [{
      "requestId": "req_...",
      "timestamp": 1234567890,
      "agent": "copilot",
      "modelId": "copilot/auto",
      "responseId": "resp_...",
      "modelState": {"value": 1, "completedAt": 1234567891},
      "response": ["<response parts>"],
      "message": {
        "text": "user message",
        "parts": [{"range": [0, 12], "text": "user message", "kind": "text"}]
      },
      "variableData": {
        "variables": [{"value": "...", "name": "file.py", "kind": "file", "id": "..."}]
      }
    }],
    "inputState": {
      "mode": {"id": "agent", "kind": "agent"},
      "selectedModel": {
        "identifier": "copilot/auto",
        "metadata": {
          "family": "gpt-5.3-codex|claude-haiku-4.5",
          "maxInputTokens": 128000,
          "maxOutputTokens": 16384,
          "capabilities": {"vision": true, "toolCalling": true, "agentMode": true}
        }
      }
    }
  }
}
```

**`kind: 1`** — Incremental patch: `{k: ["path","to","property"], v: <value>}`

**`kind: 2`** — Array replacement: `{k: ["requests"], v: [<request objects>]}`

### Response part kinds (comprehensive enumeration)

| Kind | Description | Key fields |
|------|------------|------------|
| `thinking` | LLM reasoning blocks | `value` (text), `id`, `generatedTitle`, `metadata: {vscodeReasoningDone, stopReason}` |
| `toolInvocationSerialized` | Tool calls + results | `toolId`, `toolCallId`, `invocationMessage`, `pastTenseMessage`, `isConfirmed`, `isComplete`, `source`, `toolSpecificData`, `resultDetails` |
| `mcpServersStarting` | MCP server init | `didStartServerIds` |
| `progressTaskSerialized` | Progress updates | `content: {value}`, `progress` |
| `inlineReference` | Code symbol references | `inlineReference: {name, kind, containerName, location: {range, uri}}` |
| `reference` | File references | `reference: {$mid, fsPath, scheme}` |
| `file` | File attachments | `value: {uri}`, `name` |
| `promptFile` | Prompt template files | `reference: {uri}` |
| `textEditGroup` | Multi-file code edits | `uri`, `edits: [[{text, range}]]` |
| `codeblockUri` | Code block references | `uri`, `isEdit` |
| `undoStop` | Undo checkpoints | `id` |
| (plain text) | Markdown response text | `value`, `supportThemeIcons`, `baseUri` |

### Tool IDs observed

`vscode_fetchWebPage_internal`, `copilot_readFile`, `copilot_applyPatch`, `copilot_findFiles`, `copilot_multiReplaceString`, `run_in_terminal`, `search_subagent`, `manage_todo_list`

### `toolSpecificData` variants

- **Terminal:** `{kind: "terminal", commandLine, cwd, language, terminalCommandState: {exitCode, duration}}`
- **Todo list:** `{kind: "todoList", todoList: [{id, title, status}]}`

---

## 5. Copilot (JetBrains) — `~/.config/github-copilot/db/` (Nitrite/H2 MVStore)

Three databases:
- `chat-agent-sessions/*/copilot-agent-sessions-nitrite.db` (32KB)
- `chat-sessions/*/copilot-chat-nitrite.db` (28KB)
- `chat-edit-sessions/*/copilot-edit-sessions-nitrite.db` (32KB)

**File format:** H2 MVStore version 3 (format 3, MVStore 2.2.224). Values are **Java-serialized objects** (`ObjectOutputStream`, magic bytes `AC ED 00 05`). Contains `NitriteDocument` objects (essentially `LinkedHashMap`).

### Collections

`NtChatSession`, `NtTurn`, `NtSelectedModel`, `NtAgentSession`, `NtAgentTurn`, `NtAgentWorkingSetItem`

### Entity schema (decompiled from Copilot plugin `core.jar`)

| Entity | Key fields |
|--------|------------|
| `NtChatSession` | `id, name, projectName, user, createdAt, activeAt, modifiedAt, client, input` |
| `NtTurn` | `id, sessionId, createdAt, deletedAt, steps[], request: NtMessage, response: NtMessage, rating` |
| `NtMessage` | `user, type, status, content, references, annotations, agent, model, createdAt, errorCode, errorReason` |
| `NtAgentSession` | `id, name, user, createdAt, activeAt, modifiedAt, input, turns[], workingSet[], welcomeMessageSetting` |
| `NtAgentTurn` | `id, sessionId, createdAt, deletedAt, request: NtAgentMessage, response: NtAgentMessage, rating` |

See [09-nitrite-extractor.md](09-nitrite-extractor.md) for extraction details.

---

## 6. LLM Gateway / Ollama — `http://localhost:4000/v1` (gateway) / `http://localhost:11434` (direct)

**Gateway:** OpenAI-compatible proxy aggregating 9 free providers with automatic failover, latency-based routing, and 5-hour caching. Base URL `http://localhost:4000/v1`, docs at `http://localhost:4001/docs`.

**Model aliases:** `coding`, `default`, `fast`, `thinking`, `vision`, `tools`, `big`, `local`

### Endpoints

`/api/chat`, `/api/generate`, `/api/tags`, `/api/show`

### Request format
```json
{
  "model": "coding",
  "messages": [{"role": "user", "content": "..."}],
  "stream": true,
  "options": {"temperature": 0.7, "num_ctx": 8192}
}
```

### Response format
```json
{
  "message": {"role": "assistant", "content": "..."},
  "done": true,
  "total_duration": 5000000000,
  "eval_count": 150
}
```
