# Phase 5 Agent Teams Research

> Created: 2026-02-17
> Scope: Validate current (2026) patterns for subagents, agent teams, model delegation, and A2A interoperability before Phase 5 implementation.
> Related plan: `docs/plan/phase5-agent-teams.md`

---

## 1. Executive Summary

Yes, we can implement Claude/OpenCode-style delegation in AutoCode, but with local-hardware constraints:

1. Keep a single lead agent and a small teammate pool (2-4 active teammates), not large swarms.
2. Use per-agent model selection (for quality/cost control), with strict scheduler and budget gates.
3. Add a first-class team runtime (mailbox + shared task board), not just one-shot subagents.
4. Treat A2A as an adapter layer after internal team semantics are stable.

Most important update: Claude Code now has an experimental Agent Teams feature with lead + teammates, shared mailbox, and shared task list. This changes the benchmark target for our Phase 5 design.

---

## 2. Source List (Primary First)

### 2.1 High Confidence (official docs/specs)

- Claude Code docs: Subagents
  - https://docs.claude.com/en/docs/claude-code/sub-agents
- Claude Code docs: Agent teams overview/setup
  - https://docs.claude.com/en/docs/claude-code/team
  - https://docs.claude.com/en/docs/claude-code/team-config
- Claude Code docs: Run agent teams (experimental)
  - https://docs.claude.com/en/docs/claude-code/run-agent-teams
- Claude Code docs: Agent team token costs
  - https://docs.claude.com/en/docs/claude-code/agent-team-costs
- OpenCode docs: Agents
  - https://opencode.ai/docs/agents/
- A2A protocol spec v0.3
  - https://a2a-protocol.org/latest/specification/
- A2A roadmap/near-term notes
  - https://a2a-protocol.org/latest/roadmap/

### 2.2 Medium Confidence (use for color, not core decisions)

- OpenCode OSS discussions/issues and community posts (delegation UX edge cases)

---

## 3. Findings

### 3.1 Claude Subagents (current state)

Observed in docs:

1. Subagents are first-class specialized agents with distinct prompts/tool permissions.
2. Custom subagents can specify a model override; default behavior is to inherit the parent model.
3. Docs explicitly position subagents for context isolation and repeated workflows.
4. Cost guidance explicitly suggests cheaper models for subagent tasks when appropriate.

Implication for AutoCode:

- Our current `SubagentType` model should evolve to card-based identity (`AgentCard`) with explicit model/tool policy.
- We should support model inheritance plus explicit per-agent overrides.

### 3.2 Claude Agent Teams (new benchmark target)

Observed in docs:

1. Agent Teams is an experimental feature.
2. Team structure: one lead agent plus multiple teammates (up to 10 in docs).
3. Collaboration primitives: shared mailbox and shared task list.
4. Teammates can run in parallel.
5. Guardrails/limits: no nested teammate delegation, partial context sharing, one task at a time per teammate, and operational limitations around approvals/permissions and review UX.

Implication for AutoCode:

- Teams are not just "spawn background subagent"; they require persistent team state and inter-agent communication.
- We should start with an intentionally narrower v1: no nested delegation, no cross-session teammate memory, deterministic coordinator.

### 3.3 Claude Team Cost Behavior

Observed in docs:

1. Team runs increase token usage materially versus single-agent runs.
2. Published examples show substantial multiplier effects, especially in plan mode.

Implication for AutoCode:

- Phase 5 must include cost governance as a core feature, not an optimization backlog item.
- We need hard budget controls (max teammates, max delegation depth, max delegation per turn, token caps by role).

### 3.4 OpenCode Agent Pattern

Observed in docs:

1. OpenCode exposes built-in primary agents and subagents.
2. Task-style delegation supports background execution.
3. Permission policy is configurable (including task/subagent permissions).
4. Agent definitions can be customized locally.

Implication for AutoCode:

- Good reference for permission gating and configurable delegation policy.
- We should preserve our existing approval model while adding team-level policy controls.

### 3.5 A2A v0.3 Contract Details (important corrections)

Observed in spec/roadmap:

1. Discovery metadata path in v0.3 uses `/.well-known/agent-card.json`.
2. Task state model includes: `submitted`, `working`, `input-required`, `completed`, `canceled`, `failed`, `rejected`, `auth-required`, `unknown`.
3. JSON-RPC method family includes `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`.
4. Roadmap explicitly calls out ongoing evolution to v1.0 with no planned breaking changes before v1.

Implication for AutoCode:

- Existing Phase 5 draft references to `agent.json` and older task assumptions should be corrected.
- Build an internal protocol first, then map to A2A via an adapter boundary.

---

## 4. Gap Assessment Against Current AutoCode

Current strengths (already in code):

1. `LLMScheduler` for serialized LLM access with priority.
2. `SubagentLoop` and `SubagentManager` for restricted background execution.
3. `TaskStore` with DAG dependencies and status tracking.
4. Plan mode and capability-based tool restrictions.

Missing for true "team" semantics:

1. Agent identity model (`AgentCard`) persisted and queryable.
2. Team-level mailbox/message threading between agents.
3. Shared team task board separate from ad-hoc tool-driven tasks.
4. Per-agent model registry/routing (single provider assumption still dominant).
5. Cost governance primitives (token budgets, delegation quotas, teammate limits).
6. A2A adapter layer with v0.3-compliant mappings.

---

## 5. Design Recommendations (for Phase 5)

1. Build internal Team Runtime first:
   - `AgentRegistry`, `ProviderRegistry`, `TeamRuntime`, `TeamMailbox`, `TeamTaskBoard`.
2. Use deterministic orchestration for v1:
   - lead agent decides when to delegate based on policy and budget.
3. Add model routing with explicit role tiers:
   - scout/research: low-cost model or no-LLM path when possible,
   - worker/editor: L3 constrained model,
   - lead/reviewer: L4 model.
4. Add cost controls before broad rollout:
   - max active teammates, per-turn delegation cap, token ceilings, cooldowns.
5. Ship A2A only after internal API stabilizes:
   - adapter maps internal messages/tasks/cards to v0.3 surface.

---

## 6. What This Means for the User Question

User question: "Claude and OpenCode use subagents and model delegation to save cost; can we do that, including teams?"

Answer: Yes.

- We already have the subagent substrate.
- We need to add team runtime semantics and multi-model routing.
- We should intentionally constrain concurrency and delegation depth for local hardware reliability.
- We can align with A2A for interoperability, but only as a second step after internal team protocol maturity.

