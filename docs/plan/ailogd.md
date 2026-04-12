# Universal AI Tool Logger (`ailogd`) — Design Document

## 1. Context

AutoCode needs to observe how other AI coding tools behave — their prompts, tool definitions, conversation patterns, error recovery, and token usage — to inform harness design. A background daemon (`ailogd`) captures all request-response data from every AI coding tool on this machine, regardless of where or how they are launched. All logs go to `~/logs/`. The daemon lives as a separate module within this repo at `modules/ailogd/` with its own `uv`-managed venv.

### Locked Defaults

| Setting | Value |
|---------|-------|
| Log sink | `~/logs/` |
| Module path | `modules/ailogd/` (in repo) |
| Package manager | `uv` |
| Daemon runtime | `systemd --user` |
| Source scope | CLI + VS Code + JetBrains |
| Thinking capture | Exposed full |
| Retention | Keep forever (compressed segments) |
| Redaction | Headers only |
| P4 mode | Always-on for targets |

---

## 2. Capture Universality Model

Two-tier capture — not all tiers are universal:

| Tier | Scope | Mechanism | Universal? |
|------|-------|-----------|-----------|
| **Tier 1: Parsers** | All tools, all launches | File/DB tailers watching `~/.claude/`, `~/.codex/`, etc. | **Yes** — tools write logs regardless of how launched |
| **Tier 2: Hooks** | Claude Code only | Claude Code hook system via `~/.claude/settings.json` | **Yes** — global user settings, any project |
| **Tier 3: Deep capture** | CLI tools launched via wrappers | Ollama proxy + mitmproxy via env vars | **Conditional** — only when launched through wrapper shims |

### Making P3/P4 Automatic: Wrapper Shims + Shell Profile Injection

The install script installs wrapper shims in `~/.local/bin/` that transparently inject proxy env vars:

```bash
# ~/.local/bin/claude (wrapper shim, prepended to PATH)
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
export OLLAMA_HOST=http://localhost:11435
exec /home/bs01763/.local/share/claude/versions/current/claude "$@"

# ~/.local/bin/codex (wrapper shim)
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
exec /home/bs01763/.nvm/versions/node/v24.13.1/bin/codex "$@"
```

Additionally, inject into `~/.bashrc` / `~/.zshrc`:
```bash
# ailogd: route Ollama traffic through logging proxy
export OLLAMA_HOST=http://localhost:11435
# HTTPS_PROXY set per-tool via wrappers to avoid breaking non-AI HTTPS
```

**Fallback**: Even without wrappers, Tier 1 parsers capture everything from local logs.

---

## 3. Verified Source Formats (Ground Truth)

All formats verified against actual files on this machine.

### 3.1 Claude Code — `~/.claude/projects/**/*.jsonl` (560MB)

Session files at `~/.claude/projects/-<encoded-path>/<session-uuid>.jsonl` + `subagents/agent-*.jsonl`.

**Event types:**
- `file-history-snapshot` — file state snapshots
- `user` — user turns: `{type, message: {role, content}, cwd, sessionId, gitBranch, slug, timestamp, permissionMode}`
- `assistant` — assistant turns: `{type, message: {role, content: [{type, ...}]}, requestId, timestamp}`

**Content block types within messages:**
- `text` — `{type: "text", text: "..."}`
- `tool_use` — `{type: "tool_use", name: "Bash"|"Read"|..., input: {command: ...}, id: "..."}`
- `tool_result` — `{type: "tool_result", tool_use_id: "...", content: "..."}`
- `thinking` — `{type: "thinking", thinking: "..."}`

Secondary: `~/.claude/history.jsonl` (prompt-only index: `{display, timestamp, project, sessionId}`)

### 3.2 Codex CLI — `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (51MB)

Each line: `{timestamp, type, payload}`.

**Event types (verified):**
- `session_meta` — `{id, timestamp, cwd, originator, cli_version, source, model_provider, base_instructions}`
- `response_item/message` — roles: `developer` (system), `user`, `assistant`; content: `[{type: "input_text"|"output_text"}]`
- `response_item/function_call` — tool calls with name + arguments
- `response_item/function_call_output` — tool results
- `response_item/reasoning` — model reasoning/thinking
- `response_item/custom_tool_call` / `custom_tool_call_output` — custom tool calls
- `event_msg/task_started` — turn start with `model_context_window`, `collaboration_mode_kind`
- `event_msg/task_complete` — turn end
- `event_msg/token_count` — token usage per turn
- `event_msg/user_message` — user input text
- `event_msg/agent_message` — agent response text
- `event_msg/agent_reasoning` — agent reasoning text
- `turn_context` — turn boundary context

