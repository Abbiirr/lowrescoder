# Sprint 5A0-2: Git Safety

> Status: **NOT STARTED**
> Sprint: 5A0 (Quick Wins)
> Est. Hours: ~4h (1h tests + 3h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Auto-commit before edits for safety, block GIT_EDITOR hijacking, enforce shell timeouts.

---

## TDD Tests (Write First)

- [ ] `test_git_autocommit_before_edit` - verify a commit is created before file modification
- [ ] `test_git_editor_blocked` - GIT_EDITOR env var is unset/blocked during agent operations
- [ ] `test_shell_timeout_30s` - shell commands timeout after 30s default

## Implementation

- [ ] Add git auto-commit before any file edit (configurable on/off)
- [ ] Set `GIT_EDITOR=true` to prevent interactive editor prompts
- [ ] Block interactive prompt patterns in shell execution
- [ ] Add 30s default timeout to all shell commands
- [ ] Make timeout configurable via `hybridcoder.toml`

## Acceptance Criteria

- [ ] Git auto-commit created before edits (when enabled)
- [ ] Auto-commit is configurable (on/off in config)
- [ ] GIT_EDITOR blocked during agent operations
- [ ] Interactive prompts blocked in shell
- [ ] 30s default shell timeout enforced
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Cycle time benchmark (measure overhead of auto-commit)

## Artifacts

- Test file: `tests/unit/test_git_safety.py`
- QA artifact: `docs/qa/test-results/sprint-5a0-2-git-safety.md`
