# AutoCode Internal-First Orchestration Research

> Date: 2026-03-30
> Goal: Define what AutoCode should perfect in its own agent system before building external harness orchestration for Claude Code, Codex, OpenCode, and similar tools.
> Scope: local codebase assessment plus current official docs for Codex, Claude Code, and OpenCode, with T3 Code used as an implementation reference for runtime-event normalization.

---

## 1. Executive Summary

AutoCode should **not** start by building a thin wrapper around Claude Code, Codex, and OpenCode.

It should first finish becoming a **real internal orchestrator**:

1. one canonical team runtime
2. one canonical message/task/event model
3. one canonical delegation and budget policy
4. one canonical safety and quality-gate layer
5. one canonical evaluation story

Only after that should AutoCode add external harness adapters.

The reason is straightforward:

- The repo already has meaningful internal orchestration primitives.
- Those primitives are not yet mature enough to serve as a universal control plane.
- External orchestration without a finished internal control plane would create three problems at once:
  - duplicated coordination logic
  - incompatible agent semantics across tools
  - weak observability and safety boundaries

The right architecture is:

- **AutoCode owns the control plane**
- **external tools remain worker runtimes**
- **all tasking, messaging, approvals, budgets, and artifacts flow through AutoCode**

T3 Code is useful as a control-plane reference, but not as the target product shape. It is closer to a **multi-provider session server and GUI** than a universal agent-team orchestrator.

---

## 2. Research Method

This note combines:

- local repository inspection
- existing local research docs
- current official documentation

Local implementation reviewed:

- `autocode/src/autocode/agent/orchestrator.py`
- `autocode/src/autocode/agent/bus.py`
- `autocode/src/autocode/agent/delegation.py`
- `autocode/src/autocode/agent/subagent.py`
- `autocode/src/autocode/agent/subagent_tools.py`
- `autocode/src/autocode/agent/worktree.py`
- `autocode/src/autocode/agent/policy_router.py`
- `autocode/src/autocode/agent/sop_runner.py`
- `autocode/src/autocode/session/task_store.py`
- `autocode/src/autocode/external/mcp_server.py`
- `autocode/src/autocode/external/tracker.py`
- `autocode/src/autocode/external/config_merge.py`
- `docs/plan/phase5-agent-teams.md`
- `docs/research/phase5-agent-teams-research.md`
- `docs/research/multi-agent-landscape-2026.md`

Primary external references:

- Codex Subagents
  - https://developers.openai.com/codex/subagents
- Codex Agent Approvals & Security
  - https://developers.openai.com/codex/agent-approvals-security
- Codex Config Reference
  - https://developers.openai.com/codex/config-reference
- Claude Code Agent Teams
  - https://code.claude.com/docs/en/agent-teams
- Claude Code Hooks
  - https://code.claude.com/docs/en/hooks
- OpenCode Agents
  - https://opencode.ai/docs/agents
- OpenCode Permissions
  - https://opencode.ai/docs/permissions

Implementation reference corpus:

- `research-components/t3code`
- `research-components/openai-codex`
- `research-components/opencode`
- `research-components/claude-code`

---

## 3. What AutoCode Already Has

AutoCode already contains a non-trivial internal orchestration substrate.

### 3.1 Present capabilities

| Capability | Evidence | Status |
|---|---|---|
| Typed inter-agent messaging | `autocode/src/autocode/agent/bus.py` | Present |
| Task DAG / dependencies | `autocode/src/autocode/session/task_store.py` | Present |
| Policy-based routing across intelligence layers | `autocode/src/autocode/agent/policy_router.py` | Present |
| SOP / pipeline execution | `autocode/src/autocode/agent/sop_runner.py` | Present |
| Subagent lifecycle management | `autocode/src/autocode/agent/subagent.py` | Present |
| Delegation policy with depth/thread caps | `autocode/src/autocode/agent/delegation.py` | Present |
| Subagent tool surface | `autocode/src/autocode/agent/subagent_tools.py` | Present |
| Worktree isolation substrate | `autocode/src/autocode/agent/worktree.py` | Present |
| External tool discovery | `autocode/src/autocode/external/tracker.py` | Present |
| External config generation | `autocode/src/autocode/external/config_merge.py` | Present |
| MCP exposure of AutoCode tools | `autocode/src/autocode/external/mcp_server.py` | Present |

### 3.2 What the current code means

The repo is **not** starting from scratch.

It already has the main building blocks needed for:

