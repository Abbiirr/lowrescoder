# External Harness Adapter Command Matrix

> Date: 2026-04-02
> Goal: turn the external-harness-orchestration item from a vague architecture note into an implementation-safe adapter matrix for Codex, Claude Code, OpenCode, and Forge.

## 1. Executive Summary

AutoCode should orchestrate external harnesses through their native CLIs, not by reimplementing them and not by bypassing them with raw provider APIs.

The adapter contract needs to support, at minimum:

- launch a native session in a controlled cwd/worktree
- send prompt input the same way a human would
- resume or continue an existing session
- optionally fork a resumed session when the native harness supports that
- preserve native permission and sandbox semantics rather than flattening them
- capture transcript-first evidence: stdout, stderr, session IDs, artifacts, changed files, exports
- terminate or interrupt cleanly

The important architectural result from this pass is:

- Codex, Claude Code, OpenCode, and Forge all expose enough public surface to build real adapters.
- Their surfaces are **not equivalent**.
- AutoCode should not force them into one fake “agent loop” contract.
- Instead, AutoCode should define a canonical adapter interface and let each harness map into it with explicit capability flags.

## 2. Sources Used

Official web docs:

- OpenAI Codex:
  - https://developers.openai.com/codex
  - https://developers.openai.com/codex/cli/reference
  - https://developers.openai.com/codex/noninteractive
  - https://developers.openai.com/codex/subagents
  - https://developers.openai.com/codex/config-reference
  - https://developers.openai.com/codex/rules
- Claude Code:
  - https://code.claude.com/docs/en/headless
  - https://code.claude.com/docs/en/sub-agents
  - https://code.claude.com/docs/en/agent-teams
  - https://code.claude.com/docs/en/team
  - https://code.claude.com/docs/en/hooks
- OpenCode:
  - https://opencode.ai/docs
  - https://opencode.ai/docs/cli/
  - https://opencode.ai/docs/agents/
  - https://opencode.ai/docs/permissions/
- ForgeCode:
  - https://forgecode.dev/docs/quickstart/
  - https://forgecode.dev/docs/commands/
  - https://forgecode.dev/docs/operating-agents/
  - https://forgecode.dev/docs/shell-commands/

Local validation on this machine:

- `codex-cli 0.118.0`
- `Claude Code 2.1.90`
- `opencode 1.3.13`
- `forge 2.3.2`

Validated local command surfaces:

- `codex exec --help`
- `codex exec resume --help`
- `claude --help`
- `claude agents --help`
- `opencode --help`
- `opencode run --help`
- `opencode attach --help`
- `opencode export --help`
- `opencode serve --help`
- `forge --help`
- `forge conversation --help`
- `forge conversation resume --help`
- `forge conversation dump --help`

## 3. Canonical Adapter Contract

Before implementing any concrete adapters, AutoCode should standardize on this capability-aware contract:

```python
class HarnessAdapter(Protocol):
    def probe(self) -> HarnessProbe: ...
    def start(self, request: StartRequest) -> SessionHandle: ...
    def send(self, session: SessionHandle, prompt: PromptInput) -> RunHandle: ...
    def resume(self, request: ResumeRequest) -> SessionHandle: ...
    def interrupt(self, session: SessionHandle) -> None: ...
    def shutdown(self, session: SessionHandle) -> None: ...
    def stream_events(self, run: RunHandle) -> Iterator[HarnessEvent]: ...
    def capture_artifacts(self, session: SessionHandle) -> ArtifactBundle: ...
    def snapshot_state(self, session: SessionHandle) -> SessionSnapshot: ...
```

Required capability flags:

- `supports_resume`
- `supports_fork`
- `supports_structured_output`
- `supports_streaming_events`
- `supports_native_worktree`
- `supports_native_plan_mode`
- `supports_native_permission_modes`
- `supports_transcript_export`
- `supports_agent_spawn`
- `supports_remote_attach`

The implementation rule is:

- if a capability is absent, the adapter must say so explicitly
- AutoCode must not fake support by inventing behavior the harness does not provide

## 4. Large-Codebase Comprehension: What Still Matters Before Adapters

This matrix assumes the internal AutoCode runtime keeps improving first.

Already landed:

