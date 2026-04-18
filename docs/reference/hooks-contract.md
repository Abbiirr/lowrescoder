# Hook Lifecycle Contract

Stable TUI v1 Milestone B.3 — Claude-Code-compatible hook runtime.

## Events

| Event | Cadence | Advisory? | Blocks tool call? |
|---|---|---|---|
| `SessionStart` | Once per agent loop lifetime | yes | no |
| `PreToolUse` | Before every tool call | no | **yes** |
| `PostToolUse` | After every tool call | yes | no |
| `Stop` | End of turn on success | yes | no |
| `StopFailure` | End of turn on failure (e.g. iteration cap) | yes | no |

## Where they fire from

Python: `autocode.agent.loop.AgentLoop`

- `run()` entry → fires `SessionStart` once per loop lifetime via
  `_fire_session_start()`
- `_execute_tool_call()` start → fires `PreToolUse` via
  `_fire_pre_tool_use(tc)`; if any hook blocks, returns the tool outcome
  as blocked without invoking the tool
- `run()` successful exit → fires `Stop` via `_fire_stop(..., failure=False)`
- `run()` iteration-cap exit → fires `StopFailure` via
  `_fire_stop(..., failure=True)`

`PostToolUse` is defined in the HookRegistry but the loop wiring is
currently deferred (non-advisory advisory only — the registry supports it
but the loop hasn't wired the after-tool fire site yet; see Slice 6 where
verification profiles will wire through PostToolUse).

Hook registry is injected via `AgentLoop(..., hook_registry=<HookRegistry>)`
or constructed by callers. Default is `None`, which makes every hook firing
a zero-cost no-op.

## Settings format

Project: `<project_root>/.claude/settings.json`
User: `<user_home>/.claude/settings.json`

Both are loaded and merged with **project entries first, user entries second**.
Example:

```json
{
  "hooks": {
    "SessionStart": [
      {"command": [".claude/hooks/log_session.sh"], "timeout_s": 2.0}
    ],
    "PreToolUse": [
      {"matcher": "Bash", "command": [".claude/hooks/pre_tool_guard.sh"]}
    ],
    "Stop": [
      {"command": [".claude/hooks/stop_gate.sh"]}
    ]
  }
}
```

See `docs/reference/claude-settings.sample.json` for a full starter config. Copy (or merge) its `hooks` section into your project or user `.claude/settings.json` to enable.

### Definition fields

| Field | Required | Default | Meaning |
|---|---|---|---|
| `command` | yes | — | `list[str]` executed via `subprocess.run` |
| `matcher` | no | `"*"` | Regex full-match against tool name for Pre/Post |
| `timeout_s` | no | `5.0` | Hard timeout in seconds; enforced via subprocess timeout |

Malformed `settings.json` (invalid JSON, wrong schema) degrades to an empty
registry without raising.

## Blocking protocol (PreToolUse)

A PreToolUse hook blocks the tool call if **either**:

1. It exits with a non-zero status code — `block_reason` = stderr or
   `"exit=<code>"`
2. Its stdout is a JSON object with `{"block": true, "reason": "..."}`

When blocked, the tool call never runs. The agent sees:

```
Blocked by PreToolUse hook: <reason>
```

as the tool outcome and can adapt its plan.

Timeouts are treated as blocking with reason `"hook timeout"`.

Once a PreToolUse hook blocks, iteration over remaining PreToolUse hooks
stops (short-circuit).

## Payload

The JSON payload is written to hook stdin. Canonical keys are added by the
runtime:

- `event`: the event name matching the enum value
- `session_id`: if provided by the caller
- `tool_name`: populated for PreToolUse / PostToolUse

Environment variables exported to every hook:

- `AUTOCODE_EVENT`
- `AUTOCODE_SESSION_ID` (if available)
- `AUTOCODE_TOOL_NAME` (if available)

Working directory is always the project root.

## Safety notes

- Hooks MUST NEVER be restarted by this runtime if the user manages an
  LLM-gateway-managed process. This runtime only `subprocess.run()`s the
  hook command configured in settings.
- Any exception thrown during hook loading or firing is caught and logged
  at DEBUG level; it never aborts the loop.
- `is_blocking(results)` helper provided for callers that want a single
  boolean summary.

## Tests

See `autocode/tests/unit/test_hooks.py` for 22 cases covering settings
loading, matcher semantics, blocking protocol, timeout enforcement, payload
I/O, env variable injection, serial execution order, and PreToolUse
short-circuit on block.
