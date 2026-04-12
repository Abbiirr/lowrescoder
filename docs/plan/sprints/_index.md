# Phase 5 Sprint Tracker — Index

> Last updated: 2026-02-18
> Plan: `docs/plan/phase5-agent-teams.md` Rev 6
> Strategy: **"Standalone first, then interact."**

---

## How to Use

- **Sub-sprint start gate:** Before starting any sub-sprint, present to the user what exists now and what will exist after completion. Get explicit user permission to proceed.
- **TDD: Tests come first.** Every sub-sprint begins by writing all tests. Tests are expected to fail until implementation catches up. This is by design.
- Each sub-sprint has its own file with checkboxes
- Work order within each sub-sprint: **1) Get user approval** → **2) Write TDD tests (expect failures)** → **3) Implement until tests pass** → **4) Acceptance criteria**
- Mark boxes `[x]` as you complete each item
- When a sub-sprint is fully complete, move it to `docs/plan/sprints/done/`
- Status legend: **NOT STARTED** | **IN PROGRESS** | **DONE** | **BLOCKED**

---

## Pre-Implementation Gates

| File | Description | Status |
|------|-------------|--------|
| [00-pre-gates.md](00-pre-gates.md) | Task bank freeze, user decisions (B2 CLOSED) | IN PROGRESS |

---

## Sprint 5A0: Quick Wins (5 sub-sprints)

> Milestone: M1+M2 Standalone MVP
> Focus: Low-hanging fruit that improves UX immediately

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | [5A0-1-diff-preview.md](5A0-1-diff-preview.md) | Diff preview after write_file | NOT STARTED |
| 2 | [5A0-2-git-safety.md](5A0-2-git-safety.md) | Auto-commit before edits | NOT STARTED |
| 3 | [5A0-3-token-counting.md](5A0-3-token-counting.md) | Per-request token counter | NOT STARTED |
| 4 | [5A0-4-doctor-mvp.md](5A0-4-doctor-mvp.md) | `hc doctor` diagnostic command | NOT STARTED |
| 5 | [5A0-5-completion.md](5A0-5-completion.md) | Sprint 5A0 completion gate | NOT STARTED |

---

## Sprint 5A: Identity + Eval (5 sub-sprints)

> Milestone: M1+M2 Standalone MVP
> Focus: AgentCard, ProviderRegistry, Eval Harness

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | [5A-1-agent-card.md](5A-1-agent-card.md) | AgentCard dataclass | NOT STARTED |
| 2 | [5A-2-provider-registry.md](5A-2-provider-registry.md) | ProviderRegistry + adapters | NOT STARTED |
| 3 | [5A-3-adapters.md](5A-3-adapters.md) | OllamaAdapter + LlamaCppAdapter | NOT STARTED |
| 4 | [5A-4-eval-harness.md](5A-4-eval-harness.md) | EvalHarness scaffold | NOT STARTED |
| 5 | [5A-5-identity-wire.md](5A-5-identity-wire.md) | Wire AgentCard into TUI/CLI | NOT STARTED |

---

## Sprint 5B: LLMLOOP — Architect/Editor (7 sub-sprints)

> Milestone: M1+M2 Standalone MVP
> Focus: Architect/Editor pattern, Jedi semantic tools, edit command
> Pre-gate: Editor model bakeoff (5B-0)

| # | File | Description | Status |
|---|------|-------------|--------|
| 0 | [5B-0-editor-bakeoff.md](5B-0-editor-bakeoff.md) | Editor model bakeoff (pre-gate) | NOT STARTED |
| 1 | [5B-1-architect.md](5B-1-architect.md) | ArchitectAgent (L4 planner) | NOT STARTED |
| 2 | [5B-2-editor.md](5B-2-editor.md) | EditorAgent (L3 patch applier) | NOT STARTED |
| 3 | [5B-3-verification.md](5B-3-verification.md) | VerificationAgent (L1 checker) | NOT STARTED |
| 4 | [5B-4-pipeline.md](5B-4-pipeline.md) | LLMLOOP orchestration pipeline | NOT STARTED |
| 5 | [5B-5-jedi-tools.md](5B-5-jedi-tools.md) | Jedi semantic tools (goto/refs/types) | NOT STARTED |
| 6 | [5B-6-edit-command.md](5B-6-edit-command.md) | `/edit` command integration | NOT STARTED |

---

## Sprint 5C: Evals + Cost + Policy (6 sub-sprints)

> Milestone: M1+M2 Standalone MVP
> Focus: Context eval, AgentBus, Policy Router, Cost Dashboard

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | [5C-1-context-eval.md](5C-1-context-eval.md) | Context retrieval eval suite | NOT STARTED |
| 2 | [5C-2-agent-bus.md](5C-2-agent-bus.md) | AgentBus message passing | NOT STARTED |
| 3 | [5C-3-sop-runner.md](5C-3-sop-runner.md) | SOPRunner workflow engine | NOT STARTED |
| 4 | [5C-4-policy-router.md](5C-4-policy-router.md) | PolicyRouter (L1/L2/L3/L4 routing) | NOT STARTED |
| 5 | [5C-5-cost-dashboard.md](5C-5-cost-dashboard.md) | Cost dashboard + token tracking | NOT STARTED |
| 6 | [5C-6-reliability.md](5C-6-reliability.md) | Reliability hardening + M1/M2 gate | NOT STARTED |

---

## Sprint 5D: External Integration (5 sub-sprints)

> Milestone: M3 External Integration (only after M1+M2 gate passes)
> Focus: MCP server, config generation, external tool tracking

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | [5D-1-mcp-server.md](5D-1-mcp-server.md) | MCP server (tools/resources) | NOT STARTED |
| 2 | [5D-2-config-gen.md](5D-2-config-gen.md) | Config generator for Claude/Codex | NOT STARTED |
| 3 | [5D-3-cli-broker.md](5D-3-cli-broker.md) | CLIBroker subprocess manager | NOT STARTED |
| 4 | [5D-4-golden-tests.md](5D-4-golden-tests.md) | Golden path integration tests | NOT STARTED |
| 5 | [5D-5-tracker.md](5D-5-tracker.md) | ExternalToolTracker discovery | NOT STARTED |

---

## Milestone Gates

| Gate | Criteria | Status |
|------|----------|--------|
| M1 | >= 75% task bank pass, p95 single-file <= 60s / multi-file <= 300s, 0 hard-fail regressions | NOT MET |
| M2 | context F1 >= 0.65, minimum absolute task success >= 50%, >= 30% token reduction | NOT MET |
| M3 | health probes pass, idempotent setup/uninstall, integration tests for supported tool versions | NOT MET |

---

## Sprint Order

```
Pre-Gates → 5A0 → 5A → 5B-0 (bakeoff) → 5B → 5C → 5D
```

Each sprint must pass its acceptance criteria before the next begins.
Completed sub-sprint files are moved to `docs/plan/sprints/done/`.