- a lead agent
- worker agents
- typed messages
- shared task state
- capability restrictions
- bounded delegation
- worktree isolation
- external discovery/config scaffolding

That is enough to justify an internal-first strategy.

---

## 4. What Is Still Missing Internally

The problem is not lack of primitives. The problem is that several primitives are still **substrates**, not a finished control plane.

### 4.1 The current bus is not yet a production mailbox

`AgentBus` is described as the runtime equivalent of `AGENTS_CONVERSATION.MD`, but in practice it is still an **in-memory message list plus subscriptions**:

- no persistence layer
- no ack/claim protocol
- no delivery guarantees
- no per-agent mailbox state
- no message lifecycle beyond append/read

Evidence:

- `autocode/src/autocode/agent/bus.py`
- `get_pending()` returns messages but does not mark them processed
- `subscribe()` is callback-based and process-local

Implication:

AutoCode does not yet have a real shared mailbox like Claude agent teams.

### 4.2 The orchestrator exists, but is not the product control plane

`Orchestrator` exists as a clean integration layer, but it is not clearly the main runtime path.

Evidence:

- `autocode/src/autocode/agent/orchestrator.py`
- repo-wide search shows `Orchestrator()` usage is essentially limited to unit tests
- the live product paths still center on `AgentLoop` via:
  - `autocode/src/autocode/inline/app.py`
  - `autocode/src/autocode/backend/server.py`
  - `autocode/src/autocode/tui/app.py`

Implication:

The internal control plane is conceptually present, but not yet the dominant execution model.

### 4.3 TaskStore is a session task DAG, not yet a team task board

`TaskStore` provides useful DAG semantics, but it is still closer to session-local task bookkeeping than a true team runtime task board.

It does not yet define:

- teammate assignment semantics
- claim/lease semantics
- ownership transfer
- work queue policies
- artifact/result attachment conventions
- mailbox-task linkage

Evidence:

- `autocode/src/autocode/session/task_store.py`

Implication:

This is a solid base, but not yet the equivalent of Claude’s shared team task list.

### 4.4 Subagents are still mostly “spawn worker and poll”

Subagent infrastructure is meaningful, but the runtime model is still narrow:

- flat hierarchy
- background execution
- check/cancel/list tool surface
- bounded concurrency

That is useful, but it is not the same as a persistent team runtime with direct teammate communication.

Evidence:

- `autocode/src/autocode/agent/subagent.py`
- `autocode/src/autocode/agent/subagent_tools.py`

Implication:

AutoCode currently has **worker spawning**, not full **team semantics**.

### 4.5 External integration is mostly discovery + configuration + read-only MCP

Current external pieces are still preparatory:

- `ExternalToolTracker` discovers binaries and coarse capabilities
- `config_merge.py` writes managed config sections
- `MCPServer` exposes read-only tools

Evidence:

- `autocode/src/autocode/external/tracker.py`
- `autocode/src/autocode/external/config_merge.py`
- `autocode/src/autocode/external/mcp_server.py`

Implication:

AutoCode is not yet externally orchestrating Claude/Codex/OpenCode. It is preparing for that stage.

### 4.6 Canonical runtime events are missing

The repo has messages, tasks, and agent loops, but not yet one canonical event model that spans:

- internal lead/worker execution
- approvals
- tool lifecycle
- task lifecycle
- model/runtime events
- external harness events

Implication:

Without a canonical event schema, external harness orchestration will become adapter-specific glue instead of a platform.

---

## 5. What the External Systems Teach

## 5.1 Codex: bounded subagents and hard security matter

Codex’s strongest lessons are not “copy the UI” or “copy the workflow.” They are:

- subagents are explicit and parallel-capable
- subagents inherit sandbox/approval policy
- orchestration is bounded by `agents.max_depth` and `agents.max_threads`
- sandbox and approval policy are first-class runtime concerns

Useful takeaways for AutoCode:

1. delegation should stay bounded and explicit
2. security policy must be inherited consistently by spawned workers
3. depth/thread caps belong in the control plane, not just in prompt guidance

This aligns directly with:

- `autocode/src/autocode/agent/delegation.py`
- `autocode/src/autocode/agent/sandbox.py`

What to borrow:

- stronger policy inheritance
- clearer hard caps
- better approval/sandbox exposure in runtime state

What not to copy:

- Codex is optimized for Codex’s own runtime and approval model, not for being a broker across heterogeneous external harnesses

