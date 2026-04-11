# Harness Improvement Proposal v2

**Date:** 2026-04-08  
**Purpose:** consolidate all research from this session into a more detailed, implementation-oriented proposal for improving our coding-agent harness.  
**Primary focus:** memory management, context control, subagents, permissions, hooks, execution layers, deferred tool loading, programmatic tool calling, and practical lessons from `just-bash`, Executor, Claude Code public docs, and the `learn-coding-agent` research repo.

---

## 1. Executive recommendation

Our harness should not aim to imitate a leaked implementation detail-by-detail. It should deliberately adopt the strongest **durable harness patterns** visible across the official Claude Code documentation, Anthropic engineering posts, Vercel’s `just-bash`, Executor’s integration model, and the community synthesis in `learn-coding-agent`.

The central design shift is this:

> Stop thinking of the harness as “a model with tools.”
> Build it as a **multi-layer control system** around the model.

That means the improved harness should include:

1. **File-based persistent instructions** instead of relying on chat history.
2. **Layered memory** instead of a single growing transcript or vector dump.
3. **Aggressive compaction** as a default behavior, not a rescue feature.
4. **Subagent isolation** to keep the main context clean.
5. **Deferred tool loading and tool search** so the model does not pay the context cost for unused tools.
6. **Programmatic tool calling** for multi-step external workflows and data-heavy tasks.
7. **A split execution model**:
   - real shell/container for local repo work,
   - bounded virtual shell for safe exploration/evals,
   - typed code-execution layer for orchestration.
8. **Permissions, hooks, and policy** as first-class architecture.
9. **State, transcripts, and resumability artifacts** designed intentionally rather than as by-products.
10. **Enterprise-ready managed policy hooks** only after the local-first core is stable.

---

## 2. Source trust model

This proposal uses three evidence tiers.

### Tier A — Primary, durable sources

Use these as ground truth for design decisions:

- Claude Code docs
- Claude API / tool-use docs
- Anthropic engineering posts
- Vercel `just-bash` docs
- Executor official docs

### Tier B — Secondary synthesis sources

Use these as architecture inspiration, not as canonical truth:

- `sanbuphy/learn-coding-agent`
- post-leak commentary
- architecture breakdown threads and blog posts

### Tier C — High-risk material

Do **not** design around these unless independently validated:

- random mirror repos
- malware-laced “leak” bundles
- unverifiable screenshots/snippets
- claims with no official or multi-source support

### Practical rule

If something is only present in leak-era discussion but not supported by official docs or multiple reliable sources, treat it as **non-binding inspiration**.

---

## 3. What the `learn-coding-agent` repo adds

The `learn-coding-agent` repo is useful because it acts as a **synthesis artifact**. It is not an official source; the repo itself says it is a learning/research repository compiled from public references and community discussions, focused especially on public information around Claude Code. That means it is most valuable as a structured map of harness mechanisms, not as proof of hidden product facts.

The strongest value from that repo is not the leak-adjacent gossip. It is the **shape** of the architecture it reconstructs:

- entry layer
- query engine
- tool system
- service layer
- state layer
- compaction
- permissions
- subagents
- lazy knowledge loading

The single best takeaway from the repo is its framing of **“12 progressive harness mechanisms”** — a useful ladder for how a toy coding loop evolves into a production harness.

---

## 4. Revised target architecture

We should explicitly design the harness as six layers.

### 4.1 Entry layer

Two entry modes:

- **interactive UI/CLI** for human-in-the-loop work
- **headless/SDK mode** for automation, integrations, tests, and subagents

This mirrors the community reconstruction in `learn-coding-agent`, where the entry layer flows into a shared query engine. That split is valuable and should be copied because it prevents the UI from owning core agent logic.

### 4.2 Query engine

The query engine should be the center of the harness.

Responsibilities:

- assemble prompt/context parts
- process user commands
- run the agent loop
- dispatch tools
- manage tool results
- compact context
- stream events/messages
- create checkpoints/transcripts