- iteration-zero workspace bootstrap
- structured carry-forward memory
- retrieval/index warmup on the live path
- compact repo-map preview
- stale-output collapse and truncation markers
- semantic search alias on the tool surface

Still needed before external orchestration becomes comfortable on large repos:

### 4.1 Research-only comprehension mode

Needed behavior:

- read-only tools only
- zero file mutation
- emits:
  - candidate files
  - likely entrypoints
  - active working set
  - open questions
  - compact handoff summary for the implementer

### 4.2 Active working set tracking

Needed behavior:

- keep a small ranked list of “currently hot” files and symbols
- bias retrieval and repo-map summaries toward those files
- decay or evict stale files as work moves

### 4.3 Large-repo evals

Needed metrics:

- turns-to-first-relevant-file
- context growth by turn
- compaction frequency
- stale-tool-output volume
- recovery after long tasks or resume

### 4.4 External harness bootstrap packets

Before AutoCode launches an external harness, it should feed only a bounded orientation packet:

- cwd/worktree
- active task
- pinned files
- command expectations
- tool policy expectations
- artifact capture expectations

Not the full AutoCode transcript.

## 5. Harness-by-Harness Matrix

## 5.1 Codex

### Locally validated surfaces

- `codex exec [PROMPT]`
- `codex exec resume [SESSION_ID] [PROMPT]`
- `codex exec review`
- prompt via positional arg or stdin
- `--json` JSONL event stream
- `--output-schema <FILE>`
- `--output-last-message <FILE>`
- `--ephemeral`
- `--skip-git-repo-check`
- `--sandbox read-only|workspace-write|danger-full-access`
- `--full-auto`
- `--dangerously-bypass-approvals-and-sandbox`
- `--profile`
- `--add-dir`
- `--config key=value`

### Officially documented surfaces that matter

- subagents and custom agents
- `agents.max_depth`
- `agents.max_threads`
- child sessions inherit parent runtime approval/sandbox overrides
- configuration layering through TOML profiles and project docs
- rules / exec-policy surface

### Adapter implications

Best start path:

- use `codex exec` for one-shot and CI-like runs
- use `codex exec resume` when AutoCode wants explicit continuation
- prefer `--json` when AutoCode needs structured event capture
- prefer `--output-last-message` when only the final answer is required
- use `--ephemeral` for purely temporary runs where persistence is undesirable

Resume semantics:

- native session persistence exists
- `resume` is a first-class CLI subcommand
- this is stronger than screen-scraping an interactive TUI session

Permission/sandbox semantics:

- Codex has real native sandbox and approval controls
- adapter must preserve them instead of replacing them
- AutoCode may set them, but should not pretend it owns enforcement

Plan/delegation semantics:

- subagent depth and thread limits are official
- custom agents exist
- adapter should expose this as native capability rather than translating Codex into AutoCode subagents

Transcript/artifact capture:

- JSONL event stream is the cleanest first target
- final message file is also available
- if needed, session persistence plus `resume` gives a durable session boundary

What not to assume:

- do not assume CLI-level nested team orchestration beyond what native subagents already expose
- do not assume interactive session resume is the only path; `exec resume` exists

## 5.2 Claude Code

### Locally validated surfaces

- `claude -p` / `--print`
- `--output-format text|json|stream-json`
- `--input-format text|stream-json`
- `--include-hook-events`
- `--include-partial-messages`
- `--replay-user-messages`
- `--permission-mode acceptEdits|bypassPermissions|default|dontAsk|plan|auto`
- `--allowedTools`
- `--disallowedTools`
- `--resume`
- `--continue`
- `--fork-session`
- `--session-id`
- `--agent`
- `--agents <json>`
- `--bare`
- `--mcp-config`
- `--strict-mcp-config`
- `--worktree`
- `--tmux`
- `--settings`
- `--plugin-dir`
- `--no-session-persistence`

### Officially documented / validated from docs

- tool permissions are tiered and persistent
- `/permissions` is a real control plane in the product
- hooks can approve, deny, or modify tool flow
- subagents exist and can be resumed by `SendMessage`
- agent teams are an explicit feature gate
- resumed sessions can switch back into the original worktree
- worktree isolation is a first-class feature

### Adapter implications

Best start path:

- use `claude -p` for non-interactive orchestration
- use `--output-format stream-json` when AutoCode wants event-style capture
- use `--bare` only for minimal scripted runs where hooks/LSP/auto-memory should be disabled intentionally

