# TUI Testing

Single source of truth for testing the interactive terminal surface. Not for unit tests.

## Files

- **[`tui-testing-strategy.md`](tui-testing-strategy.md)** — the rules. Read this first. Covers the four-dimension matrix, required validation matrix (§3), command discoverability (§4), policies, PTY patterns, triage workflow, adding scenarios, and common pitfalls.
- **[`tui_testing_checklist.md`](tui_testing_checklist.md)** — the enforced template. Copy it per-change, fill in as you go, store as an artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-tui-verification.md`. Unchecked boxes or missing evidence paths = FAIL.
- **[`tui-reference-scene-trigger-guide.md`](tui-reference-scene-trigger-guide.md)** — the 14-scene trigger matrix for `tui-references`, including which scenes are direct, approximate, or blocked.
- **[`tui-capture-compare-workflow.md`](tui-capture-compare-workflow.md)** — the repeatable screenshot-first workflow: baseline checks, comparison bundle generation, targeted frame capture, and gap reporting.
- **[`tui-system-feature-coverage-guide.md`](tui-system-feature-coverage-guide.md)** — guidance for non-frontend-only scenes such as planning, subagents, restore, review/diff, search, and escalation.
- **[`tui_implementation_plan.md`](tui_implementation_plan.md)** — durable execution plan for turning the current 14-scene matrix into real `tui-references` parity, updated to reflect Claude Entry `1294`.
- **[`tui_implementation_todo.md`](tui_implementation_todo.md)** — actionable checklist version of the implementation plan.
- **[`../reference/rpc-schema-v1.md`](../reference/rpc-schema-v1.md)** — canonical Stage 0A JSON-RPC method names and compat-alias audit.

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
- Manual visual evidence helpers:
  - `make tui-reference-gap` — screenshot-first reference-vs-live bundle
  - `make tui-scene-matrix` — current-state sweep for all 14 reference scenes
  - `autocode/tests/tui-references/capture_frame_sequence.py --list-presets` — named scene trigger presets
  - `autocode/tests/tui-references/capture_frame_sequence.py` — mid-run frame capture for plan / restore / task / subagent / benchmark flows
- Known-bug inventory: `bugs/codex-tui-issue-inventory.md` (60 patterns + 12 adversarial sweeps S1-S12; all referenced in the checklist)
- PTY command reference: `docs/tests/pty-testing.md`