This should exist as a reusable library module, not only inside a CLI process.

### 4.3 Tool system

Tools should use a common interface, not ad hoc handlers.

Every tool should have:

- input validation
- permission check
- execution function
- read/write/destructive metadata
- concurrency safety metadata
- interrupt behavior
- output size and cost hints
- direct-call vs programmatic-call eligibility

### 4.4 Service layer

This layer owns integrations and side systems:

- model adapters
- prompt caching
- compaction service
- memory persistence
- git integration
- telemetry adapter
- MCP/OpenAPI/GraphQL adapters
- sandbox adapters
- transcript storage

### 4.5 State layer

Separate runtime state from raw transcript storage.

Suggested runtime state:

- current permission mode
- task/session id
- branch/worktree
- recently accessed files
- tool budget/cost stats
- active plan/todo
- checkpoint stack
- last compact summary
- subagent registry
- pending approvals

### 4.6 Artifact layer

The harness should intentionally write durable artifacts for future sessions:

- plan files
- todo files
- compact summaries
- memory updates
- diff summaries
- evaluation results
- checkpoint metadata

This is important because Anthropic’s long-running-agent guidance emphasizes leaving clear artifacts across many context windows.

---

## 5. The four-plane context system

This remains the most important architectural change.

### Plane A — Durable instruction plane

Purpose: stable rules and operating constraints.

Suggested files:

```text
.harness/
  instructions/
    AGENTS.md
    SAFETY.md
    REPO_RULES.md
    COMPACTION_RULES.md
```

Contents:

- coding standards
- architecture invariants
- approved commands
- review rules
- prohibited operations
- repository workflows
- compaction preservation rules

### Plane B — Durable project memory plane

Purpose: cross-session learnings.

Suggested structure:

```text
.harness/
  memory/
    MEMORY.md
    debugging.md
    commands.md
    architecture.md
    gotchas.md
    api-quirks.md
    decisions.md
```

Rules:

- `MEMORY.md` is an **index**, not a dump
- load only the compact index at session start
- load topic files on demand
- write memory only from explicit triggers or structured heuristics

### Plane C — Live session plane

Purpose: current task reasoning context.

Controls:

- automatic compaction thresholds
- manual reset
- manual compact
- transcript trimming
- stale tool-result clearing
- partial rewind/checkpoint restore

### Plane D — Ephemeral scratch plane

Purpose: exploratory isolation.

Used for:

- repo scouting
- code search
- API/data processing
- verifier passes
- speculative experiments
- subagent work

Outputs should be returned as structured summaries, not raw traces.

---

## 6. What to steal from the “12 progressive harness mechanisms”

The `learn-coding-agent` repo’s most useful abstraction is the ladder from “simple loop” to “production harness.” We should adopt that framing and turn it into our own roadmap.

### Stage 1 — The loop

Minimum agent loop:

- call model
- inspect stop reason
- run tool
- append result
- continue

This is necessary but insufficient.

### Stage 2 — Tool dispatch

Every new tool should plug into a registry without changing the main loop.

**Proposal:** build a tool registry and dispatch map early. No special-cased tool branches in the query loop.

### Stage 3 — Planning

Tasks drift without explicit structure.

**Proposal:** add a planning mode and persistent todo state. Plans should be explicit objects, not just paragraphs in the transcript.

### Stage 4 — Subagents

This is one of the highest-value additions.

**Proposal:** make subagents a built-in primitive with separate context, separate budgets, and summarized return artifacts.

### Stage 5 — Knowledge on demand

This lines up directly with Claude Code’s official memory model.

**Proposal:** load instruction/memory/skills lazily through files or memory tools rather than stuffing everything into the system prompt.

### Stage 6+ — The rest of the production ladder

Even where the repo’s names differ from official docs, the overall progression is good. We should explicitly add the following later-stage mechanisms:

- checkpointing and rewind
- hookable permission flow
- compaction and context editing
- deferred tool definitions
- stateful resumability
- model/surface specialization
- telemetry and evals
- enterprise policy overlays