Resume semantics:

- `--resume` and `--continue` are first-class
- `--fork-session` lets AutoCode preserve the original and branch a continuation
- `--session-id` lets AutoCode impose an external identity when needed

Permission semantics:

- Claude Code is not just “ask or don’t ask”
- adapter must account for:
  - session permission mode
  - allowed/disallowed tool filters
  - hooks that can intercept or mutate tool decisions

Plan/delegation semantics:

- `plan` is a native permission mode
- agent/subagent/team features exist
- native teams are not the same as AutoCode orchestration; AutoCode should treat them as harness-local capabilities

Worktree semantics:

- native `--worktree` support is strong enough that AutoCode should prefer it over manual wrapping when using Claude Code

Transcript/artifact capture:

- `stream-json` is the cleanest structured runtime surface
- resumed session behavior is mature enough to trust for orchestration
- hook events can be included explicitly when needed

What not to assume:

- do not force `--bare` as the default adapter mode; it intentionally disables a lot of native behavior
- do not flatten Claude’s hooks into AutoCode middleware one-to-one

## 5.3 OpenCode

### Locally validated surfaces

- `opencode run [message..]`
- `--continue`
- `--session`
- `--fork`
- `--share`
- `--agent`
- `--format default|json`
- `--file`
- `--attach <url>`
- `--dir`
- `--port`
- `--variant`
- `--thinking`
- `opencode serve`
- `opencode attach <url>`
- `opencode export [sessionID]`
- `opencode session list`
- `opencode session delete`
- `opencode agent create`
- `opencode agent list`

### Officially documented / locally confirmed semantics

- built-in `build` and `plan` agents
- built-in `general` subagent
- client/server architecture is central
- permissions are a UX layer, not a security sandbox
- real isolation should come from Docker/VM if needed

### Adapter implications

Best start path:

- for local orchestration, `opencode run --format json` is the simplest entrypoint
- for stable remote reuse, `opencode serve` plus `opencode run --attach` or `opencode attach` is stronger

Resume semantics:

- `--continue` and `--session` are first-class
- `--fork` exists
- `export` gives a clean artifact capture path

Permission semantics:

- OpenCode’s permission system should not be treated as a sandbox
- AutoCode must supply worktree/container isolation itself if safety matters

Plan/delegation semantics:

- `plan` agent is first-class and read-only
- this makes OpenCode one of the easiest harnesses to map into an AutoCode “analysis worker” role

Remote/session semantics:

- OpenCode’s client/server architecture is a major advantage for orchestration
- AutoCode can choose:
  - ephemeral local `run`
  - attached session against a managed headless server

Transcript/artifact capture:

- `--format json` is the cleanest runtime event path
- `export` is the cleanest durable artifact path

What not to assume:

- do not assume native sandboxing exists
- do not treat permission prompts as hard security guarantees

## 5.4 Forge

### Locally validated surfaces

- `forge -p/--prompt`
- prompt via stdin or `--prompt`
- `--conversation <JSON>`
- `--conversation-id`
- `-C/--directory`
- `--sandbox <name>`
- `--agent <AGENT>`
- `-e/--event <JSON>`
- `forge conversation list`
- `forge conversation new`
- `forge conversation dump`
- `forge conversation compact`
- `forge conversation retry`
- `forge conversation resume`
- `forge conversation show`
- `forge conversation info`
- `forge conversation stats`
- `forge conversation clone`
- `forge conversation delete`
- machine-readable `--porcelain` on list-like management commands

### Officially documented / researched semantics

- `forge` is the implementation agent
- `muse` is the planning agent
- `sage` is the internal research helper/tool
- shell and command workflow docs are central to the UX

### Adapter implications

Best start path:

- use `forge --prompt` for single-run automation
- set `--conversation-id` if AutoCode wants stable native continuation
- use `forge conversation dump` after runs for transcript-grade artifact capture

Resume semantics:

- `forge conversation resume <ID>` is a first-class resume path
- `conversation clone` gives a native branch/fork-style primitive

Worktree/isolation semantics:

- `--sandbox <name>` is the important native isolation surface
- AutoCode should prefer it over inventing its own wrapper when using Forge

Agent semantics:

- `--agent` is a first-class selector
- public docs describe a meaningful separation between planning and implementation agents

Structured/runtime capture:

- Forge is weaker than Claude/OpenCode on obvious headless JSON event streaming
- the safest first adapter path is transcript-first:
  - launch natively
  - capture stdout/stderr
  - capture conversation ID
  - dump conversation JSON after the run

What not to assume:

- do not assume a `--json` event stream on the main prompt path until officially documented
- do not make AutoCode depend on fragile terminal parsing when conversation dump/info already exist

## 6. Cross-Harness Feature Matrix

| Feature | Codex | Claude Code | OpenCode | Forge |
|---|---|---|---|---|
| Non-interactive run | Yes | Yes | Yes | Yes |
| Prompt via stdin | Yes | Yes in `-p` flows | Yes | Yes |
| Native resume | Yes | Yes | Yes | Yes |
| Native fork/clone | Partial | Yes | Yes | Yes |
| Structured runtime events | Yes (`--json`) | Yes (`stream-json`) | Yes (`--format json`) | Weak / transcript-first |
| Output schema | Yes | Yes (`--json-schema`) | Not obvious on CLI | Not obvious on prompt path |
| Native plan/read-only mode | Partial via agents/config | Yes (`plan`) | Yes (`plan`) | Yes via `muse` model/agent split |
| Native worktree/isolation | Sandbox + dirs; not worktree-first | Yes | Server/dir oriented; external sandbox needed | Yes (`--sandbox`) |
| Native permissions | Yes | Yes | Yes, but not security isolation | Limited public surface from CLI |
| Transcript export | Session + JSONL paths | Session resume + transcript ecosystem | `export` | `conversation dump` |
| Remote attach/server mode | MCP/app/server ecosystems | Remote/worktree rich, but CLI is still session-centric | Yes | Not clearly first-class from CLI |

## 7. What AutoCode Must Account For

These are now mandatory checklist items for external orchestration. An adapter is not “done” unless it handles or explicitly rejects each row.

### 7.1 Session lifecycle

- new session
- resume session
- continue most recent session
- fork/clone session when supported
- stable session identity storage

### 7.2 Execution mode

- interactive-equivalent cwd/worktree launch
- prompt via arg or stdin
- non-interactive batch mode
- ephemeral/no-persistence mode where supported

### 7.3 Permissions and safety

- sandbox mode
- permission mode
- tool allow/deny surfaces
- external safety note when the harness lacks real isolation

### 7.4 Planning/delegation

- native plan/read-only mode
- native subagent or agent/team features
- native worktree/task isolation when available

### 7.5 Artifacts and replay

- event stream if available
- transcript export/dump
- stdout/stderr capture
- final message capture
- changed-files capture
- session stats if available

### 7.6 Control-plane fit

- probe command
- version detection
- feature/capability detection
- fail-closed behavior when required features are absent

## 8. Recommended Implementation Order

### Step 1: Capability probes

Before launching any harness, AutoCode should probe:

- binary exists
- version
- required subcommands exist
- required flags exist
- auth state or server reachability

### Step 2: Transcript-first adapters

Implement in this order:

1. Codex
2. Claude Code
3. OpenCode
4. Forge

Reason:

- Codex, Claude, and OpenCode already expose clean structured/headless surfaces.
- Forge is viable, but its safest initial adapter is transcript-first rather than event-stream-first.

### Step 3: Normalize into AutoCode events

Map each harness into:

- session started
- prompt sent
- tool activity observed
- approval requested / approval denied / approval granted
- partial output
- final result
- transcript exported
- run failed / interrupted

### Step 4: Only then build cross-harness team UX

Do not attempt “Claude + Codex + OpenCode chatting together” until:

- each adapter is trustworthy on its own
- transcript capture is stable
- resume/clone behavior is proven

## 9. Bottom Line

The right design is:

- AutoCode owns the control plane.
- External harnesses keep their own runtime semantics.
- Adapters translate native sessions into AutoCode events and artifacts.

The wrong design is:

- reimplement harness internals inside AutoCode
- flatten every harness to the same fake loop
- screen-scrape terminal UIs when the native CLI already exposes a resumable/exportable surface

This research removes the main ambiguity around the checklist item. The remaining work is now implementation, not discovery.