Secondary: `~/.codex/log/codex-tui.log` (Rust tracing: token usage, tool call JSON payloads, timing)

### 3.3 OpenCode — `~/.local/share/opencode/opencode.db` (SQLite, ~5.6MB)

**Tables:** `session`, `message` (63 rows), `part` (301 rows), `project`, `permission`, `todo`, `session_share`, `control_account`

**Message `data` JSON — user:**
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

**Message `data` JSON — assistant:**
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

**Part `data` JSON — 6 types (verified with counts):**

| Part type | Count | Key fields |
|-----------|-------|-----------|
| `text` | 26 | `{type, text}` |
| `step-start` | 54 | `{type, snapshot}` |
| `step-finish` | 53 | `{type, reason, snapshot, cost, tokens}` |
| `reasoning` | 54 | `{type, text, time: {start, end}}` |
| `tool` | 104 | `{type, callID, tool: "read\|bash\|task\|grep\|glob\|question", state: {status, input, output, title, metadata, time}}` |
| `patch` | 10 | `{type, hash, files: [...]}` |

Secondary: `~/.local/state/opencode/prompt-history.jsonl` — `{input, parts, mode}`
Logs: `~/.local/share/opencode/log/` — structured text logs
Snapshots: `~/.local/share/opencode/snapshot/` — git repo snapshots per project

### 3.4 Copilot (VS Code) — `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

Multi-kind JSONL format with rich nested structures.

**Top-level entry kinds:**

**`kind: 0`** — Session initialization (once per file):
```
v: {
  version, creationDate, customTitle, sessionId,
  requests: [{
    requestId, timestamp, agent, modelId, responseId,
    modelState: {value: 0|1, completedAt},
    response: [<response parts>],
    message: {text, parts: [{range, text, kind: "text"}]},
    variableData: {variables: [{value, name, kind: "workspace"|"file"|"terminal"|"agent", id}]},
    contentReferences, codeCitations
  }],
  inputState: {
    mode: {id: "agent", kind: "agent"},
    selectedModel: {
      identifier: "copilot/auto",
      metadata: {family: "gpt-5.3-codex"|"claude-haiku-4.5", maxInputTokens, maxOutputTokens,
                 capabilities: {vision, toolCalling, agentMode}}
    }
  }
}
```

**`kind: 1`** — Incremental patch: `{k: ["path","to","property"], v: <value>}`

**`kind: 2`** — Array replacement: `{k: ["requests"], v: [<request objects>]}`

**Response part kinds (comprehensive enumeration):**

| Kind | Description | Key fields |
|------|------------|-----------|
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

**Tool IDs observed:** `vscode_fetchWebPage_internal`, `copilot_readFile`, `copilot_applyPatch`, `copilot_findFiles`, `copilot_multiReplaceString`, `run_in_terminal`, `search_subagent`, `manage_todo_list`

**`toolSpecificData` variants:**
- Terminal: `{kind: "terminal", commandLine, cwd, language, terminalCommandState: {exitCode, duration}}`
- Todo list: `{kind: "todoList", todoList: [{id, title, status}]}`

### 3.5 Copilot (JetBrains) — `~/.config/github-copilot/db/` (Nitrite/H2 MVStore)

Three databases:
- `chat-agent-sessions/*/copilot-agent-sessions-nitrite.db` (32KB)
- `chat-sessions/*/copilot-chat-nitrite.db` (28KB)
- `chat-edit-sessions/*/copilot-edit-sessions-nitrite.db` (32KB)

**File format:** H2 MVStore version 3 (format 3, MVStore 2.2.224). Values are **Java-serialized objects** (`ObjectOutputStream`, magic bytes `AC ED 00 05`). Contains `NitriteDocument` objects (essentially `LinkedHashMap`).

**Collections (from `strings` output):** `NtChatSession`, `NtTurn`, `NtSelectedModel`, `NtAgentSession`, `NtAgentTurn`, `NtAgentWorkingSetItem`

**Entity schema (decompiled from Copilot plugin `core.jar`):**