---

## 7. Memory redesign in detail

### 7.1 What memory should store

Only store things with future value.

Store:

- recurring build/debug commands
- environment setup fixes
- project invariants
- API quirks
- repeated user corrections
- patterns that prevented repeated failures
- repo-specific review preferences

Do not store:

- raw stack traces unless canonicalized
- low-signal task history
- entire conversations
- random temporary assumptions
- huge tool outputs

### 7.2 Structured memory event schema

Instead of free-form notes only, each memory write should be tagged.

Suggested schema:

```json
{
  "type": "debugging_lesson | command | invariant | user_preference | architecture_decision | failure_pattern",
  "title": "short title",
  "summary": "one paragraph",
  "evidence": ["file/path", "command", "issue reference"],
  "scope": "repo | branch | user | subagent",
  "confidence": "high | medium | low",
  "last_verified": "ISO-8601"
}
```

### 7.3 Branch-aware memory overlay

Claude Code’s documented auto memory is per working tree. For our harness, I recommend a slightly richer model:

- repo-global base memory
- optional branch overlay
- optional task/session overlay

This avoids contaminating stable memory with experimental branch-specific findings.

### 7.4 Compaction contract

When compacting, always preserve:

- active plan
- files touched/read
- commands run + outcome
- unresolved issues
- risky assumptions
- last verifier status
- branch/worktree
- budget/cost status
- next recommended action

Everything else should be aggressively compressible.

---

## 8. Subagents: the most important feature after memory

Subagents are primarily a **context control mechanism**.

### 8.1 Required built-in subagents

#### Scout

- read-only
- cheap model
- fast grep/glob/read/search
- returns repo map and candidate files

#### Planner

- read-only
- stronger model
- creates plan, risk list, open questions, evaluation strategy

#### Implementer

- edit + shell access
- only agent allowed to mutate files by default
- bounded to approved workspace

#### Verifier

- read-only + narrow shell
- runs tests, static checks, diff review, edge-case review
- returns pass/fail with evidence

#### Tool-Orchestrator

- code execution + tool access
- no arbitrary repo edits
- specialized for programmatic tool calling and multi-step external workflows

### 8.2 Required subagent return format

Each subagent should return a compact structured artifact:

```json
{
  "summary": "...",
  "key_findings": ["..."],
  "files_examined": ["..."],
  "commands_run": ["..."],
  "risks": ["..."],
  "recommended_next_step": "..."
}
```

Do not append full subagent transcripts to the parent context.

### 8.3 Model routing

Do not use the same model for every subagent.

Suggested routing:

- Scout → cheap/fast model
- Planner → best reasoning model
- Implementer → strong coding model
- Verifier → strong but cheaper review model where possible
- Tool-Orchestrator → good reasoning + code execution compatibility

---

## 9. Tool system redesign

The `learn-coding-agent` repo is very useful here because its reconstructed tool interface is the right abstraction shape even if some specifics are community-derived.

### 9.1 Required tool metadata

Each tool definition should include:

```ts
interface HarnessTool {
  name: string;
  description: string;
  inputSchema: JSONSchema;
  outputSchema?: JSONSchema;
  validateInput(args): ValidationResult;
  checkPermissions(ctx, args): PermissionDecision;
  call(ctx, args): Promise<ToolResult>;
  isEnabled?(ctx): boolean;
  isReadOnly?: boolean;
  isDestructive?: boolean;
  isConcurrencySafe?: boolean;
  interruptBehavior?: "cancel" | "block" | "continue";
  maxResultBytes?: number;
  costClass?: "low" | "medium" | "high";
  allowedCallers?: ["direct"] | ["code_execution"] | ["direct", "code_execution"];
}
```

### 9.2 Tool execution pipeline

Recommended flow:

1. validate input
2. classify tool risk
3. evaluate permission policy
4. optionally run pre-tool hooks
5. execute tool
6. summarize/truncate output if needed
7. optionally run post-tool hooks
8. append structured result to transcript state
9. decide whether to keep, summarize, or evict result from live context

