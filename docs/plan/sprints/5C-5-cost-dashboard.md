# Sprint 5C-5: Cost Dashboard

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~5h (2h tests + 3h impl)
> Dependencies: 5A0-3 (Token Counting), 5A-3 (Adapters)
> Owner: Claude

---

## Goal

Token breakdown dashboard: local vs cloud, per-agent, per-task cost tracking.

---

## TDD Tests (Write First)

- [ ] `test_cost_per_agent` - cost attributed to correct agent
- [ ] `test_cost_local_vs_cloud` - local ($0) vs cloud (capped) costs tracked separately

## Implementation

- [ ] Aggregate token counts per agent
- [ ] Track local vs cloud separately
- [ ] Per-task cost attribution
- [ ] Display dashboard in CLI output
- [ ] Export cost report

## Acceptance Criteria

- [ ] Cost dashboard shows per-agent, per-task token breakdown
- [ ] Local vs cloud costs tracked separately
- [ ] Local operations show $0 cost
- [ ] Cloud operations show actual cost
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_cost_dashboard.py`
- QA artifact: `docs/qa/test-results/sprint-5c-5-cost-dashboard.md`