| Entity | Key fields |
|--------|-----------|
| `NtChatSession` | `id, name, projectName, user, createdAt, activeAt, modifiedAt, client, input` |
| `NtTurn` | `id, sessionId, createdAt, deletedAt, steps[], request: NtMessage, response: NtMessage, rating` |
| `NtMessage` | `user, type, status, content, references, annotations, agent, model, createdAt, errorCode, errorReason` |
| `NtAgentSession` | `id, name, user, createdAt, activeAt, modifiedAt, input, turns[], workingSet[], welcomeMessageSetting` |
| `NtAgentTurn` | `id, sessionId, createdAt, deletedAt, request: NtAgentMessage, response: NtAgentMessage, rating` |

**Extraction approach:** Java subprocess using JARs already on this machine at `/home/bs01763/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib/`:
- `nitrite-4.3.0.jar` + `nitrite-mvstore-adapter-4.3.0.jar` + `nitrite-jackson-mapper-4.3.0.jar`
- `h2-mvstore-2.2.224.jar` (must use this exact version — format 3 only)
- `jackson-core-2.18.4.1.jar` + `jackson-databind-2.18.4.jar` + `jackson-annotations-2.18.4.jar`
- `core.jar` (Copilot entity classes for deserialization)
- `kotlin-stdlib-2.0.0.jar`
- Java 25 available at `/usr/bin/java`

**Extractor:** A ~50-line Java program opens the Nitrite DB in read-only mode, iterates all collections, serializes documents via Jackson, dumps JSONL to stdout. Python calls via `subprocess.run(["java", "-cp", classpath, "NitriteExtractor", db_path])`.

**Gotchas:**
- DB is locked while IntelliJ/PyCharm is running — extractor must copy the file first or use MVStore read-only mode
- Must use h2-mvstore 2.2.224 exactly (not 2.4.x — incompatible format version)
- Entity classes from `core.jar` needed on classpath for proper deserialization

### 3.6 LLM Gateway / Ollama — `http://localhost:4000/v1` (gateway) / `http://localhost:11434` (direct Ollama)

Endpoints: `/api/chat`, `/api/generate`, `/api/tags`, `/api/show`
- Request: `{model, messages, stream, options: {temperature, num_ctx, ...}}`
- Response: `{message: {role, content}, done, total_duration, eval_count, ...}`

---

## 4. Unified Event Contract (`ailogd.v1`)

```json
{
  "schema_version": "ailogd.v1",
  "ts": "2026-02-27T16:30:00.123Z",
  "source": "claude-code|codex|opencode|copilot-vscode|copilot-jetbrains|ollama|api-https",
  "event": "session_start|session_end|user_prompt|assistant_message|reasoning_exposed|tool_call|tool_result|api_request|api_response|token_usage|error",
  "session_id": "abc-123",
  "event_id": "evt-uuid",
  "event_seq": 1,
  "data": {},
  "capture_mode": "parsed|hook|proxy_http|proxy_https",
  "redaction_applied": "headers_only|none",
  "project_root": "/path/to/project",
  "role": "user|assistant|developer|system",
  "tool_name": "Bash|Read|exec_command|copilot_readFile|...",
  "model": "claude-opus-4-6|gpt-5.3-codex|kimi-k2.5-free|glm-5-free|...",
  "provider": "anthropic|openai|ollama|openrouter|opencode",
  "token_usage": {"input": 0, "output": 0, "reasoning": 0},
  "latency_ms": 0
}
```

### Hook Event Normalization Map

| Hook Event | ailogd.v1 `event` | Notes |
|-----------|-------------------|-------|
| `UserPromptSubmit` | `user_prompt` | Extract `prompt`, `cwd` |
| `PreToolUse` | `tool_call` | Extract `tool_name`, `tool_input`, `tool_use_id` |
| `PostToolUse` | `tool_result` | Extract `tool_name`, `tool_input`, `tool_response`, `tool_use_id` |
| `PostToolUseFailure` | `error` | `data.error_context: "tool_failure"` |
| `SessionStart` | `session_start` | |
| `SessionEnd` | `session_end` | |
| `SubagentStart` | `session_start` | `data.is_subagent: true` |
| `SubagentStop` | `session_end` | `data.is_subagent: true` |

### Source-Specific Event Mapping

**Codex `type` -> ailogd.v1 `event`:**