### 9.3 Tool result handling

Do not blindly paste full tool output back into the model.

For large outputs, use one of:

- summarize before insertion
- write to file and reference path
- keep in out-of-band artifact store
- route through programmatic tool calling so only filtered output reaches the model

---

## 10. Deferred tools, tool search, and context economy

This is one of the most directly actionable Claude Code lessons.

### 10.1 Problem

If the harness exposes too many tools at once, the model pays context cost for tools it never uses.

### 10.2 Proposal

Split tools into three buckets:

#### Hot tools

Always loaded:

- read
- grep/search
- edit/write
- diff
- shell
- plan/todo
- checkpoint

#### Warm tools

Listed by name/summary only until selected:

- git helpers
- issue tracker tools
- deployment tools
- repo analyzers
- docs lookup tools

#### Cold tools

Discovered only via tool search:

- MCP long-tail tools
- external APIs
- organization-specific integrations

### 10.3 Add tool search

When tool count exceeds a threshold, expose a search/retrieval mechanism for tools instead of loading all definitions.

### 10.4 Add prompt caching for tools

Stable tool definitions and system components should be cached so long sessions and repeated turns do not repeatedly pay the same token tax.

---

## 11. Programmatic tool calling: the biggest architecture addition

This should become a first-class feature of our harness.

### 11.1 Why it matters

Ordinary tool calling is too expensive for workflows like:

- call API A → filter
- call API B for each item
- aggregate
- sort
- enrich
- summarize

That pattern bloats the transcript and creates extra model round-trips.

### 11.2 Proposed model

Add a **code execution environment** that can call selected tools programmatically.

The model should be able to write Python or TypeScript code that:

- loops over many items
- calls tools repeatedly
- applies local filtering/aggregation
- writes intermediate artifacts to sandbox files
- returns only the final condensed result to the model

### 11.3 Direct-call vs code-call split

Each tool should declare whether it is meant for:

- direct model invocation
- code-execution-only invocation
- both

However, default to **one preferred mode** per tool to reduce ambiguity.

### 11.4 Best-fit use cases

Use programmatic tool calling for:

- 3+ dependent tool calls
- large result filtering
- batch endpoint checks
- repetitive data enrichment
- conditional branching over tool results
- workflows where intermediate outputs should not enter the main context

Do **not** use it for:

- one fast tool call
- interactions needing immediate user confirmation each step
- tiny outputs where code-execution overhead dominates

### 11.5 Proposed implementation surfaces

Surface A: **managed sandbox execution**  
Good for safer deployment.

Surface B: **local client-side execution**  
Good for local-first power users, but higher risk.

Surface C: **hybrid orchestration sandbox**  
Preferred long-term direction: local repo work in shell/container, external orchestration in managed code-execution sandbox.

---

## 12. Execution model: where `just-bash` fits

`just-bash` is useful, but only as one execution surface.

### 12.1 What it is good for

- safe-ish repo exploration
- read/search/transform flows
- ephemeral eval sandboxes
- reproducible shell behavior
- portable agent skills
- bounded scripting with restricted filesystem/network

### 12.2 Why it is not enough as the main runtime

Its documented constraints make it a poor sole runtime for a full coding harness:

- beta software
- no VM isolation
- `exec()` resets shell state each call
- limited surface compared with a real dev environment
- unsuitable as the only execution backend for arbitrary local engineering tasks

### 12.3 Recommended usage

Adopt a **three-surface execution model**:

#### Surface 1 — Real shell/container runtime

For:

- actual repo work
- builds/tests/lint
- package managers
- git workflows
- realistic local development

#### Surface 2 — `just-bash` virtual shell

For:

- exploratory search
- low-risk transformations
- eval environments
- safe reproduction
- small automations and skills

#### Surface 3 — Typed code execution runtime

For:

- programmatic tool calling
- large-scale orchestration
- API/data workflows
- filtered multi-step external operations

This is a much better fit than trying to force all work through bash.

---