## 5.2 Claude Code: team semantics are more than subagents

Claude’s agent teams are the most important benchmark for internal team behavior.

The key differences from plain subagents are:

- a lead plus teammates
- a shared task list
- a mailbox / inter-agent communication model
- direct teammate interaction
- quality gates via hooks around team lifecycle events

The most important lesson:

**team semantics are a separate runtime layer**, not just “spawn more subagents.”

Useful takeaways for AutoCode:

1. build a real team runtime, not just richer worker spawning
2. model teammate communication explicitly
3. treat task assignment and claim semantics as first-class
4. expose lifecycle hooks for quality gates

This is the best reference for what AutoCode should perfect internally before touching external orchestration.

## 5.3 OpenCode: agent modes and hidden internal agents are good control-plane ideas

OpenCode’s useful ideas are:

- primary vs subagent distinctions
- hidden/internal agents
- per-agent modes
- task permissions

Useful takeaways for AutoCode:

1. distinguish product-facing agents from internal service agents
2. keep compaction/title/summary agents internal
3. enforce per-agent capability and permission policy centrally

This aligns with:

- `autocode/src/autocode/agent/delegation.py`

What to borrow:

- explicit mode taxonomy
- central permission policy
- hidden/internal agent model

## 5.4 T3 Code: normalize runtime events, but do not mistake that for orchestration

T3 Code is useful because it has a serious control-plane layer:

- provider sessions
- provider runtime event contracts
- orchestration event ingestion/projection
- server-mediated session control

Evidence:

- `research-components/t3code/AGENTS.md`
- `research-components/t3code/apps/server/src/orchestration/Layers/OrchestrationEngine.ts`
- `research-components/t3code/apps/server/src/orchestration/Layers/ProviderRuntimeIngestion.ts`

The key lesson is:

**normalize external runtime events into a canonical orchestration domain model**.

But T3 Code is still mostly:

- a provider session server
- a runtime-event normalizer
- a UI control surface

It is not the same as a universal peer-agent orchestrator that lets multiple external harnesses collaborate through a shared AutoCode-owned control plane.

So T3 Code is a good reference for:

- event normalization
- control-plane persistence
- session projection

It is not the architecture AutoCode should copy end-to-end.

---

## 6. Internal-First Decision

AutoCode should perfect the following **before** implementing external harness orchestration.

### 6.1 Required internal milestones

#### A. Canonical Team Runtime

Build a real team runtime on top of current primitives:

- persistent mailbox
- task claim/lease semantics
- assignment and ownership
- teammate lifecycle
- artifact/result linkage
- direct teammate-to-teammate messaging through the broker

This should extend the current:

- `AgentBus`
- `TaskStore`
- `SubagentManager`

It should not be built as ad hoc logic in each adapter.

#### B. Canonical Event Model

Define one event schema that covers:

- session started/resumed/stopped
- turn started/completed/failed
- approval requested/resolved
- tool started/completed/errored
- task created/claimed/completed/blocked
- mailbox message sent/received/acknowledged
- artifact published/consumed
- subagent spawned/completed/cancelled

This is the biggest prerequisite for any future Claude/Codex/OpenCode adapters.

#### C. Orchestrator on the Main Product Path

Move from “orchestrator exists” to “orchestrator is the runtime control plane.”

That means:

- the live user path should run through a real orchestrator layer
- `AgentLoop` should be a worker primitive inside the control plane
- team/delegation/task semantics should not live as scattered side features

#### D. Budget / Safety / Governance Layer

Before external orchestration, AutoCode needs one unified policy surface for:

- delegation depth
- active worker count
- total task budget
- token budget
- approval policy inheritance
- sandbox policy inheritance
- worktree/isolation policy

Otherwise each external harness adapter will invent its own rules.

#### E. Quality Gates and Evaluation

Before external harnesses, AutoCode should be able to evaluate:

- internal single-agent quality
- internal subagent quality
- internal team coordination quality
- routing regret
- delegation usefulness
- message overhead
- budget adherence
- failure recovery

If AutoCode cannot measure its own internal team runtime, it will not be able to judge whether external orchestration improved or degraded outcomes.

---

## 7. What Should Be Deferred Until After Internal Perfection

These should come **after** the internal runtime is mature:

1. live Claude Code team orchestration
2. live Codex session orchestration
3. live OpenCode session orchestration
4. cross-harness mailbox bridging
5. bidirectional orchestration where external tools can invoke AutoCode as a peer
6. remote multi-machine agent federation

