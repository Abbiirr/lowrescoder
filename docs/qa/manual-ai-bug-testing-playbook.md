# Manual AI Bug-Testing Playbook

Last updated: 2026-04-11
Scope: interactive AutoCode behavior bugs that unit tests and static snapshots often miss.

## Purpose

Use this playbook when validating the shipped AI experience, especially during:

- TUI / inline UX changes
- slash-command changes
- provider / model routing changes
- tool-surface changes
- prompt / tool-schema / orchestration changes

This is **behavioral QA**, not just visual QA. The goal is to catch cases where the UI looks reasonable but the agent behaves incorrectly in-session.

## Why This Exists

Recent live screenshots exposed bugs that normal render tests did not fully catch:

- bare `/` did not expose the full command surface
- `/model` could not list models even though the local gateway was healthy
- the agent claimed a tool list was empty or missing `list_files`
- the agent lost repo-local grounding and answered as if no repo context existed
- resize behavior needed live verification, not just fixed-width snapshots

These are end-to-end interaction bugs. They require manual prompts and human judgment.

## Preflight

Before starting a manual sweep, record:

- frontend:
  - inline: `autocode chat`
  - full-screen TUI: `autocode chat --tui` or Go TUI path if specifically testing it
- profile:
  - default
  - `claude_like` when parity work is active
- cwd / repo root
- provider
- model
- terminal size:
  - narrow (`80x24`)
  - normal (`120x30` or larger)

Capture environment facts up front:

```bash
pwd
command -v autocode
autocode --version
printf 'AUTOCODE_PROFILE=%s\n' "${AUTOCODE_PROFILE:-}"
printf 'AUTOCODE_LLM_PROVIDER=%s\n' "${AUTOCODE_LLM_PROVIDER:-}"
printf 'AUTOCODE_LLM_API_BASE=%s\n' "${AUTOCODE_LLM_API_BASE:-}"
printf 'OPENROUTER_API_KEY=%s\n' "${OPENROUTER_API_KEY:+set}"
printf 'LITELLM_API_KEY=%s\n' "${LITELLM_API_KEY:+set}"
printf 'LITELLM_MASTER_KEY=%s\n' "${LITELLM_MASTER_KEY:+set}"
```

If testing a local gateway, check it directly:

```bash
curl -sS http://localhost:4000/v1/models
curl -sS -H "Authorization: Bearer $LITELLM_API_KEY" http://localhost:4000/v1/models
```

Interpretation:

- unauthenticated `401` plus authenticated `200` means the gateway is healthy and AutoCode must send auth
- `connection refused` means the gateway is actually down

## Artifact Capture

At minimum, keep:

- exact prompt text
- exact assistant output
- screenshot when layout matters
- terminal size
- provider/model shown in UI
- any slash-command output involved

### Headless PTY Resize Technique

When tmux or a GUI terminal is unavailable, you can still test live resize behavior against a real PTY:

1. Launch the target TUI in a PTY.
2. Find the attached `pts/N` with something like:

```bash
ps -ef | rg 'go run \.|autocode-tui'
```

3. Apply a real window-size change with `TIOCSWINSZ`:

```bash
python3 - <<'PY2'
import fcntl, termios, struct
path = '/dev/pts/22'  # replace with the actual pts path
with open(path, 'wb', buffering=0) as f:
    fcntl.ioctl(f.fileno(), termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
PY2
```

4. Poll the PTY and/or trigger a light redraw to verify whether the live surface recomputes width.

Notes:
- this is suitable for headless/manual QA in Codex/Claude-style PTY environments
- some redraw defects will only become visible on the next state change, which is itself a bug signal worth recording
- capture both idle-resize and during-streaming-resize behavior separately

Recommended capture methods:

- exact prompt text
- exact assistant output
- screenshot when layout matters
- terminal size
- provider/model shown in UI
- any slash-command output involved

Recommended capture methods:

```bash
script -q /tmp/autocode-manual-ai-test.typescript
autocode chat --tui
exit
```

and/or store screenshots plus a short markdown summary under:

- `docs/qa/test-results/`
- `autocode/docs/qa/test-results/`

For every manual run, start from:

- `docs/qa/manual-ai-bug-test-report-template.md`

Do not invent ad hoc result formats. Every manual sweep should end with a filled PASS/FAIL artifact based on that template.

## Severity Guide

- **Critical**
  - destructive unsafe action
  - wrong approval behavior
  - wrong repo/file modified
- **High**
  - agent loses tool grounding
  - model/provider controls are misleading or broken
  - repo-local task answered as generic chat
  - slash-command discovery is materially broken
- **Medium**
  - resize/layout breaks readability
  - status surface hides important live state
  - incorrect but recoverable workflow guidance
- **Low**
  - spacing/color/detail mismatch with parity target
  - cosmetic truncation oddities without functional impact

## Test Matrix

Run the high-value cases below for any major TUI / prompt / provider change.

### 1. Slash Command Discovery

Prompts / actions:

- type bare `/`
- type `/h`
- type `/model`
- type `/loop`
- type `/plan`
- type `/research`

Expected:

- bare `/` shows the real public command surface
- `/help` content is consistent with the slash completion surface
- aliases do not hide the primary command names

Fail if:

- bare `/` shows only a stale subset
- a documented command exists in Python but cannot be discovered in the TUI
- help and completion disagree

### 2. Provider and Model State

Actions:

- inspect startup/status line
- run `/model`
- if supported, run `/provider`
- switch model and verify the visible state updates

Expected:

- current provider and current model are visible and understandable
- model listing works against the configured backend
- gateway-backed providers do not falsely report “could not list models” when auth is available

Fail if:

- the gateway is up but AutoCode behaves as if it is down
- provider is known to the backend but not surfaced to the user
- the user cannot tell what model/provider is active

### 3. Tool Grounding and Repo-Local Behavior

Use prompts like:

- `check the files in this repo`
- `read AGENTS.md and summarize the repo rules`
- `find current_directives.md`
- `what files define slash commands here?`

Expected:

- the agent uses local tools or explicitly calls the right repo-aware path
- it does not answer like a generic remote chatbot
- it does not invent missing-tool explanations when equivalent tools are present

Fail if:

- it says tool list is empty when tools exist
- it says it cannot inspect the repo when launched inside the repo
- it hallucinates a tool contract that does not match the exposed schema

### 4. Prompt / Tool-Schema Consistency

This class is easy to miss.

Check for mismatches between:

- system prompt guidance
- environment snapshot
- actual callable tool schemas
- visible tool/status surfaces

Concrete red flags:

- prompt says “use `list_files`” but the live callable schema omits it
- UI/status claims tools are available, but model acts as if none exist
- deferred tools exist but the model is not told how to discover them

If you see this, classify at least **High**.

### 5. Resize and Re-render

Test in a live session:

1. start wide (`120+` columns)
2. resize to `80` columns while idle
3. resize during streaming
4. resize back to wide

Judge the **live render area**, not old scrollback lines.

Expected:

- prompt/footer/status recompute to the new width
- active separators/tool rows/spinners fit the new width
- no overlapping or duplicated live widgets
- narrow layout stays readable

Fail if:

- live prompt/footer remains at the old width
- new renders continue using stale width
- resize causes broken wrapping or unreadable footer/status output

### 6. Approval / Mode / Loop Behavior

Actions:

- `/mode`
- `/plan on`
- `/plan approve`
- `/review on`
- `/build on`
- `/loop 10s /model`
- `/loop list`
- `/loop cancel <id>`

Expected:

- mode changes are visible and enforced
- loop jobs are inspectable and cancellable
- read-only/review modes do not silently allow writes

Fail if:

- state changes are accepted but not reflected
- loops run but cannot be inspected/cancelled
- mode text and actual behavior diverge

### 7. Error Surface Quality

Intentionally provoke errors:

- disconnected gateway
- missing API key
- bad model alias
- unknown slash command

Expected:

- error explains the real failure
- remediation is actionable
- gateway auth failures are not mislabeled as generic connectivity failures

Fail if:

- messages are misleading
- backend is healthy but UI claims it is unreachable
- user cannot distinguish auth failure from transport failure

## Minimal Regression Prompt Set

When time is limited, run this exact set:

1. `/`
2. `/help`
3. `/model`
4. `check the files in this repo`
5. `read AGENTS.md and summarize the agent rules`
6. resize terminal narrow, then ask `what model/provider am I on?`
7. `/loop 10s /model`
8. `/loop list`
9. `/loop cancel 1`

If any of those fail materially, stop claiming parity and fix that first.

## Known Bug Classes To Watch For

### A. Prompt/Schema mismatch around `list_files`

Observed class:

- prompt guidance still mentions `list_files`
- live core schema may expose a narrower tool surface
- model then says “no `list_files` tool” or behaves like tools are missing

What to verify:

- whether `list_files` is truly callable in the active runtime
- whether the model was given the same tool view that the prompt assumes
- whether deferred-tool guidance is explicit enough

### B. Gateway auth mismatch

Observed class:

- `localhost:4000/v1/models` fails unauthenticated
- succeeds with `Authorization: Bearer $LITELLM_API_KEY`
- AutoCode may still only check `LITELLM_MASTER_KEY` or no auth at all

What to verify:

- `/model` model listing
- doctor backend check
- doctor model check

### C. Discovery mismatch between Go TUI and Python router

Observed class:

- Python router supports more commands than the Go TUI completion list
- bare `/` therefore misrepresents the actual capability surface

What to verify:

- visible completion list
- help output
- actual command dispatch

## Reporting Template

Use this template for every manual AI bug:

```md
### Manual AI Bug

- Frontend:
- Profile:
- Provider:
- Model:
- Terminal size:
- Prompt:
- Expected:
- Actual:
- Severity:
- Reproducible:
- Screenshot / artifact:
- Suspected root cause:
```

## Exit Criteria For A Manual Sweep

A manual sweep is only complete when:

- slash-command discovery is sane
- provider/model state is accurate
- repo-local prompts stay repo-local
- tool availability matches prompt/schema reality
- resize behavior is acceptable in live rendering
- artifacts are stored for the failing or newly fixed cases