| Codex type | Codex payload.type | ailogd.v1 `event` |
|-----------|-------------------|-------------------|
| `session_meta` | — | `session_start` |
| `response_item` | `message` (role=user) | `user_prompt` |
| `response_item` | `message` (role=assistant) | `assistant_message` |
| `response_item` | `message` (role=developer) | `assistant_message` (role=developer) |
| `response_item` | `function_call` | `tool_call` |
| `response_item` | `function_call_output` | `tool_result` |
| `response_item` | `reasoning` | `reasoning_exposed` |
| `response_item` | `custom_tool_call` | `tool_call` |
| `response_item` | `custom_tool_call_output` | `tool_result` |
| `event_msg` | `token_count` | `token_usage` |
| `event_msg` | `task_started` | `session_start` (turn-level) |
| `event_msg` | `task_complete` | `session_end` (turn-level) |
| `event_msg` | `user_message` | `user_prompt` |
| `event_msg` | `agent_message` | `assistant_message` |
| `event_msg` | `agent_reasoning` | `reasoning_exposed` |

**OpenCode part.type -> ailogd.v1 `event`:**

| Part type | ailogd.v1 `event` | Notes |
|-----------|-------------------|-------|
| `text` | `assistant_message` | |
| `reasoning` | `reasoning_exposed` | |
| `tool` | `tool_call` + `tool_result` | Single part contains both input and output |
| `step-start` | `session_start` (step-level) | |
| `step-finish` | `token_usage` | Contains cost and token breakdown |
| `patch` | `tool_result` | `tool_name: "patch"` |

**Copilot VS Code response kind -> ailogd.v1 `event`:**

| Response kind | ailogd.v1 `event` | Notes |
|-------------|-------------------|-------|
| `thinking` | `reasoning_exposed` | |
| `toolInvocationSerialized` | `tool_call` + `tool_result` | Contains both invocation and completion state |
| (plain text) | `assistant_message` | |
| `textEditGroup` | `tool_result` | `tool_name: "code_edit"` |
| `inlineReference` | (skip — metadata only) | |
| `reference` / `file` | (skip — metadata only) | |

---

## 5. Module Layout

```
modules/ailogd/
├── pyproject.toml                     <- uv project (name=ailogd, python>=3.11)
├── uv.lock
├── .python-version
├── src/
│   └── ailogd/
│       ├── __init__.py
│       ├── daemon.py                  <- main daemon entry point
│       ├── config.py                  <- config loading from config.yaml
│       ├── schema.py                  <- ailogd.v1 event dataclasses + validation
│       ├── normalize.py               <- hook/source event normalization mappers
│       ├── state.py                   <- checkpoint store (per-source strategies)
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py               <- BaseParser ABC with incremental tailing
│       │   ├── claude_code.py        <- projects/**/*.jsonl parser
│       │   ├── codex.py              <- sessions/**/*.jsonl parser
│       │   ├── opencode.py           <- SQLite (session/message/part) parser
│       │   ├── copilot_vscode.py     <- chatSessions/*.jsonl (kind:0/1/2)
│       │   └── copilot_jetbrains.py  <- Java subprocess -> Nitrite -> JSONL
│       └── capture/
│           ├── __init__.py
│           ├── ollama_proxy.py       <- HTTP reverse proxy (localhost:11435 -> Ollama)
│           └── mitm_addon.py         <- mitmproxy addon for HTTPS API domains
├── java/
│   └── NitriteExtractor.java         <- ~50-line Java program for Nitrite -> JSONL
├── hooks/
│   └── claude_hook.sh                 <- Claude Code hook (installed to ~/.local/bin/ailogd-hook)
├── wrappers/
│   ├── claude.sh                      <- wrapper shim for Claude Code CLI
│   └── codex.sh                       <- wrapper shim for Codex CLI
├── config.yaml                        <- default config (source paths, ports, domains, resolved paths)
├── install.sh                         <- one-shot installer
├── analyze.py                         <- pattern analysis CLI tool
└── tests/
    ├── fixtures/                      <- sample JSONL/DB per source format
    ├── test_parsers.py
    ├── test_schema.py
    ├── test_normalize.py
    ├── test_state.py
    ├── test_ollama_proxy.py
    ├── test_nitrite_extractor.py
    └── test_hook_latency.py

~/logs/                        <- global sink (chmod 700)
├── claude-code/
│   ├── live.jsonl             <- real-time from hooks (normalized ailogd.v1)
│   └── parsed.jsonl           <- parsed from projects/**/*.jsonl
├── codex/
│   ├── live.jsonl             <- real-time from session file watching
│   └── parsed.jsonl           <- parsed from sessions/**/*.jsonl
├── opencode/
│   ├── live.jsonl             <- real-time from DB polling
│   └── parsed.jsonl           <- parsed from opencode.db
├── copilot/
│   ├── vscode-parsed.jsonl    <- parsed from chatSessions
│   └── jetbrains-parsed.jsonl <- parsed from Nitrite via Java extractor
├── ollama/
│   └── traffic.jsonl          <- full HTTP request/response (plaintext)
├── api-traffic/
│   └── https.jsonl            <- full HTTPS payloads via mitmproxy
└── unified.jsonl              <- merged normalized stream from all sources
```

