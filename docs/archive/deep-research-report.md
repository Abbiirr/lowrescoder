# Roadmap to a Stable, Migration-Friendly Coding-Agent TUI

## Scope, goals, and constraints

This roadmap aims to produce a **stable v1 terminal UI (TUI) coding agent** that regular developers can adopt immediately, and that **Claude Code / Pi users can migrate to with minimal friction**—primarily by preserving file formats, directories, and workflow expectations (project memory files, skills, hooks, session history, and permission gates). citeturn7view1turn7view2turn7view0turn4view2turn8view3

Two non-negotiable constraints shape the plan:

- **Clean-room implementation**: you can learn from public documentation and public analyses, but avoid copying proprietary leaked code or reproducing it verbatim. The Claude Code leak context (accidentally shipped sourcemap, subsequent analysis and rewrites) is widely discussed, but the engineering goal here is to implement *capabilities and interface contracts*, not to replicate proprietary code. citeturn4view1turn9view3
- **Stability first**: v1 must be “boring” in the best way—predictable input handling, deterministic rendering, resilient session storage, and testable tool execution. The “5 levels” user-journey framework is a good way to scope v1 and prevent overreach: start with raw prompting → project memory → skills → hooks; treat orchestration as post‑v1 unless you can ship it behind a safe boundary. citeturn4view2turn7view1turn7view2turn7view0

In the sources you provided (and adjacent primary docs), the most repeatable “why these tools feel usable” themes are:

- **Progressive disclosure for context** (skills, repo maps, dynamic loading) to control token use and reduce context noise. citeturn7view2turn11view0turn5view5turn15view0turn15view2
- **Explicit permission/sandbox controls** that map to user trust and risk tolerance (allow/ask/deny, read-only vs workspace-write, etc.). citeturn7view4turn17view4turn17view5turn9view2
- **Lifecycle automation** (hooks) to turn “please run tests” from a prompt into enforceable infrastructure. citeturn7view0turn6search4turn4view2
- **Resumable, inspectable history** (tree sessions + compaction + export) to survive long work without losing state. citeturn8view1turn7view3turn11view3turn17view2

## What the reference tools get right

This section distills the best *portable* ideas from each source—i.e., features and patterns you can implement cleanly without inheriting their entire architecture.

### Claude Code’s “harness primitives” to copy

The migration-critical primitives are not “UI polish,” they’re **filesystem contracts** and **lifecycle extension points**:

- **Project memory via `CLAUDE.md`**: loaded into context at session start, with explicit guidance to keep it concise (target under ~200 lines) and split via imports / rule files when it grows. It can import other files via `@path` syntax, and external imports trigger an approval prompt the first time. citeturn7view1
- **Skills as folders with `SKILL.md`** using YAML frontmatter + markdown instructions, with live change detection (skills update within the current session when edited). Skills can be personal, project-specific, plugin-scoped, etc., and frontmatter supports controls like `disable-model-invocation`, `allowed-tools`, optional subagent execution (`context: fork`), and even skill-scoped hooks. citeturn7view2
- **Hooks as a lifecycle event bus**: a defined set of events can fire once per session, once per turn, and per tool call; hooks can observe context and *block* tool calls at `PreToolUse`. citeturn7view0turn6search4

Two additional architectural insights from public analysis are worth treating as **post‑v1 optimizations**, but should influence design decisions now:

- **Prompt cache boundary** (stable vs dynamic prompt split) to control cost and cache busting. citeturn13view0turn13view3
- **Compaction is an attack surface** if you do not preserve origin metadata (user vs tool output vs file content) during summarization; attackers can “smuggle” instructions via repo files that survive compaction. citeturn13view2turn13view3

The security discussion around shell execution also contains implementable lessons: the analyzed harness reportedly performs **AST-based validation** of shell commands and defaults to “ask the human when in doubt,” and highlights edge cases like carriage-return tokenization differences between parsers. citeturn13view3turn4view0

### Pi’s “minimal but extensible” system to copy

The Pi monorepo is effectively a field guide for *how to keep a small core stable while still empowering power users*:

