# Large-Codebase Comprehension and External Harness Orchestration

> Date: 2026-04-01
> Goal: Define the next two major research-backed workstreams for AutoCode after the current internal orchestration substrate: (1) fast large-codebase comprehension without context-window overload and (2) external native-harness orchestration for Codex, Claude Code, OpenCode, and Forge-style runners.

## 1. Executive Summary

There are two distinct problems here, and they should not be conflated:

1. **Large-codebase comprehension**
   - The goal is to move through large repositories quickly without forcing the active model context to carry the whole repository.
   - The best current systems do not solve this with “bigger context” alone. They combine retrieval/indexing, agent specialization, structured compaction, and strict output hygiene.

2. **External harness orchestration**
   - The goal is not to reimplement Codex, Claude Code, OpenCode, or Forge inside AutoCode.
   - The goal is to let those harnesses operate through their own native CLIs and policies while AutoCode owns the control plane: tasking, routing, transcripts, approvals, artifacts, and cross-harness coordination.

The practical conclusion is:

- **First build better internal codebase comprehension primitives inside AutoCode.**
- **Then build external harness adapters on top of AutoCode’s own control plane.**

Detailed harness CLI / resume / permission / transcript surfaces are tracked separately in:

- [external-harness-adapter-command-matrix.md](/home/bs01763/projects/ai/lowrescoder/docs/research/external-harness-adapter-command-matrix.md)

This matches the earlier internal-first conclusion in [autocode-internal-first-orchestration.md](/home/bs01763/projects/ai/lowrescoder/docs/research/autocode-internal-first-orchestration.md).

## 2. Current Public Competitive Context

As of the public Terminal-Bench 2.0 leaderboard snapshot available on 2026-04-01, the top published entries are:

| Rank | Agent | Accuracy | Source |
|---|---|---:|---|
| 1 | Forge Code | 78.4% +/- 1.8 | https://www.tbench.ai/leaderboard/terminal-bench/2.0 |
| 2 | Droid | 77.3% +/- 2.2 | https://www.tbench.ai/leaderboard/terminal-bench/2.0 |
| 3 | Simple Codex | 75.1% +/- 2.4 | https://www.tbench.ai/leaderboard/terminal-bench/2.0 |

Important note:

- ForgeCode’s own docs/homepage currently also claim `81.8%` and “#1 on TermBench.”
- The public leaderboard snapshot above shows `78.4%` for the currently visible Forge Code entry dated 2026-03-02.
- For planning work in this repo, use the **public leaderboard snapshot date and value** when making comparisons.

## 3. Research Topic A: Large-Codebase and File Comprehension

### 3.1 What the strongest systems are doing

Across ForgeCode, Droid, OpenCode, Codex, Goose, Pi-mono, and the local harness-engineering notes, the strongest pattern is consistent:

- **Do not stuff the repository into the live conversation.**
- **Build a retrieval and summarization layer around the agent.**
- **Keep only the active slice of the repo in the hot context window.**

### 3.2 The useful patterns

#### Pattern A1: Retrieval/indexing must be first-class

ForgeCode is the clearest current example. Its “ForgeCode Services” runtime exposes:

- a context engine that “starts the agent in the most relevant files and functions”
- project indexing / semantic sync via `:sync`
- `sem_search` as a system tool

Sources:

- https://forgecode.dev/docs/forge-services/
- https://forgecode.dev/docs/file-tagging-guide/

Why this matters:

- Large-codebase comprehension is mostly a retrieval problem, not a prompt-writing problem.
- If AutoCode only has `rg`/`glob`/manual file walking, it will waste turns and burn context budget rediscovering structure.

#### Pattern A2: Split research, planning, and execution contexts

ForgeCode’s public agent model is explicit:

- `muse` for planning
- `forge` for implementation
- `sage` as the internal research tool

OpenCode does the same in a simpler form:

- `build`
- `plan`
- internal/hidden compaction and summary agents

Sources:

- https://forgecode.dev/docs/operating-agents/
- https://opencode.ai/docs/agents/

Why this matters:

- Exploration should not contaminate the execution context with thousands of lines of low-signal search output.
- AutoCode should treat “understand the repo” as a dedicated mode/agent, not as ad hoc noise inside the implementing loop.

#### Pattern A3: Structured compaction beats blind truncation

ForgeCode exposes context compaction as a first-class feature.
Codex has model-aware compaction limits and a dedicated `codex exec` / automation path.
Goose and Pi-mono, in the local corpus, both use more sophisticated thresholds and structured carry-forward summaries than AutoCode currently does.

Sources:

- https://forgecode.dev/docs/context-compaction/
- `docs/research/context-window-management.md`
- `research-components/openai-codex/codex-rs/README.md`

Why this matters:

- “Summarize everything” is not enough.
- Carry-forward memory must preserve:
  - user goal
  - current plan
  - key decisions
  - files read / files modified
  - unresolved blockers
  - next actions

#### Pattern A4: Cheap file-reference syntax matters

ForgeCode’s `@file` tagging is a good example of a lightweight UX that feeds the retrieval layer without inflating prompt size.
The docs are also candid about the limitations: broad prefixes in 500+ file repos return too many matches, so specificity and filtering matter.

Sources:

- https://forgecode.dev/docs/file-tagging-guide/
- https://forgecode.dev/docs/auto-complete/

Why this matters:

- Users need a quick way to pin exact files or code slices without manual copy-paste.
- The agent also needs an internal way to express “the active file set” without dragging whole files into context.

#### Pattern A5: Output hygiene is part of comprehension

The local harness-engineering analysis and context-window-management research both point in the same direction:

- output caps
- explicit truncation markers
- progressive removal/summarization of stale tool output
- compression of old tool-result pairs

Sources:

- `docs/research/harness-engineering-competitive-analysis.md`
- `docs/research/context-window-management.md`

Why this matters:

- Large-codebase confusion often comes from runaway tool output, not only from source files.
- A good comprehension system controls observation volume aggressively.

#### Pattern A6: Environment bootstrap reduces wasted discovery turns

The Droid/Meta-Harness style pattern is to gather environment shape early:

- repo tree shape
- git state
- build/test commands
- available tools
- package manager
- potentially code search / LSP status

Sources:

- https://docs.factory.ai/cli/getting-started/overview
- `docs/research/harness-engineering-competitive-analysis.md`

Why this matters:

- The agent should not spend its first three turns rediscovering `pwd`, `ls`, and “how do I run tests?” on every task.

### 3.3 What AutoCode should build for Topic A

#### A. Retrieval / repo-map layer

Build a codebase-comprehension substrate with:

- persistent file graph / repo map
- symbol index and dependency hints
- semantic search over synchronized project state
- “active working set” selection for current task

#### B. Research-only comprehension agent

Add an explicit read-only comprehension mode/agent that is optimized for:

- locating the right files
- producing a concise task-scoped repo summary
- handing only the relevant file set and findings to the implementer

#### C. Structured carry-forward memory

Replace generic compaction summaries with structured state:

- objective
- active task
- decisions
- open questions
- read files
- modified files
- blockers
- next steps

#### D. Output-budget controls

Treat output volume as a first-class budget:

- hard caps per tool response
- truncation markers
- post-tool summarization for oversized output
- stale-output collapse when context pressure rises

#### E. Bootstrap snapshot

Add a first-turn environment bootstrap that feeds the implementing agent:

- repo root / worktree
- build/test entrypoints
- git status summary
- runtime/tool availability
- top-level package/module map

## 4. Research Topic B: External Native-Harness Orchestration

### 4.1 The core principle

AutoCode should not “clone” Codex, Claude Code, OpenCode, or Forge.

It should:

- let each harness operate in its native runtime
- drive that runtime from outside the way a human would
- normalize transcripts, artifacts, and control signals into AutoCode’s control plane

That means:

- **native CLI / session execution**
- **native permission and sandbox semantics left intact**
- **AutoCode as broker, not reimplementation**

### 4.2 What “simulate real human behavior” means here

The correct adapter model is:

- launch the harness CLI as a subprocess
- set cwd/worktree/env exactly as a human session would
- feed prompt text via documented non-interactive or scripted surfaces
- capture stdout/stderr/logs/session IDs
- continue/resume sessions with the harness’s own continuation APIs
- never bypass the harness by talking to raw model APIs unless the harness itself requires it

### 4.3 Execution surfaces we can actually target

#### Codex

Useful native surfaces:

- `codex exec PROMPT`
- prompt via stdin
- `--ephemeral` for non-persistent automation
- explicit sandbox modes
- `codex mcp-server` for using Codex as a tool from another MCP client

Local source evidence:

- `research-components/openai-codex/codex-rs/README.md`
- `research-components/openai-codex/docs/install.md`

Why Codex is a good first adapter:

- the headless `exec` mode is explicit and documented
- sandbox/approval surfaces are explicit
- MCP server mode gives an alternate integration path

#### Claude Code

Useful native surfaces:

- `claude -p` / print mode for scripted calls
- `--bare` for lightweight scripted calls
- `--output-format json|stream-json` for machine-readable output
- `--continue` / `--resume` for session continuation
- hooks and agent-team semantics for richer coordination

Official docs and current source evidence:

- https://code.claude.com/docs/en/headless
- https://code.claude.com/docs/en/agent-teams
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- `research-components/claude-code/CHANGELOG.md`

Important nuance:

- Claude Code already has richer internal team semantics than a simple subprocess worker.
- AutoCode should still treat Claude Code as an **external worker runtime**, not as the control plane.

#### OpenCode

Useful native surfaces:

- `opencode run`
- `--format json`
- `--attach` to a running `opencode serve`
- `opencode serve` for headless API access
- session creation / continuation / share APIs
- explicit agent and permission configuration

Sources:

- https://opencode.ai/docs/cli/
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/permissions/
- `research-components/opencode/packages/opencode/src/cli/cmd/run.ts`

Why OpenCode is especially orchestration-friendly:

- it already exposes JSON event output
- it already supports headless server/client operation
- it has explicit per-agent and per-subagent permission policy

#### ForgeCode

Useful native surfaces:

- `forge -p "prompt"` for non-interactive execution
- stdin piping into `forge`
- `--conversation-id` for continuation
- `--sandbox` for worktree isolation
- `--agent` to select `muse` / `forge`
- `-w` / `--workflow` for workflow execution

Sources:

- https://forgecode.dev/docs/cli-reference/
- https://forgecode.dev/docs/sandbox-feature/
- https://forgecode.dev/docs/operating-agents/
- https://forgecode.dev/docs/forge-services/

Important limitation:

- The public docs do not currently expose a clearly documented machine-readable event stream comparable to OpenCode’s JSON mode or Droid’s explicit headless output modes.
- So a Forge adapter likely starts as a **prompt/result/transcript adapter**, not a rich event-stream adapter.

#### Droid (reference, not target harness)

Droid is useful as a design reference even if AutoCode does not target it first:

- `droid exec`
- `--output-format`
- `--input-format stream-json`
- `--session-id`
- explicit autonomy levels
- fail-fast scripted execution model

Sources:

- https://docs.factory.ai/cli/droid-exec/overview
- https://docs.factory.ai/cli/user-guides/auto-run

Why this matters:

- Droid is the clearest documented example of a **real headless terminal-agent CLI** designed for automation.
- AutoCode’s external-harness runner should resemble this level of operational explicitness.

### 4.4 What AutoCode should build for Topic B

#### B. Canonical HarnessAdapter contract

Define one adapter interface per external harness with methods like:

- `probe()`
- `start()`
- `send()`
- `resume()`
- `interrupt()`
- `shutdown()`
- `capture_artifacts()`
- `stream_events()`
- `snapshot_state()`

#### C. Normalize to AutoCode’s event schema

Every external harness should map into one canonical event model:

- session started
- task assigned
- message sent
- tool use observed
- file edits observed
- approval required
- task completed / failed
- artifact emitted

This should sit on top of the internal event-schema work already planned/landed for AutoCode.

#### D. One worktree per harness session

To preserve real-human behavior while avoiding conflicts:

