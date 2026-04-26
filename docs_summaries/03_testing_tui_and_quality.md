# Testing, TUI, And Quality Summary

## Main point

The project has a heavy TUI/testing surface. The core rule is: do not trust one harness alone.

## Canonical testing docs

- [autocode/TESTING.md](../autocode/TESTING.md) is the broad testing and evaluation guide.
  - Python tests
  - Rust tests
  - integration tests
  - sprint verification
  - benchmarks
- [docs/tui-testing/tui-testing-strategy.md](../docs/tui-testing/tui-testing-strategy.md) is the authoritative TUI test policy.
- [docs/tui-testing/tui_testing_checklist.md](../docs/tui-testing/tui_testing_checklist.md) is the enforced per-change checklist.
- [autocode/tests/README.md](../autocode/tests/README.md) and the harness-specific readmes under `autocode/tests/` explain the individual test families.

## TUI testing model

The TUI strategy explicitly uses multiple dimensions:

- runtime invariants
- design-target ratchet / reference scenes
- self-regression image/VHS style checks
- live PTY smoke

This matters because many failures are visible-surface problems, not just reducer/backend-state problems.

## Most important TUI test docs

- [docs/tui-testing/tui-testing-strategy.md](../docs/tui-testing/tui-testing-strategy.md)
- [docs/tui-testing/tui_testing_checklist.md](../docs/tui-testing/tui_testing_checklist.md)
- [autocode/tests/pty/README.md](../autocode/tests/pty/README.md)
- [autocode/tests/tui-comparison/README.md](../autocode/tests/tui-comparison/README.md)
- [autocode/tests/tui-references/README.md](../autocode/tests/tui-references/README.md)
- [autocode/tests/vhs/README.md](../autocode/tests/vhs/README.md)
- [docs/tests/pty-testing.md](../docs/tests/pty-testing.md)

## QA artifact stores

Two big doc families are mostly evidence stores:

- `docs/qa/`
- `autocode/docs/qa/`

These are not “read this first” docs. They are stored verification artifacts. Use them when you need proof for a specific slice, canary, smoke run, or bug close-out.

As of this inventory pass, they dominate the doc count:

- `docs/qa`: 509 docs
- `autocode/docs/qa`: 459 docs

## Bug docs

Two bug docs matter most:

- [bugs/codex-tui-issue-inventory.md](../bugs/codex-tui-issue-inventory.md)
  - the big historical TUI issue inventory and fuzz/bug-finding strategies
- [bugs/bugs.md](../bugs/bugs.md)
  - the live runtime bug ledger with current screenshot-backed failures and fixes

Use the inventory for product debt and test ideas. Use the live ledger for current regressions and real-path evidence.

## Quality takeaway

The project’s testing philosophy is:

- green unit tests are necessary but insufficient
- TUI changes need renderer-owned evidence
- PTY/live-path failures are first-class
- checklists and artifacts matter as much as raw pass counts

## Source references

- [autocode/TESTING.md](../autocode/TESTING.md)
- [docs/tui-testing/tui-testing-strategy.md](../docs/tui-testing/tui-testing-strategy.md)
- [docs/tui-testing/tui_testing_checklist.md](../docs/tui-testing/tui_testing_checklist.md)
- [autocode/tests/README.md](../autocode/tests/README.md)
- [autocode/tests/pty/README.md](../autocode/tests/pty/README.md)
- [autocode/tests/tui-comparison/README.md](../autocode/tests/tui-comparison/README.md)
- [autocode/tests/tui-references/README.md](../autocode/tests/tui-references/README.md)
- [autocode/tests/vhs/README.md](../autocode/tests/vhs/README.md)
- [docs/tests/pty-testing.md](../docs/tests/pty-testing.md)
- [bugs/codex-tui-issue-inventory.md](../bugs/codex-tui-issue-inventory.md)
- [bugs/bugs.md](../bugs/bugs.md)
- [../docs/qa/](../docs/qa/)
- [../autocode/docs/qa/](../autocode/docs/qa/)