- **Tiny default tool surface** (four tools: read/write/edit/bash) with customization via skills, prompt templates, extensions, themes, and packages. citeturn4view3turn8view1
- **Message queue** to let users steer mid-flight without racing the agent: Enter queues a steering message delivered after the current tool-using turn; Alt+Enter queues a follow-up after the agent finishes. citeturn8view0turn8view3turn11view2
- **Sessions as a JSONL tree** (`id`/`parentId`) enabling in-place branching (`/tree`), plus export/share flows. citeturn8view1turn11view3
- **Compaction mechanics** with explicit thresholds and reserve tokens, plus extension points to intercept summarization. citeturn7view3turn10search23turn11view1
- **Skills compatibility**: Pi implements the Agent Skills standard, discovers skills from multiple locations, and explicitly supports reusing Claude Code and Codex skill directories by adding them to settings. citeturn11view0
- **Extensions as first-class**: TypeScript modules that can intercept tool calls, add commands, present UI prompts, persist state into sessions, and hot‑reload. citeturn11view1turn8view3
- **RPC/headless mode** over JSONL, with strict framing rules and streaming-safe message queue semantics (important if you want multiple frontends). citeturn11view2turn4view3

There’s also a philosophical stance you should decide on early: Pi’s author explicitly describes it as **“YOLO by default”** with no permission prompts/safety rails, arguing that sandboxing is often “security theater.” citeturn10search21  
For a migration-friendly v1, you likely want the opposite default (safe-by-default), but you can still offer an explicit “danger” mode.

### OpenAI Codex CLI’s operational model to copy

Codex CLI documentation emphasizes a tight loop of “inspect, edit, run,” but the most migration-relevant benefits are its **approval/sandbox model** and strong “operational UX”:

- Runs locally; can read/change/run code in the selected directory. citeturn5view0
- **Approval modes and sandbox policies**: default workspace-limited behavior; asks approval for edits outside workspace or commands requiring network access; provides explicit “danger-full-access / yolo” escape hatches. citeturn17view4turn17view5
- The CLI surfaces features that matter to v1 parity: interactive TUI sessions, code review by a separate agent, subagents, scripting (`exec`), and MCP tool access. citeturn5view0turn17view5
- In GitHub workflows, Codex code review uses `AGENTS.md` review guidelines and follows the closest file per changed path. citeturn12view0turn7view1

### OpenCode’s “terminal-first platform” to copy

OpenCode is the clearest reference for a **provider-agnostic, configurable, multi-client architecture**:

- Its own README highlights core differentiators vs Claude Code: **open-source, provider-agnostic, built-in LSP support, and client/server architecture** enabling remote control (TUI is “one client”). citeturn5view3
- **Permission config** is explicit: `allow`, `ask`, `deny`, with wildcard rules and granular matching (e.g., deny `rm *`, allow `git *`). citeturn7view4turn6search2
- **Config layering and managed settings**: project `opencode.json` overrides global config; config files are merged, and enterprise-managed config can be enforced at system paths. citeturn7view5turn16search25
- **Server mode**: `opencode serve` exposes an OpenAPI 3.1 endpoint; when you run `opencode` it starts both a server and a TUI client; TUI can attach to a running backend (`opencode attach`). citeturn17view1turn17view2
- **Built-in LSP integration**: uses diagnostics; ships many built-in language servers (e.g., `gopls`, `clangd`, etc.), and also offers an experimental `lsp` tool for call hierarchy, definitions, references, hover, etc. citeturn17view0turn17view3
- **GitHub automation**: triggering via `/opencode` or `/oc` in comments and running inside GitHub Actions runners; supports triage, implementation on new branches, PR creation, scheduled tasks. citeturn12view1

### Aider’s “context compression + git discipline” to copy

Aider’s enduring advantage is that it makes large-repo edits work reliably by combining **structured context + verification loops**:

- **Repo map**: it sends a concise map of the repository with key symbols and signatures, then selects the most relevant parts using a dependency-graph ranking approach to fit a token budget. citeturn5view5
- **Git integration**: automatically commits changes with sensible commit messages and encourages diffs/rollback via normal git tools. citeturn5view4
- **Automatic lint/test after edits** is a documented feature; the agent can fix issues detected by test suites/linters. citeturn5view4

