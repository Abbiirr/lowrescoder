# Sprint 5D-3: CLIBroker

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~5h (2h tests + 3h impl)
> Dependencies: 5D-1 (MCP Server)
> Owner: Claude

---

## Goal

Minimal CLI broker for Codex with JSON-only parsing (no regex/free-text).

---

## TDD Tests (Write First)

- [ ] `test_clibroker_json` - parses Codex `--json` output correctly
- [ ] `test_clibroker_no_regex` - no regex used for CLI output parsing

## Implementation

- [ ] Implement CLIBroker for Codex (`codex exec --json` + `--output-schema`)
- [ ] JSON/schema parsing ONLY (Section 15.15 R1)
- [ ] No regex or free-text parsing
- [ ] Error handling for malformed JSON responses

## Acceptance Criteria

- [ ] CLIBroker can invoke Codex `--json` and parse output
- [ ] JSON/schema parsing only (no regex)
- [ ] Error handling for malformed responses
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_cli_broker.py`
- QA artifact: `docs/qa/test-results/sprint-5d-3-cli-broker.md`