---

## 6. Daemon Design (`daemon.py`)

### 6.1 Startup
1. Ensure `~/logs/` directory structure with `chmod 700`
2. Load `config.yaml` — source paths, proxy ports, domain filters, all resolved executable paths
3. Open state DB — checkpoint store with per-source strategies
4. Validate dependencies: check resolved `mitmdump` path, check ports free, check mitmproxy CA cert
5. Compile `NitriteExtractor.java` if `.class` not present (one-time)

### 6.2 Runtime Workers (asyncio)

**1. Incremental File Tailers** (one per source type):
- Claude Code: tail `~/.claude/projects/**/*.jsonl` — track inode + byte offset per file
- Codex: tail `~/.codex/sessions/**/*.jsonl`
- Codex TUI log: tail `~/.codex/log/codex-tui.log`
- Copilot VS Code: tail `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

**2. Periodic File Discovery Scanner** (every 30s):
- Scan for new session files across all JSONL sources
- Register new files with tailers

**3. Database Pollers** (source-specific checkpoint strategies):
- **OpenCode**: poll `opencode.db` every 5s for new `message`/`part` rows
  - Checkpoint: `max(time_created)` per table — not inode/offset
  - Query: `SELECT * FROM message WHERE time_created > ? ORDER BY time_created`
  - Dedup key: `message.id` / `part.id` (stable primary keys)
  - Connection: read-only with `PRAGMA journal_mode=WAL`; retry on `SQLITE_BUSY`
- **Copilot JetBrains**: poll Nitrite DBs every 60s via Java subprocess
  - Copy DB file to temp location first (avoid lock conflicts with running IDE)
  - Run `java -cp <classpath> NitriteExtractor <temp_copy>` -> capture stdout JSONL
  - Checkpoint: `max(modifiedAt)` per collection from extracted data
  - Dedup key: `NtTurn.id` / `NtAgentTurn.id`

**4. Ollama Reverse Proxy** (inline async):
- `httpx`-based async reverse proxy on `localhost:11435`
- Forwards to configured Ollama host (from `config.yaml`, default `localhost:4000`)
- Logs full request body + full response body to `~/logs/ollama/traffic.jsonl`
- Non-blocking — streams responses through while capturing

**5. mitmproxy Subprocess** (always-on targeted):
- Runs resolved `mitmdump` path: `{venv}/bin/mitmdump -s {resolved_addon_path} --listen-port 8080 --set confdir=~/.mitmproxy`
- Addon filters to: `api.anthropic.com`, `api.openai.com`, `api.openrouter.ai`
- Logs to `~/logs/api-traffic/https.jsonl`

**6. Unified Merger**:
- Tails all per-source JSONL sinks
- Validates against `ailogd.v1` schema
- Append-only write to `~/logs/unified.jsonl`

### 6.3 Checkpoint Strategy (per-source)

| Source | Checkpoint Key | Dedup Key |
|--------|---------------|-----------|
| JSONL files (Claude, Codex, Copilot VS Code) | `inode + byte_offset` per file | `source_file + byte_offset + content_hash` |
| OpenCode SQLite | `max(time_created)` per table | `message.id` / `part.id` (row PK) |
| Copilot JetBrains Nitrite | `max(modifiedAt)` per collection | `NtTurn.id` / `NtAgentTurn.id` |
| Ollama proxy | N/A (real-time) | Request hash (method + path + body_hash) |
| mitmproxy | N/A (real-time) | Request hash |

All checkpoints persisted to `state.db` (SQLite) every 5s and on SIGTERM.

### 6.4 Retention & Archival

**Policy:** Keep forever, with compression.
- **Active logs**: `~/logs/<source>/*.jsonl` — written to actively
- **Segment rotation**: When any active log exceeds 100MB, rotate to `<name>.<ISO-timestamp>.jsonl.gz`
- **Compression worker**: Background asyncio task, runs every 60s, gzips rotated segments
- **No deletion**: All segments retained indefinitely
- **Disk usage monitoring**: `analyze.py --disk-usage` reports per-source sizes and growth rate

### 6.5 systemd Service

File: `~/.config/systemd/user/ailogd.service`
```ini
[Unit]
Description=AI Tool Request-Response Logger Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/projects/ai/lowrescoder/modules/ailogd
ExecStart=%h/projects/ai/lowrescoder/modules/ailogd/.venv/bin/python -m ailogd.daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

Setup: `cd modules/ailogd && uv sync && systemctl --user enable --now ailogd`

---

## 7. Phase Details

### 7.1 Phase 1: Log Parsers + Unified Store

**Claude Code parser** (`parsers/claude_code.py`):
- Scan `~/.claude/projects/**/*.jsonl` (glob pattern)
- For each file, read JSONL lines incrementally from last checkpoint
- Map `user` -> `user_prompt`, `assistant` with `tool_use` blocks -> `tool_call`, `tool_result` blocks -> `tool_result`, `thinking` blocks -> `reasoning_exposed`, `text` blocks -> `assistant_message`
- Extract: `sessionId`, `cwd`, `gitBranch`, `slug`, `permissionMode`, `requestId`

**Codex parser** (`parsers/codex.py`):
- Scan `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
- Map using the normalization table in Section 4
- Extract from `session_meta`: `cwd`, `cli_version`, `model_provider`, `base_instructions`
- Extract from `event_msg/token_count`: `total_usage_tokens`, `estimated_token_count`
- Pair `function_call` with subsequent `function_call_output` by matching turn order