### Claw Code’s “verification harness mindset” to copy

Claw Code is a useful reference not because it’s “the best UX,” but because it treats verification as a first-class product surface:

- **Health checks** (`claw doctor`) as a first-run diagnostic. citeturn9view0
- **Permission modes** (read-only → workspace-write → danger-full-access) as explicit modes. citeturn9view2turn9view0
- **Deterministic mock service + parity harness** in the workspace (“mock Anthropic-compatible service”), plus a clear “run verification” step (workspace tests). citeturn9view2turn9view0

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["OpenCode TUI screenshot","Pi coding agent terminal UI screenshot","OpenAI Codex CLI TUI screenshot","aider terminal screenshot"],"num_per_query":1}

## V1 definition that users can migrate to

A v1 that “everyone can use” is less about feature count and more about **compatibility + predictability**. The following v1 scope is designed to align with the “levels” progression users describe—v1 should cover Levels 1–4 solidly, with Level 5 (orchestration) postponed unless strictly scoped. citeturn4view2

### The migration promise for v1

The migration promise should be phrased in terms of artifacts users already maintain:

- **Project memory**: supports `CLAUDE.md` loading semantics (walk up directory tree; support `CLAUDE.local.md`; optional `@imports`; strip block HTML comments; optional excludes) and explicitly supports importing `AGENTS.md` so teams don’t duplicate instructions. citeturn7view1
- **Skills**: supports `SKILL.md` + YAML frontmatter + progressive disclosure (frontmatter in always-loaded catalog; body loaded on demand; linked files optional), and supports Claude-style and Agent Skills–style conventions well enough that existing skills can be reused with minimal edits. citeturn7view2turn15view0turn15view2turn11view0
- **Hooks**: supports Claude Code’s hook lifecycle events and JSON payload I/O, including the ability to block tool calls at `PreToolUse` and react to permission prompts. citeturn7view0turn6search4
- **Sessions**: provides durable, inspectable session storage with branching and compaction; Pi’s JSONL-tree is a proven design you can adopt or emulate. citeturn11view3turn8view1turn7view3
- **Permission and sandboxing**: provide explicit permission rules (allow/ask/deny) plus a higher-level sandbox mode that aligns to user mental models (read-only, workspace-write, full access) and can be changed in-session. citeturn7view4turn17view4turn17view5turn9view2

### V1 product surface

V1 needs a tight product surface (the “everyday loop”), plus essential power-user controls:

Everyday loop:
- Interactive TUI session (streaming output)
- Multi-line editor with file references (at minimum, `@` fuzzy file reference is an established norm) citeturn5view2turn8view3
- Tool execution view with collapsible tool output and explicit approval prompts
- A **message queue** mechanic for steering mid-execution (this solves a major usability problem when tool calls take time) citeturn8view0turn11view2
- Session persistence and resumption

Power-user controls:
- `/model` switching (or equivalent) at runtime citeturn5view0turn8view3
- `/permissions` (or equivalent) to switch sandbox/approval modes citeturn17view5turn17view4turn9view2
- `/compact` + automatic compaction with transparent summaries and “go back via tree” capability citeturn8view1turn7view3turn10search23
- `/tree`-style navigation and branching history citeturn8view1turn11view3turn6search19
- Hooks config and a basic “hook status” view (what fired, what blocked) citeturn7view0turn6search8

## Technical blueprint for implementing v1

This is the “how to build it” layer: modules, boundary choices, and what each part must guarantee. The intent is to make later research and implementation tasks decomposable and testable.

### Agent runtime core

Adopt a “minimal core, extension ring” architecture:

- **Core**: message loop (prompt → tool calls → results → model → final), session persistence, compaction, and a small set of built-in tools.
- **Extension surface**: hooks + skills + plugins/extensions.
- **Cross-run mode support**: interactive TUI plus headless (JSON/RPC) mode so other clients can exist later.

Pi’s docs provide a fully worked example of this split: minimal default tools, extensions ability to intercept tool calls and add UI, and an RPC protocol over JSONL. citeturn4view3turn11view1turn11view2