## 13. Where Executor fits

Executor should not be the local coding runtime. It fits best as an **integration and control plane**.

### Good fit

- approval gates
- workspace policy
- multi-tenant roles
- external tool discovery
- MCP/OpenAPI/GraphQL integration
- typed task execution

### Weak fit

- full local repo semantics
- arbitrary dev environment behavior
- interactive local engineering loop as the primary runtime

### Recommended role in our architecture

Use Executor-like ideas for:

- organization-wide integration catalog
- approval workflows
- role-based access control
- audit trails
- shared credentials and workspace policy

Not for:

- the core local code-edit/test loop

---

## 14. Permissions, hooks, and governance

This is where most open harnesses stay too shallow.

### 14.1 Permission model

Required modes:

- **plan/read-only**
- **supervised edit**
- **supervised full**
- **auto mode** with independent risk control

### 14.2 Permission rules

Support:

- allow
- ask
- deny
- pattern-based matching
- scope layering (global/project/user/session)

### 14.3 Hooks

Add deterministic hooks at minimum for:

- pre-tool
- post-tool
- pre-commit
- post-edit
- subagent-start
- subagent-stop
- compact-start
- compact-finish
- session-end

### 14.4 What hooks should do

Examples:

- block writes in protected paths
- force lint/tests after edits
- redact secrets from tool output
- summarize giant results before insertion
- attach extra context for certain tools
- enforce commit-message policy
- snapshot artifacts before destructive operations

### 14.5 Auto mode

Do not make auto mode just “stop asking.”

Auto mode should:

- use tighter permission policy
- ignore broad dangerous allow rules
- maintain deny/retry thresholds
- route high-risk operations back to manual approval
- keep transcript artifacts for post-hoc review

---

## 15. State, checkpoints, and resumability

A strong harness must behave well across interrupted or multi-session work.

### 15.1 Required checkpoint artifact

```json
{
  "session_id": "...",
  "task_id": "...",
  "branch": "...",
  "worktree": "...",
  "active_plan": {...},
  "files_touched": ["..."],
  "last_compact_summary": "...",
  "open_risks": ["..."],
  "next_step": "...",
  "timestamp": "..."
}
```

### 15.2 Resume behavior

When resuming a task, the harness should reconstruct context from:

1. instructions plane
2. memory index + relevant topic files
3. checkpoint summary
4. recent files
5. only then selected transcript fragments

This is far better than replaying a giant conversation.

---

## 16. Telemetry and privacy posture

The `learn-coding-agent` repo spends a lot of time on telemetry, remote settings, and internal-vs-external behavior. Treat its specifics as secondary, but the category is important.

### Proposal

Build explicit telemetry modes from the beginning:

- off / local-only
- minimal product telemetry
- full debug telemetry

And make all of the following explicit:

- what events are recorded
- whether tool args are stored
- whether tool outputs are stored
- whether repo identifiers are hashed
- retention duration
- local redaction controls

### Non-negotiable rule

Do not silently collect detailed tool inputs/outputs in local mode.

### Enterprise extension

For org-managed deployments, support central policy and remote config — but only with visibility and auditability.

---

## 17. Packaging and plugin model

A good long-term direction is to package harness extensions as reusable bundles.

A plugin should be able to contain:

- skills
- hooks
- subagents
- tool definitions
- MCP server definitions
- instruction fragments
- evaluation configs

This lets teams reuse harness behavior across repos without duplicating configuration.

---

## 18. Revised implementation roadmap

### Phase 1 — Foundation (highest ROI)

Build:

- query engine library
- tool registry
- four-plane context system
- `AGENTS.md` + memory index system
- basic compaction
- checkpoint artifacts
- plan/todo state

### Phase 2 — Context hygiene

Build:

- Scout / Planner / Implementer / Verifier subagents
- structured subagent returns
- memory write heuristics
- stale tool-result eviction
- deferred file/topic loading

### Phase 3 — Tool economy

Build:

