# Sprint 5A0-1: Diff Preview

> Status: **NOT STARTED**
> Sprint: 5A0 (Quick Wins)
> Est. Hours: ~3h (1h tests + 2h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Show a before/after diff comparison after every `write_file` call so the user can see exactly what changed.

---

## TDD Tests (Write First)

- [ ] `test_diff_preview_shows_before_after` - diff output contains original and modified content
- [ ] `test_diff_preview_empty_file` - handles new file creation (no "before")
- [ ] `test_diff_preview_binary_skip` - skips binary files gracefully
- [ ] `test_diff_preview_output_contains_plus_minus` - assert diff output has +/- markers (deterministic)

## Implementation

- [ ] Enrich `write_file` tool to capture file content before write
- [ ] Generate unified diff (difflib)
- [ ] Display diff in TUI/CLI output with syntax highlighting
- [ ] Handle edge cases: new files, binary files, empty files
- [ ] Ensure diff is shown BEFORE the write is committed (preview mode)

## Acceptance Criteria

- [ ] Diff preview displayed after every `write_file` call
- [ ] +/- markers visible in diff output
- [ ] Binary files skipped with clear message
- [ ] New file creation shows entire content as additions
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Manual TUI verification (visual check)
- [ ] Deterministic assertion: diff output has +/- markers

## Artifacts

- Test file: `tests/unit/test_diff_preview.py`
- QA artifact: `docs/qa/test-results/sprint-5a0-1-diff-preview.md`