If you want remote clients later, OpenCode’s design shows a clean path: TUI is a client talking to a server; `serve` exposes an OpenAPI endpoint; `attach` lets a TUI connect to a remote backend. citeturn17view1turn17view2turn5view3

### Instructions and “project memory” loader

Implement Claude-compatible semantics for `CLAUDE.md` resolution (because migration depends on it), including:

- directory-walk loading order
- `CLAUDE.local.md` precedence
- `@imports` with bounded recursion depth
- external import approval prompt
- optional excludes for monorepos
- `AGENTS.md` interoperability via import recommendation citeturn7view1turn12view0

OpenCode’s concept of “instructions list files” is similar but config-driven; supporting both styles is feasible: `CLAUDE.md` for Claude migrants, `opencode.json`-style “instructions:” arrays for OpenCode migrants. citeturn6search18

### Skills system

For v1 migration parity, support both:

- **Claude Code skills semantics** (`~/.claude/skills/<name>/SKILL.md` and project `.claude/skills/…`, live reload, YAML frontmatter fields like `disable-model-invocation`, `allowed-tools`, subagent execution controls). citeturn7view2
- **Agent Skills standard** conventions (name rules, description importance, progressive disclosure scanning), since Pi and other ecosystems use it and it supports reusing Claude/Codex skills explicitly. citeturn11view0turn15view0turn15view2

The official skills guide emphasizes progressive disclosure (frontmatter always loaded; body loaded when needed; optional linked files) and composability (multiple skills coexisting), plus concrete “how to measure success” ideas like trigger-rate testing and tool-call count comparisons. citeturn15view0turn15view1

### Hooks and automation

Hooks are the bridge between “agent did something” and “workflow is safe and verified.” Claude Code’s hooks reference provides:

- event taxonomy and cadence (session, turn, tool-call) citeturn7view0
- blocking mechanisms (PreToolUse can block tool calls) citeturn7view0
- practical automation patterns (e.g., PostToolUse formatting/linting) citeturn6search4

In v1, implement at least:
- SessionStart hooks for context injection
- PreToolUse hooks for gating
- PostToolUse hooks for verification and formatting
- Stop/StopFailure hooks for end-of-turn quality gates and reporting citeturn7view0turn4view2

### Permissions and sandbox model

Unify three proven ideas into a coherent, user-understandable policy:

- **Granular per-tool allow/ask/deny rules** (OpenCode) with wildcards and pattern matching over inputs (especially for bash: allow `git *`, deny `rm *`, etc.). citeturn7view4turn6search2turn7view4
- **Sandbox modes** (Codex / Claw Code) that define default trust zones: read-only, workspace-write, full access. citeturn17view4turn17view5turn9view2
- **Lifecycle interception** (Claude hooks) so permissions are observable as events and can be audited or enforced externally. citeturn7view0turn7view4

Two v1 security details are directly motivated by the leak analyses:

- Treat compaction as a security boundary: do not let tool-derived text become indistinguishable from user instructions during summarization. citeturn13view3turn13view2
- Test command parsing against non-obvious tokenization pitfalls (e.g., carriage returns) if you implement any “safe bash” classifiers. citeturn13view3turn4view0

### Context intelligence: repo map + LSP

You likely need both, but with different roles:

- **Repo map** (Aider): always-on, concise, model-friendly “index” of symbols and key signatures, optimized to a token budget via graph signals. This is extremely compatible with the “progressive disclosure” design philosophy and can be implemented without needing deep tool plumbing in v1. citeturn5view5
- **LSP** (OpenCode + Claude harness analysis): best for verification after edits (diagnostics) and precision navigation for definitions/references/call hierarchy. OpenCode already documents both built-in LSP server integration and the `lsp` tool operations that matter. citeturn17view0turn17view3turn13view0

For v1, a pragmatic sequence is:
1) ship repo map + fuzzy file reference
2) add LSP diagnostics after edits (as a hook-triggered verification step)
3) later expose full LSP tool APIs (definition, references, call hierarchy) citeturn17view0turn17view3turn6search4

