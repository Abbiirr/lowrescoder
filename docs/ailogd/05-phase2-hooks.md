# Phase 2: Claude Code Hooks (Real-Time Capture)

Phase 2 adds real-time capture from Claude Code via its hook system. This is Tier 2 — global user settings that work in any project.

---

## Claude Code Hook API Reference

### All Available Hook Events

| Event | Has Matcher | Can Block (exit 2) | Description |
|-------|-------------|--------------------:|-------------|
| `SessionStart` | Yes (startup, resume, clear, compact) | No | Session begins |
| `SessionEnd` | Yes (clear, logout, prompt_input_exit, other) | No | Session ends |
| `InstructionsLoaded` | No | No | Instructions loaded |
| `UserPromptSubmit` | No | Yes | User submits prompt |
| `PreToolUse` | Yes (tool name regex) | Yes | Before tool execution |
| `PermissionRequest` | Yes (tool name) | Yes | Permission requested |
| `PostToolUse` | Yes (tool name regex) | No | After tool execution |
| `PostToolUseFailure` | Yes (tool name) | No | Tool execution failed |
| `Stop` | No | Yes | Agent stops |
| `SubagentStart` | Yes (agent type) | No | Subagent begins |
| `SubagentStop` | Yes (agent type) | Yes | Subagent ends |
| `TeammateIdle` | No | Yes | Teammate idle |
| `TaskCompleted` | No | Yes | Task completed |
| `Notification` | Yes (notification type) | No | Notification |
| `ConfigChange` | Yes (config source) | Yes | Config changed |
| `PreCompact` / `PostCompact` | Yes (manual, auto) | No | Context compaction |
| `WorktreeCreate` / `WorktreeRemove` | No | Create: Yes | Worktree lifecycle |
| `Elicitation` / `ElicitationResult` | Yes (MCP server name) | Yes | MCP elicitation |

**ailogd uses 8 events:** `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`

### stdin JSON Schema

Every hook receives JSON on stdin with these common fields:

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse"
}
```

**Additional fields by event:**

`PreToolUse` adds:
```json
{
  "tool_name": "Bash",
  "tool_input": {"command": "npm test", "description": "Run test suite", "timeout": 120000},
  "tool_use_id": "toolu_..."
}
```

`PostToolUse` adds `tool_response` on top of `PreToolUse` fields.

`UserPromptSubmit` adds:
```json
{"prompt": "User's input text"}
```

### Exit Code Semantics

| Exit Code | Meaning | Behavior |
|-----------|---------|----------|
| `0` | Success | stdout parsed as JSON (or plain text added as context) |
| `2` | Blocking error | stderr becomes error message; action is prevented |
| Other | Non-blocking error | stderr shown in verbose mode; execution continues |

### stdout JSON Output

```json
{
  "continue": true,
  "suppressOutput": false,
  "decision": "approve",
  "reason": "Safe operation",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {"command": "modified command"},
    "additionalContext": "Extra info for Claude"
  }
}
```

**For ailogd:** We always `exit 0` with no stdout output. We are observing, not blocking.

---

## Hook Installation

### Hook Script (`~/.local/bin/ailogd-hook`)

The hook is a bash wrapper around an embedded Python one-liner. The Python path is resolved at install time and embedded as an absolute path.

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

### settings.json Configuration

Installed in `~/.claude/settings.json` (user scope — applies to all projects):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "PreToolUse": [
      {"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "PostToolUse": [
      {"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "PostToolUseFailure": [
      {"matcher": ".*", "hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "SubagentStart": [
      {"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ],
    "SubagentStop": [
      {"hooks": [{"type": "command", "command": "~/.local/bin/ailogd-hook"}]}
    ]
  }
}
```

### Installation Process

1. `install.sh` resolves the ailogd venv Python path
2. Generates `hooks/claude_hook.sh` with absolute Python path embedded
3. Copies to `~/.local/bin/ailogd-hook` and `chmod +x`
4. Reads existing `~/.claude/settings.json`
5. Merges hook config (JSON deep merge — preserves existing hooks and settings)
6. Writes back `~/.claude/settings.json`

---

## Caveats and Gotchas

### Performance

- **Latency target:** Median < 100ms per hook invocation (Test #8)
- **Startup cost:** Python interpreter startup is the main bottleneck (~50-80ms). The actual processing is trivial.
- **Mitigation:** The hook script is minimal — no imports beyond stdlib, no I/O except stdin read + file append.

### Hook Execution Model

- **Parallel execution:** When multiple hooks match the same event, they run in parallel (not sequentially).
- **Deduplication:** Identical commands are deduplicated by Claude Code.
- **Timeout:** Default is 10 minutes (600s). SessionEnd has 1.5s timeout.
- **Async option:** Setting `"async": true` runs the hook in the background — cannot control behavior but good for logging.

### Reliability

- **Hook script stale after venv rebuild:** If `uv sync` recreates the venv, the embedded Python path may break. Fix: `install.sh` re-resolves paths. Also consider `ExecStartPre` check in systemd unit.
- **File append atomicity:** Single `f.write(json.dumps(evt) + '\n')` is atomic on Linux for small writes (< PIPE_BUF = 4096 bytes). Events are always < 4KB.
- **Error suppression:** `2>/dev/null` + `exit 0` ensures the hook never blocks Claude Code, even on errors.

### What Hooks Do NOT Capture

- **Assistant response text** — hooks don't fire on assistant output (only on user input and tool use)
- **Thinking blocks** — not available via hooks (must use Tier 1 parser)
- **Token usage** — not available via hooks
- **Model selection** — not available via hooks

**This is why Phase 1 parsers are essential** — they capture everything hooks miss.

### MCP Tool Matching

MCP tools use the pattern `mcp__<server>__<tool>` for matchers. If MCP tools are in use, the `.*` matcher in `PreToolUse`/`PostToolUse` will capture them automatically.

### Environment Variables Available

- `CLAUDE_PROJECT_DIR` — available in all hook scripts
- All standard env vars from the user's shell
