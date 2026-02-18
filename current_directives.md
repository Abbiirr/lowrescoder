# Current Directives

> Last updated: 2026-02-18

## Active Phase

**Phase 5 — Universal Orchestrator** (`PROVISIONAL_LOCKED` Rev 6)

## Current Sprint

**Pre-Implementation Gates** — must complete before any Sprint 5A0 work begins.

Tracking file: `docs/plan/sprints/00-pre-gates.md`

## Sprint Order

```
Pre-Gates → 5A0 → 5A → 5B-0 (bakeoff) → 5B → 5C → 5D
```

## Where to Look

| What | File |
|------|------|
| Sprint index (all sub-sprints) | `docs/plan/sprints/_index.md` |
| Current sub-sprint checklist | `docs/plan/sprints/00-pre-gates.md` |
| Full Phase 5 plan | `docs/plan/phase5-agent-teams.md` |
| Lock criteria | `docs/plan/phase5-roadmap-lock-checklist.md` |

## Pending Decisions (User)

- [x] Confirm num_ctx policy (Option A: adaptive 4096/8192) — confirmed 2026-02-18
- [ ] Confirm waiver acceptance (B1 → CLOSED)
- [ ] Give go-ahead for Sprint 5A0

## Sub-Sprint Start Gate

Before starting any sub-sprint, you MUST:
1. Have clearly defined goals and clear tests for the sub-sprint
2. Present to the user: **what exists now** and **what will exist after the sub-sprint completes**
3. Get explicit user permission to proceed

No sub-sprint starts without this approval step.

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Open the current sub-sprint file and work through its checkboxes
3. **TDD: Write all tests first.** Tests are expected to fail until implementation is done. This is the workflow, not a problem.
4. Implement until all tests pass
5. Mark items `[x]` as you complete them
6. When a sub-sprint is done, update this file to point to the next one
7. Archive completed sub-sprint files to `docs/plan/sprints/done/`