- each external harness session gets its own worktree or isolated workspace
- AutoCode owns lifecycle and cleanup
- merge/synthesis happens after the harness run, not during

#### E. Transcript-first capture

Especially for Codex/Forge/Claude Code adapters, AutoCode should capture:

- stdout/stderr transcript
- session id / resume token
- changed files
- test commands executed
- final patch/diff or commit
- failure reason / exit code

#### F. Do not bypass native safety

AutoCode should not erase the harness’s native semantics:

- Codex approvals/sandbox
- Claude hooks/permissions/agent-teams behavior
- OpenCode permission.task / doom_loop / external_directory
- Forge restricted shell / sandbox mode

### 4.5 Recommended implementation order

1. **Large-codebase comprehension first**
   - retrieval / repo map
   - research-only comprehension agent
   - structured compaction and output hygiene

2. **External adapter prototypes next**
   - OpenCode adapter first (best machine-readable surfaces)
   - Codex adapter second (`codex exec`, optional MCP)
   - Claude Code adapter third (`-p`, `--bare`, `--resume`, hooks-aware)
   - Forge adapter fourth (`-p`, `--conversation-id`, `--sandbox`, transcript-first)

3. **Only after adapter prototypes**
   - build cross-harness orchestration UI and policy layer

## 5. Recommended Checklist Translation

The checklist should add two explicit carry-forward epics:

1. **Large codebase / file comprehension**
   - retrieval/indexing
   - active file set selection
   - research-only comprehension agent
   - structured compaction
   - bootstrap snapshot
   - output hygiene

2. **External native-harness orchestration**
   - canonical adapter contract
   - worktree/session isolation
   - Codex / Claude Code / OpenCode / Forge adapters
   - transcript/artifact normalization
   - “simulate real human use” contract via native CLI execution

## 6. Sources

### Official / current web sources

- Terminal-Bench leaderboard
  - https://www.tbench.ai/leaderboard/terminal-bench/2.0
- Terminal-Bench 2.0 announcement
  - https://www.tbench.ai/news/announcement-2-0
- ForgeCode homepage
  - https://forgecode.dev/
- ForgeCode Services
  - https://forgecode.dev/docs/forge-services/
- ForgeCode operating agents
  - https://forgecode.dev/docs/operating-agents/
- ForgeCode CLI reference
  - https://forgecode.dev/docs/cli-reference/
- ForgeCode file tagging
  - https://forgecode.dev/docs/file-tagging-guide/
- ForgeCode sandboxes
  - https://forgecode.dev/docs/sandbox-feature/
- OpenCode CLI
  - https://opencode.ai/docs/cli/
- OpenCode agents
  - https://opencode.ai/docs/agents/
- OpenCode permissions
  - https://opencode.ai/docs/permissions/
- Claude Code agent teams
  - https://code.claude.com/docs/en/agent-teams
- Claude Code headless / programmatic usage
  - https://code.claude.com/docs/en/headless
- Claude Code subagents
  - https://code.claude.com/docs/en/sub-agents
- Claude Code hooks
  - https://code.claude.com/docs/en/hooks
- Factory Droid overview
  - https://docs.factory.ai/cli/getting-started/overview
- Factory Droid exec
  - https://docs.factory.ai/cli/droid-exec/overview
- Factory auto-run
  - https://docs.factory.ai/cli/user-guides/auto-run
- OpenAI Codex product pages
  - https://openai.com/index/introducing-codex/
  - https://openai.com/index/introducing-upgrades-to-codex/
  - https://openai.com/index/introducing-gpt-5-2-codex/
  - https://openai.com/index/harness-engineering

### Local primary references

- `research-components/openai-codex/codex-rs/README.md`
- `research-components/openai-codex/docs/install.md`
- `research-components/opencode/packages/opencode/src/cli/cmd/run.ts`
- `research-components/claude-code/CHANGELOG.md`
- `docs/research/context-window-management.md`
- `docs/research/harness-engineering-competitive-analysis.md`
- `docs/research/terminal-bench-analysis.md`
- `docs/research/autocode-internal-first-orchestration.md`