**OpenCode parser** (`parsers/opencode.py`):
- Poll `opencode.db` with SQLite read-only WAL connection
- Join `message` -> `part` on `message_id`
- Map using the normalization table in Section 4
- Extract from message data: `role`, `agent`, `modelID`, `providerID`, `mode`, `tokens`, `cost`
- Extract from part data: tool name, input/output, reasoning text, patch files

**Copilot VS Code parser** (`parsers/copilot_vscode.py`):
- Scan `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`
- Process `kind:0` for initial session state + `v.requests[]` canonical data
- Process `kind:1` patches for incremental updates
- Process `kind:2` response arrays for tool invocations + thinking
- Extract from `toolInvocationSerialized`: `toolId`, `toolCallId`, `toolSpecificData` (terminal commands, todo lists)
- Extract from `thinking`: reasoning text, `generatedTitle`
- Extract from `inputState.selectedModel`: model family, capabilities
- Skip metadata-only kinds: `mcpServersStarting`, `undoStop`, `reference`, `inlineReference`

**Copilot JetBrains parser** (`parsers/copilot_jetbrains.py`):
- Call Java subprocess: `java -cp <classpath> NitriteExtractor <db_copy_path>`
- Classpath uses JARs from `/home/bs01763/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib/`
- Extractor opens DB read-only, iterates `NtChatSession` + `NtTurn` + `NtAgentSession` + `NtAgentTurn`
- Dumps each document as JSONL line to stdout
- Python parser reads stdout, maps `NtTurn.request/response` -> `user_prompt`/`assistant_message`, `NtMessage.content` -> message text

### 7.2 Phase 2: Claude Code Hooks (Real-Time)

**Hook installation (global-safe):**
- Script installed to `~/.local/bin/ailogd-hook` (absolute path, works from any project)
- `install.sh` resolves venv Python path and embeds as absolute in script
- Registered in `~/.claude/settings.json` (user scope)

