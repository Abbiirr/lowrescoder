# TUI Testing

Single source of truth for testing the interactive terminal surface. Not for unit tests.

## Files

- **[`tui-testing-strategy.md`](tui-testing-strategy.md)** — the rules. Read this first. Covers the four-dimension matrix, required validation matrix (§3), command discoverability (§4), policies, PTY patterns, triage workflow, adding scenarios, and common pitfalls.
- **[`tui_testing_checklist.md`](tui_testing_checklist.md)** — the enforced template. Copy it per-change, fill in as you go, store as an artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-tui-verification.md`. Unchecked boxes or missing evidence paths = FAIL.

## Workflow

1. Starting a TUI change → read the strategy doc (`tui-testing-strategy.md`)
2. Kicking off verification → copy the checklist (`tui_testing_checklist.md`)
3. Fill the checklist as you work — evidence paths must be real files
4. Post the filled-in file as your review artifact
5. If Codex or another reviewer finds a gap you missed, update the strategy doc to catch it next time (§6.5 predicate-drift + §3.0 visible-surface rule)

## Related

- Per-harness implementation READMEs:
  - `autocode/tests/tui-comparison/README.md` — Track 1 runtime invariants
  - `autocode/tests/tui-references/README.md` — Track 4 design-target ratchet
  - `autocode/tests/vhs/README.md` — VHS self-regression
  - `autocode/tests/pty/README.md` — PTY smoke harnesses
- Known-bug inventory: `bugs/codex-tui-issue-inventory.md` (60 patterns + 12 adversarial sweeps S1-S12; all referenced in the checklist)
- PTY command reference: `docs/tests/pty-testing.md`