### Session model and compaction

Adopt a session model that is:

- **append-only**
- **stable across crashes**
- **branchable**
- **exportable**

Pi’s JSONL tree format is a strong reference (id/parentId tree, versioned sessions, and clear migration behavior). citeturn11view3turn8view1

Compaction needs to be transparent and controllable:

- explicit manual compaction (`/compact`)
- auto-compaction before overflow and on overflow recovery
- a structured summary format
- truncation strategies for massive tool outputs citeturn8view2turn7view3turn10search23

The Sabrina analysis highlights a real production failure mode: compaction retries can silently burn massive API spend if not circuit-broken; therefore, v1 should include explicit circuit-breakers and telemetry around compaction failures. citeturn13view3

## Delivery roadmap from v1 to post‑v1 improvements

This roadmap is organized as “v1 milestones” (hard requirements for a usable migration target) and “post‑v1 improvements” (where you start to surpass Claude Code / Pi / others instead of chasing parity).

### V1 milestones

**Stabilize the loop**
- Deliver interactive TUI with: streaming transcript, multi-line editor, file reference insertion, tool call cards, and explicit approvals.
- Implement message queue (steering + follow-up) semantics consistent across UI and headless mode. citeturn8view0turn11view2
- Ship session persistence + resume + export.

**Compatibility and migration**
- Implement `CLAUDE.md` loading + `@imports` + `CLAUDE.local.md` + `AGENTS.md` import guidance. citeturn7view1turn12view0
- Implement skills discovery with:
  - Claude-style directories (`~/.claude/skills`, project `.claude/skills`)
  - progressive disclosure scanning of name/description
  - live reload of skill edits in-session citeturn7view2turn15view0
- Implement hooks (at minimum: SessionStart, PreToolUse, PostToolUse, Stop/StopFailure) with JSON payloads and an allowlist of safe hook runtimes. citeturn7view0turn6search4

**Safety defaults**
- Ship a clear permission/sandbox surface:
  - “read-only / workspace-write / full access” modes
  - per-tool allow/ask/deny rules with granular bash patterns citeturn17view4turn7view4turn9view2
- Add compaction origin labeling and “instruction provenance” so file-sourced text cannot silently become user instruction after summarization. citeturn13view3

**Verification in the workflow**
- Provide hook templates (or built-in “verification profiles”) that run:
  - formatter after edits (PostToolUse)
  - typecheck per file (PostToolUse)
  - targeted tests before Stop
- Provide a “separate reviewer” mode (second agent pass) as Codex and others emphasize code review as a distinct step. citeturn5view0turn12view0turn5view4

**Context intelligence baseline**
- Implement repo map generation and token-bounded selection. citeturn5view5
- Implement “diagnostics after edits” via LSP integration (even if you don’t yet expose the full LSP tool). citeturn17view0turn17view3

### Post‑v1 improvements

**Multi-client and remote workflows**
- Add optional “server-first” mode (OpenCode style): TUI client attaches to a long-running backend over HTTP; support web/mobile clients later. citeturn17view1turn17view2
- Add “remote safe access” patterns: server auth, CORS allowlists, explicit bind/hostname choices. citeturn17view1

**Orchestration and parallelism**
- Add subagents and worktree isolation gradually. Both the leak analysis and Codex docs highlight subagents as a core scaling method, but this should be introduced after stability because it multiplies state complexity. citeturn13view0turn5view0turn7view0
- If you implement orchestration, scope it with explicit guardrails: isolated worktrees, conflict avoidance, and clear resumability (Level‑5 style). citeturn4view2turn12view0

**Cost and performance engineering**
- Implement explicit prompt cache boundary design (stable vs dynamic prompt) so you can take advantage of provider caching where available and avoid unnecessary cache-busting. citeturn13view0turn13view3
- Add structured compaction strategies and circuit breakers informed by real-world failure modes. citeturn13view3turn7view3

**Self-updating docs and “agent-maintained artifacts”**
- Implement a constrained “single-file doc updater” (inspired by “Magic Docs”): only allows editing one file, invoked when idle, and gated by explicit opt-in. citeturn13view0