**Hook script** (`~/.local/bin/ailogd-hook`):
```bash
#!/bin/bash
AILOGD_PYTHON="/home/bs01763/projects/ai/lowrescoder/modules/ailogd/.venv/bin/python"
exec "$AILOGD_PYTHON" -c "
import sys, json, uuid, datetime, os
NORM = {
    'UserPromptSubmit': 'user_prompt',
    'PreToolUse': 'tool_call',
    'PostToolUse': 'tool_result',
    'PostToolUseFailure': 'error',
    'SessionStart': 'session_start',
    'SessionEnd': 'session_end',
    'SubagentStart': 'session_start',
    'SubagentStop': 'session_end',
}
inp = json.load(sys.stdin)
hook_name = inp.get('hook_event_name', 'unknown')
evt = {
    'schema_version': 'ailogd.v1',
    'ts': datetime.datetime.utcnow().isoformat() + 'Z',
    'source': 'claude-code',
    'event': NORM.get(hook_name, hook_name),
    'session_id': inp.get('session_id', ''),
    'event_id': str(uuid.uuid4()),
    'capture_mode': 'hook',
    'redaction_applied': 'none',
    'tool_name': inp.get('tool_name'),
    'data': {
        'hook_event_name': hook_name,
        'tool_input': inp.get('tool_input'),
        'tool_response': inp.get('tool_response'),
        'tool_use_id': inp.get('tool_use_id'),
        'prompt': inp.get('prompt'),
        'cwd': inp.get('cwd'),
        'is_subagent': hook_name in ('SubagentStart', 'SubagentStop'),
    }
}
with open(os.path.expanduser('~/logs/claude-code/live.jsonl'), 'a') as f:
    f.write(json.dumps(evt) + '\n')
" < /dev/stdin 2>/dev/null
exit 0
```

**Settings.json** (`~/.claude/settings.json`, user scope):
```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "PreToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "PostToolUseFailure": [{"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "SessionStart": [{"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "SubagentStart": [{"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}]
  }
}
```

### 7.3 Phase 3: Ollama Reverse Proxy

File: `modules/ailogd/capture/ollama_proxy.py`

- Async `httpx`-based reverse proxy on `localhost:11435`
- Forwards to configured Ollama host (default `localhost:4000`)
- Captures full request JSON (model, messages, system, options) + full response JSON
- Output: `~/logs/ollama/traffic.jsonl`
- Automatically used via `OLLAMA_HOST` injected by wrappers and `~/.bashrc`

### 7.4 Phase 4: mitmproxy HTTPS Capture

File: `modules/ailogd/capture/mitm_addon.py`

- Addon filters requests to AI API domains: `api.anthropic.com`, `api.openai.com`, `api.openrouter.ai`
- Logs: URL, method, headers (auth redacted), full body -> `~/logs/api-traffic/https.jsonl`
- Executable resolution: `install.sh` resolves `{venv}/bin/mitmdump` at install time, stores in `config.yaml`
- Wrapper shims in `~/.local/bin/` set `HTTPS_PROXY=http://localhost:8080` for CLI launches
- IDE extensions cannot be proxied (known limitation) — parser capture covers those
- CA cert: `cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates`

### 7.5 NitriteExtractor.java

File: `modules/ailogd/java/NitriteExtractor.java`

```java
// ~50 lines: open Nitrite DB read-only, iterate collections, dump as JSONL
// Classpath: nitrite-4.3.0.jar, nitrite-mvstore-adapter-4.3.0.jar,
//            nitrite-jackson-mapper-4.3.0.jar, h2-mvstore-2.2.224.jar,
//            jackson-core-2.18.4.1.jar, jackson-databind-2.18.4.jar,
//            jackson-annotations-2.18.4.jar, core.jar, kotlin-stdlib-2.0.0.jar
// All JARs from: ~/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib/
// Compile: javac -cp <classpath> NitriteExtractor.java
// Run: java -cp <classpath>:. NitriteExtractor <db_path>
// Output: one JSON line per document to stdout
```

---

## 8. Security & Privacy

- `~/logs/` mode `700` — owner-only access
- Redact **headers only**: `Authorization`, `x-api-key`, `proxy-authorization`, `cookie`, `set-cookie`
- Keep bodies/content **raw** (this is the whole point — observing prompt patterns)
- Local-only storage, no uploads
- Installer prints sensitive-data warning and mitigation guidance
- Nitrite DB copies are temp files, deleted after extraction

---

## 9. Install Flow (`install.sh`)

1. `mkdir -p ~/logs/{claude-code,codex,opencode,copilot,ollama,api-traffic} && chmod 700 ~/logs`
2. `cd modules/ailogd && uv sync` — creates `.venv/` and installs all deps
3. **Resolve all executable paths** and write to `config.yaml`:
   - `python`: `modules/ailogd/.venv/bin/python`
   - `mitmdump`: `modules/ailogd/.venv/bin/mitmdump`
   - `java`: `/usr/bin/java`
   - `claude_real`: path to real Claude Code binary (before wrapper)
   - `codex_real`: path to real Codex binary (before wrapper)
   - `jetbrains_lib`: `~/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib/`
