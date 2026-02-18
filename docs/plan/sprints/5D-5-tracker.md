# Sprint 5D-5: ExternalToolTracker

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~4h (1.5h tests + 2.5h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Runtime discovery of external AI coding tools on PATH with health probes.

---

## TDD Tests (Write First)

- [ ] `test_tracker_path_discover` - discovers tools available on PATH
- [ ] `test_tracker_health` - health probe returns status for each discovered tool

## Implementation

- [ ] Implement `ExternalToolTracker.discover()` - check PATH for known tools
- [ ] Known tools: claude (Claude Code), codex (Codex), opencode (OpenCode)
- [ ] Get version for each discovered tool
- [ ] Health probe: verify tool is functional (not just present)
- [ ] Version compatibility matrix documentation

## Acceptance Criteria

- [ ] ExternalToolTracker discovers tools on PATH
- [ ] Health probes verify tool functionality
- [ ] Version compatibility matrix documented with tested minimum versions
- [ ] Manual fallback installation docs for every supported tool
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_external_tracker.py`
- QA artifact: `docs/qa/test-results/sprint-5d-5-tracker.md`