**Ecosystem integrations**
- GitHub automation:
  - start with pull-request review using repository guidelines (`AGENTS.md`-style) and sandboxed runners (OpenCode style) citeturn12view1turn12view0
  - then expand to issue triage, scheduled jobs, etc. citeturn12view1
- MCP ecosystem:
  - support MCP servers with clear permission mapping and destructive annotation handling (Codex notes destructive tool calls should always require approval when advertised as destructive). citeturn17view4turn16search21

## Verification methods and acceptance criteria

This section describes how you prove v1 is stable and safe enough to ship broadly, using verification patterns explicitly present in the reference tools and adding a few critical “agent-specific” test types.

### Verification methods you can adopt directly from the sources

**Deterministic agent harness testing**
- Use a **mock provider service** to run deterministic test cases through the agent loop, similar to Claw Code’s deterministic mock service / parity harness approach. This is the best way to regression-test tool calling, message queue semantics, and hook decision paths without relying on nondeterministic model outputs. citeturn9view2turn11view2

**Hook-driven verification gates**
- Treat format/lint/typecheck/test execution as hooks triggered on tool use or stop events. Claude’s hook lifecycle and reference guide patterns make this achievable and standardizable. citeturn7view0turn6search4
- Add a “verification profile” library: common hook configs that users can adopt per language/toolchain (formatters, test runners, typecheckers).

**Transcript and rollback discipline**
- Ensure every tool action is logged in the session transcript and exportable; Codex emphasizes that actions are transcripted and you can review/rollback with normal git workflows. citeturn17view5turn5view4
- Require “diff-first” confirmation in the UI before large multi-file writes, unless the user has explicitly escalated permissions.

### Acceptance criteria for v1 readiness

A v1 should be considered “stable” only if it can pass these acceptance tests reliably:

**UI stability**
- No broken rendering under:
  - rapid resizes
  - large tool outputs (truncate + “view more”)
  - streaming output interleaved with tool calls
- Deterministic keyboard routing:
  - message queue works during streaming/tool execution
  - `/commands` and autocomplete don’t lose focus citeturn8view0turn8view3

**Session integrity**
- Session file is append-only and recoverable after crash.
- `/tree` navigation never corrupts history; branching produces consistent `parentId` structure.
- Compaction never discards raw history; summaries are explicit and reversible by navigating the tree. citeturn11view3turn8view1turn7view3

**Security and permissions**
- Permission rules are testable and explainable: given a tool call, you can deterministically show which rule matched and why (OpenCode’s allow/ask/deny and pattern matching are a useful model). citeturn7view4turn7view5
- Sandbox modes behave as promised: read-only cannot edit/run; workspace-write cannot escape workspace or use network unless explicitly enabled; full access is gated and clearly labeled. citeturn17view4turn17view5
- Compaction preserves instruction provenance to mitigate “instruction smuggling” concerns described in public analysis. citeturn13view3

**Migration correctness**
- A Claude Code user can drop in their `CLAUDE.md` and skills folders and the tool:
  - loads them predictably
  - updates skills live when edited
  - supports hooks with the expected event names and payload schemas citeturn7view1turn7view2turn7view0
- A Pi user can expect:
  - message queue semantics
  - session branching and compaction behavior
  - skill discovery from their existing directories (including “use skills from other harnesses” patterns) citeturn8view0turn11view3turn11view0

### Measurement and “verification of verification”

Use the skills guide’s notion of success criteria as a template for measuring behavioral reliability:

- Skill triggering accuracy (e.g., “does it load when it should?”) and “how to measure” via test prompts. citeturn15view1
- Tool-call counts and retry rates for workflows to detect regressions and runaway loops. citeturn15view1turn13view3
- Hook success/failure rates (Stop vs StopFailure) and explicit circuit breakers for repeated failures (notably compaction). citeturn7view0turn13view3

Finally, treat “verification” as a product feature, not just tests: the Sabrina analysis describes an internal “verification agent” mindset (“verify independently”). Whether or not you implement a dedicated “verification agent,” the product should make it harder to skip checks and easier to run them. citeturn13view3