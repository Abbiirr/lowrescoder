# North Star — AutoCode

> The durable project vision. These statements are **user-approved invariants** that guide every decision in this repo. They change only when the user explicitly authorizes a change. Agents must not deviate without user authorization.
>
> This document is **deliberately tech-agnostic.** Specific implementation choices (languages, libraries, model names, package managers) live in `CLAUDE.md` and `PLAN.md` so they can evolve without rewriting the vision.

---

## Mission

**AutoCode** is an edge-native AI coding assistant.

- Local-first
- Deterministic-first
- Consumer-hardware target (8 GB VRAM, 16 GB RAM)
- Classical deterministic AI as the primary intelligence layer; LLMs only when nothing else can solve it

**This is the opposite of how most AI coders work.** That contrast is the product.

---

## Project Invariants

These decisions are **locked**.

1. **LLM as last resort** — Deterministic tools first (lexical/AST analysis, static analysis, language-server queries). LLM only when they can't solve it.
2. **4-Layer Architecture** — Layer 1 (deterministic) → Layer 2 (retrieval) → Layer 3 (constrained generation) → Layer 4 (full reasoning). Every feature declares which tier it lives in; an L2 feature must not secretly escalate to L4 for convenience.
3. **Edge-native** — All intelligence runs on the user's machine. No cloud dependency by default.
4. **Consumer hardware target** — 8 GB VRAM, 16 GB RAM. No 70B+ parameter models required.
5. **Docs are the single source of truth** — If docs say X and code does Y, the docs are wrong and must be fixed before continuing.

---

## The 4-Layer Intelligence Model

Invariant #2 unpacked. Latency and token budgets below are the target contract each layer must hit.

| Layer | Purpose | Latency | Tokens |
|---|---|---|---|
| **L1 — Deterministic** | Lexical / AST parsing, static analysis, language-server queries, pattern matching | <50 ms | 0 |
| **L2 — Retrieval** | AST-aware chunking, keyword + vector search, project rules, repo map | 100–500 ms | 0 |
| **L3 — Constrained generation** | Grammar-constrained decoding, small language model, structured output | 500 ms – 2 s | 500–2 000 |
| **L4 — Full reasoning** | Larger language model, multi-file planning, architect/editor pattern, feedback loops | 5–30 s | 2 000–8 000 |

Cost and latency drive correctness: a feature that could run at L1 must not escalate to L4 for convenience.

---

## Key Design Principles

These flow from the invariants above. They are the day-to-day contract for every change. Invariant #1 (LLM as last resort) is the governing principle; the items below add operational texture around it.

1. **Fail fast, fail safe** — Verify edits before applying; use safety checkpoints; never leave the tree half-migrated.
2. **Transparent operations** — The user should be able to see what's happening at every step.
3. **Local-first** — Privacy and cost are features, not afterthoughts.
4. **Incremental complexity** — Start with the simplest approach that solves the problem; add sophistication only when the simple approach proves insufficient.
5. **Docs track reality** — Update documentation WITH code changes, never after.

---

## What AutoCode is NOT

These are explicit non-goals:

- **Not cloud-first.** The product runs on the user's machine. Cloud is opt-in, never default.
- **Not dependent on frontier models.** No 70B+ weights, no 100 K context window prerequisites.
- **Not a judgement replacement.** The human user is the developer; agents accelerate, review, and build under user direction.
- **Not orchestration-first.** Complex multi-agent fleets are not the default product surface. Simple, inspectable pipelines win.
- **Not parity-only with cloud assistants.** Features that only improve surface-level similarity to Claude Code / Copilot / Cursor are not the goal; the target is compatibility for migrants plus the edge-native, deterministic-first differentiation.

---

## Rationale — why these invariants

**Why edge-native?** Token cost and latency are real. Every round-trip to a frontier model burns budget the user will not get back. The edge path is always cheaper, always faster after the first call, and works offline.

**Why deterministic-first?** Lexical and static-analysis tools are rigorously correct — they don't hallucinate a function signature, they don't drift between runs, they don't paywall features. Using them as the primary intelligence layer makes the product's behavior reproducible and inspectable.

**Why 4 layers?** A clean layering lets every feature declare which tier it lives in. That declaration is itself enforcement: an L2 retrieval feature must not secretly call L4; an L3 feature must use grammar constraints, not free-form generation.

**Why consumer hardware?** Users who need AutoCode are not the ones with A100 clusters. Targeting 8 GB VRAM / 16 GB RAM forces every component to stay honest about its cost. A feature that requires a bigger machine is a feature that broke the invariant.

---

## How to use this document

- **Agents:** read this on session start. Do not propose changes that conflict with these invariants without asking the user first.
- **Reviewers:** if a change violates an invariant, flag it in `AGENTS_CONVERSATION.MD` with severity `Critical` and stop the change until the user authorizes the deviation.
- **Product owner (user):** this is the change-control surface for the vision. Amendments happen here, not in ephemeral session docs.

---

## Authority chain

- **This file** — user-approved vision. Tech-agnostic.
- **`CLAUDE.md`, `AGENTS.md`** — entry-point docs for agents. May name specific tech choices; must stay consistent with this file's invariants.
- **`PLAN.md`** — phase-by-phase implementation map. May name specific tech choices; must stay consistent with this file's invariants.
- **`AGENT_COMMUNICATION_RULES.md`** — agent-to-agent protocol.

If two documents disagree, **this file wins**. Fix the drift in the other file.