4. Compile `NitriteExtractor.java` with resolved classpath
5. Install hook: copy `hooks/claude_hook.sh` -> `~/.local/bin/ailogd-hook` (with resolved Python path embedded)
6. Merge hook config into `~/.claude/settings.json` (JSON merge, preserve existing settings)
7. Install **wrapper shims**: `wrappers/claude.sh` -> `~/.local/bin/claude`, `wrappers/codex.sh` -> `~/.local/bin/codex` (with resolved real binary paths)
8. Inject `OLLAMA_HOST=http://localhost:11435` into `~/.bashrc` (idempotent, guarded by `# ailogd:` marker)
9. Install `~/.config/systemd/user/ailogd.service` -> enable + start
10. If mitmproxy available: run `mitmdump` once to generate CA cert, print cert install instructions
11. Run doctor checks: log dirs writable, daemon running, hooks installed, ports free, wrappers resolve correctly, Java + JARs present

---

## 10. Test Plan

| # | Test | Validates |
|---|------|-----------|
| 1 | Parser fixture tests — known JSONL snippets -> normalized output | Each parser's format handling |
| 2 | Claude historical replay — parse real `~/.claude/projects/` | Claude backfill including thinking + tool_use + tool_result |
| 3 | Codex session replay — parse real `~/.codex/sessions/` | function_call/reasoning extraction + token_count |
| 4 | OpenCode DB query — read real `opencode.db` | session/message/part extraction with `time_created` checkpoint |
| 5 | Copilot VS Code — parse `kind:0` requests[], `kind:2` toolInvocationSerialized + thinking | Full Copilot parser |
| 6 | Copilot JetBrains — run NitriteExtractor on real DB -> verify JSONL output | Java subprocess + entity deserialization |
| 7 | Claude hook normalization — `UserPromptSubmit`->`user_prompt`, `PreToolUse`->`tool_call`, etc. | Schema compliance |
| 8 | Claude hook latency — time 100 invocations -> median < 100ms | Hook performance |
| 9 | Ollama proxy e2e — `curl` through proxy -> `traffic.jsonl` has full payload | Ollama capture |
| 10 | mitmproxy domain filter — filtered + non-filtered requests -> only filtered logged | HTTPS capture |
| 11 | Header redaction — Authorization/x-api-key -> `[REDACTED]` in api-traffic only | Privacy |
| 12 | Daemon restart + dedup — stop, restart -> no duplicate events | Reliability per source type |
| 13 | DB checkpoint recovery — restart after OpenCode inserts -> no duplicates, no missed rows | DB-specific checkpoint |
| 14 | Nitrite checkpoint — restart after JetBrains session -> no duplicates | Nitrite-specific checkpoint |
| 15 | Unified schema — validate every event in unified.jsonl against ailogd.v1 | Contract |
| 16 | Wrapper shim — `~/.local/bin/claude` sets proxy and delegates to real binary | P3/P4 universality |
| 17 | Rotation + gzip — write >100MB -> segment rotated and compressed | Retention |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| GUI clients/IDEs bypass proxy env | Tier 1 parsers always on as universal fallback; wrapper shims cover CLI launches |
| TLS pinning blocks mitmproxy for some tools | Rely on parser capture; log warning and continue |
| Keep-forever disk growth | Gzip rotated segments (100MB trigger); `analyze.py --disk-usage` reports growth |
| Vendor format drift breaks parsers | Tolerant parsers (skip unknown fields); versioned test fixtures per source |
| Hook script stale after venv rebuild | `install.sh` re-resolves paths; systemd `ExecStartPre` could run path check |
| Wrapper shim PATH ordering | Install to `~/.local/bin/` (typically first in `$PATH`); `install.sh` verifies |
| OpenCode DB locked during writes | `PRAGMA journal_mode=WAL` read connection; retry on `SQLITE_BUSY` |
| Nitrite DB locked by running IDE | Copy to temp file before extraction; use MVStore read-only mode |
| JetBrains JARs move on IDE upgrade | `config.yaml` stores resolved path; `install.sh --doctor` detects and warns |
| h2-mvstore version mismatch | Pin to 2.2.224 exactly; verify at install time by checking DB file header |
