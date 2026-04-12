# Sprint 5A0-5: Completion Notifications

> Status: **NOT STARTED**
> Sprint: 5A0 (Quick Wins)
> Est. Hours: ~1h (0.5h tests + 0.5h impl)
> Dependencies: 5A0-3 (token counting)
> Owner: Claude

---

## Goal

Enrich the on_done handler with summary statistics including token count, files changed, and time elapsed.

---

## TDD Tests (Write First)

- [ ] `test_on_done_has_summary_stats` - on_done output includes files changed, time elapsed
- [ ] `test_on_done_has_token_count` - on_done output includes token usage from 5A0-3

## Implementation

- [ ] Enrich on_done handler with:
  - [ ] Total token count (from 5A0-3)
  - [ ] Files changed count
  - [ ] Time elapsed
  - [ ] Tools used summary
- [ ] Format as clean summary block

## Acceptance Criteria

- [ ] on_done shows summary stats (tokens, files, time, tools)
- [ ] Token count integrated from 5A0-3
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_completion.py`
- QA artifact: `docs/qa/test-results/sprint-5a0-5-completion.md`