These are all valid goals, but they belong to the **adapter stage**, not the **control-plane-definition stage**.

---

## 8. Recommended Architecture for the External Stage

Once the internal runtime is mature, the external architecture should look like this:

```text
User
  |
AutoCode Control Plane
  |- Team Runtime
  |- Mailbox
  |- Task Board
  |- Budget / Approval / Sandbox Policy
  |- Artifact Store
  |- Event Store / Projections
  |
  +- HarnessAdapter: Claude Code
  +- HarnessAdapter: Codex
  +- HarnessAdapter: OpenCode
  +- HarnessAdapter: AutoCode-native
```

Rules:

1. external harnesses do not coordinate directly outside the broker
2. AutoCode owns the task graph and mailbox
3. adapters translate native runtime events into AutoCode events
4. adapters translate AutoCode commands into native tool actions
5. all external runtime capabilities are version-probed and fail-closed

This is how AutoCode becomes a platform instead of a thin multi-provider UI.

---

## 9. Concrete Repo Priorities

If work starts tomorrow, the next internal priorities should be:

### Priority 0

- define canonical orchestration event schema
- decide mailbox persistence model
- decide team task-board semantics

### Priority 1

- promote `Orchestrator` from test/demo integration layer to real product runtime
- unify lead/worker lifecycle through one control-plane entrypoint
- persist mailbox and task state

### Priority 2

- add explicit internal service-agent roles
- finish budget, delegation, and approval inheritance rules
- add team-runtime evals and failure-injection tests

### Priority 3

- implement the first external adapter, likely Codex-first or AutoCode-native-first
- normalize external session events into the canonical event schema
- keep external orchestration behind a capability gate until stable

---

## 10. Anti-Patterns to Avoid

1. **Do not build a UI-first wrapper and call it orchestration.**
   - That is the trap T3 Code shows.

2. **Do not let each external adapter invent its own team semantics.**
   - The team model must be AutoCode-owned.

3. **Do not use regex scraping of CLI text as the main integration path.**
   - Prefer official config surfaces, MCP, SDK/runtime events, or structured output.

4. **Do not collapse mailbox, task board, and event log into one loose JSON blob.**
   - Those are separate control-plane concerns.

5. **Do not ship external orchestration before measuring internal delegation quality.**
   - Otherwise failures will be impossible to localize.

---

## 11. Final Recommendation

The right sequence is:

1. **Perfect AutoCode’s own agent system**
   - finish team runtime semantics
   - finish event model
   - finish governance and evals
   - make the orchestrator the actual runtime control plane

2. **Then add external harness orchestration**
   - one adapter at a time
   - canonical event translation
   - strict capability probes
   - fail-closed behavior

3. **Then, and only then, consider broader “orchestrate everything” platform UX**
   - mixed tool teams
   - bidirectional orchestration
   - remote/federated teams

That sequence fits both the local codebase reality and the strongest lessons from Codex, Claude Code, OpenCode, and T3 Code.

---

## 12. Source List

### Official docs

- Codex Subagents
  - https://developers.openai.com/codex/subagents
- Codex Agent Approvals & Security
  - https://developers.openai.com/codex/agent-approvals-security
- Codex Config Reference
  - https://developers.openai.com/codex/config-reference
- Claude Code Agent Teams
  - https://code.claude.com/docs/en/agent-teams
- Claude Code Hooks
  - https://code.claude.com/docs/en/hooks
- OpenCode Agents
  - https://opencode.ai/docs/agents
- OpenCode Permissions
  - https://opencode.ai/docs/permissions

### Local code and local research

- `docs/plan/phase5-agent-teams.md`
- `docs/research/phase5-agent-teams-research.md`
- `docs/research/multi-agent-landscape-2026.md`
- `research-components/t3code/AGENTS.md`
- `research-components/t3code/apps/server/src/orchestration/Layers/OrchestrationEngine.ts`
- `research-components/t3code/apps/server/src/orchestration/Layers/ProviderRuntimeIngestion.ts`
- `autocode/src/autocode/agent/orchestrator.py`
- `autocode/src/autocode/agent/bus.py`
- `autocode/src/autocode/agent/delegation.py`
- `autocode/src/autocode/agent/subagent.py`
- `autocode/src/autocode/session/task_store.py`
- `autocode/src/autocode/external/tracker.py`
- `autocode/src/autocode/external/config_merge.py`
- `autocode/src/autocode/external/mcp_server.py`
