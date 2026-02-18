# Sprint 5A0-4: Doctor MVP

> Status: **NOT STARTED**
> Sprint: 5A0 (Quick Wins)
> Est. Hours: ~3.5h (1h tests + 2.5h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

`hybridcoder doctor` command that runs 8 readiness checks with actionable remediation messages.

---

## TDD Tests (Write First)

- [ ] `test_doctor_8_checks` - doctor runs exactly 8 checks
- [ ] `test_doctor_remediation_messages` - each failing check has an actionable message
- [ ] `test_doctor_ollama_check` - Ollama connectivity check works
- [ ] `test_doctor_returns_structured_report` - JSON report with pass/fail per check (deterministic)

## Implementation

- [ ] Create `hybridcoder doctor` CLI command
- [ ] Implement 8 readiness checks:
  - [ ] Check 1: Python version >= 3.11
  - [ ] Check 2: Ollama installed and reachable
  - [ ] Check 3: L4 model (Qwen3-8B) available
  - [ ] Check 4: LanceDB database exists
  - [ ] Check 5: tree-sitter grammars loaded
  - [ ] Check 6: Git available and project is git repo
  - [ ] Check 7: VRAM sufficient (>= 6GB free)
  - [ ] Check 8: Disk space sufficient (>= 2GB free)
- [ ] Return structured JSON report with pass/fail per check
- [ ] Display remediation message for each failing check

## Acceptance Criteria

- [ ] `hybridcoder doctor` runs 8 checks
- [ ] Each check returns pass/fail with description
- [ ] Failing checks have actionable remediation messages
- [ ] Output is structured (JSON-parseable)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Manual verification on clean machine

## Artifacts

- Test file: `tests/unit/test_doctor.py`
- QA artifact: `docs/qa/test-results/sprint-5a0-4-doctor-mvp.md`
