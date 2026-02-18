# Sprint 5D-4: Golden Transcript Tests

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~5h (2h tests + 3h impl)
> Dependencies: 5D-1 (MCP Server), 5D-3 (CLIBroker)
> Owner: Claude

---

## Goal

Known-good JSON IO fixtures per adapter + strict version probe with fail-closed behavior (Section 15.17 R3).

---

## TDD Tests (Write First)

- [ ] `test_golden_claude` - Claude Code golden transcript matches expected IO
- [ ] `test_golden_codex` - Codex golden transcript matches expected IO
- [ ] `test_version_failclosed` - unsupported version triggers graceful error

## Implementation

- [ ] Create golden transcript fixtures for each adapter
- [ ] Implement version probes: supports_mcp_server, supports_json_schema_output, supports_background_tasks (R3)
- [ ] Fail-closed behavior: unsupported version = graceful error, not silent degradation
- [ ] Contract tests against real tool binaries

## Acceptance Criteria

- [ ] Golden transcript tests per adapter
- [ ] Version probes implemented (R3)
- [ ] Fail-closed on unsupported versions
- [ ] Contract tests pass against real tool binaries (not mocked)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_golden_transcripts.py`
- Integration test: `tests/integration/test_adapter_contracts.py`
- QA artifact: `docs/qa/test-results/sprint-5d-4-golden-tests.md`