- hot/warm/cold tool buckets
- tool search
- prompt caching for system/tool defs
- result summarization limits
- output/file indirection for huge results

### Phase 4 — Orchestration

Build:

- code execution sandbox
- `allowed_callers`-style tool modes
- batch workflows
- programmatic tool calling
- structured output contracts for programmatic tools

### Phase 5 — Governance

Build:

- permission modes
- allow/ask/deny rules
- hooks
- approval flows
- audit logs
- protected path policies

### Phase 6 — Optional advanced surfaces

Build:

- `just-bash` integration for exploration/evals
- Executor-like integration plane
- plugin packaging
- org-managed settings
- stronger auto mode

---

## 19. Concrete file layout proposal

```text
.harness/
  instructions/
    AGENTS.md
    SAFETY.md
    REPO_RULES.md
    COMPACTION_RULES.md
  memory/
    MEMORY.md
    architecture.md
    debugging.md
    commands.md
    gotchas.md
    api-quirks.md
    decisions.md
  agents/
    scout.yaml
    planner.yaml
    implementer.yaml
    verifier.yaml
    tool-orchestrator.yaml
  tools/
    registry.json
    policies.json
    search-index.json
  checkpoints/
    current.json
    archive/
  artifacts/
    plans/
    todos/
    summaries/
    evals/
  hooks/
    pre_tool/
    post_tool/
    post_edit/
    pre_commit/
    compact/
  settings/
    user.json
    project.json
    managed.json
```

---

## 20. Evaluation plan

Do not ship this as intuition only. Add evals from the beginning.

### 20.1 Bench categories

- repo navigation
- small code edit
- multi-file refactor
- bug fix
- flaky test investigation
- API/data orchestration
- long-horizon interrupted task resume
- protected-path safety
- context overflow survival

### 20.2 Measure

- task completion rate
- number of model turns
- token use
- wall-clock latency
- tool-call count
- compaction count
- verifier pass rate
- unsafe action attempts blocked
- resume success rate

### 20.3 Specific hypotheses to test

1. Subagents reduce token growth and improve completion rate on complex tasks.
2. Memory index + topic files outperform giant persistent notes.
3. Programmatic tool calling improves token cost and latency on multi-step API/data tasks.
4. Deferred tool loading improves large-tool-catalog performance.
5. `just-bash` improves eval safety/reproducibility for exploration tasks but should not replace real shell for repo work.

---

## 21. What not to copy

Do **not** copy blindly:

- opaque telemetry defaults
- hidden/undocumented modes
- unclear remote overrides
- internal-vs-external product divergence
- deceptive authorship behavior
- broad shell allow rules in autonomy mode
- giant system prompts that try to encode everything

The goal is a strong harness, not a mysterious one.

---

## 22. Final decision summary

### Adopt now

- four-plane context system
- tool registry + metadata
- structured planning/todo state
- checkpoint artifacts
- compact memory index + topic files
- subagents with isolated context
- phased permission and hook model

### Add next

- deferred tool loading
- tool search
- programmatic tool calling
- structured programmatic tool contracts
- typed code-execution sandbox

### Add selectively

- `just-bash` as bounded exploration/eval surface
- Executor-like control plane features for shared integrations and approvals
- managed org policy features

### Avoid

- using bash as the only substrate
- overloading the model context with every tool/file/note
- treating unofficial leak artifacts as architecture truth

---

## 23. References used for this proposal

### Primary sources

- Claude Code Docs — Memory
- Claude Code Docs — Permissions / Settings / Hooks / Subagents / MCP / Costs / Permission Modes
- Claude API Docs — Programmatic tool calling
- Anthropic Engineering — Effective context engineering for AI agents
- Anthropic Engineering — Effective harnesses for long-running agents
- Anthropic Engineering — Advanced tool use / code execution with MCP / writing tools for agents
- Vercel `just-bash` README / docs
- Executor official docs

### Secondary synthesis source

- `sanbuphy/learn-coding-agent` — used as a structured synthesis of harness mechanisms and reconstructed architecture shape, not as sole authority

