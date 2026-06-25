# TUI Plan — v9 Shell Contract And Reference Alignment

Status: LOCKED / PARKED.

Do not start TUI implementation until backend harness solidification is closed (`AGENTS_CONVERSATION.MD` Entry 1946 / BHF-0 through BHF-6) or the user explicitly overrides this order.

Last updated: 2026-05-06

## Purpose

This file is the durable checkpoint for remaining AutoCode TUI work. It consolidates the accepted TUI direction from `AGENTS_CONVERSATION.MD` Entries 1944 and 1945, preserves the backend-first sequencing from Entry 1946, and gives future builders a single plan to check before modifying the Rust TUI or TUI reference harness.

This plan does not delete or invalidate older TUI testing docs. It supersedes scattered planning notes for the next TUI tranche, but older docs remain useful as historical evidence and validation references.

## Source Inputs

- `tui-references/autocode_tui_design_v9_shell_contract.md`
- `tui-references/autocode_tui_v9_corrected_static.html`
- `tui-references/autocode_tui_v9_screens_manifest.json`
- `tui-references/screens/*.png`
- `docs/tui-testing/tui_implementation_plan.md`
- `docs/tui-testing/tui_implementation_todo.md`
- `docs/tui-testing/tui-testing-strategy.md`
- `docs/tui-testing/tui_testing_checklist.md`
- `autocode/tests/tui-references/README.md`
- `autocode/tests/tui-comparison/README.md`
- `autocode/tests/vhs/README.md`
- `autocode/tests/pty/README.md`
- `AGENTS_CONVERSATION.MD` Entries 1944, 1945, and 1946

## Non-Negotiables

- Backend first: TUI work is parked until backend harness truthfulness, artifacts, retry/infra classification, and backend surface coverage are accepted.
- Do not fake screenshots or static product surfaces. A reference scene becomes a hard gate only after the live product exposes the state honestly.
- Version reference manifests. Do not replace the legacy 14-scene manifest during the retargeting slice.
- Preserve all four TUI test dimensions: runtime invariants, design-target ratchet, self-vs-self PNG regression, and live PTY smoke.
- Use bare `autocode` in user-facing launch guidance unless discussing a subcommand-specific implementation detail.
- Default inline mode must remain full-screen and preserve native terminal scrollback. Altscreen remains opt-in.
- Every visible app state must have exactly one live composer and exactly one footer.
- Focus modes may replace only `MainRegion`; they must not mount their own live composer or footer.
- Bounded drawers and queue strips must never push the composer or footer off-screen.

## Current State

The earlier HR-5 14-scene Rust TUI migration is largely complete: direct triggerability exists for legacy scenes, many detail surfaces have real-data bindings, and runtime follow-ons such as spinner correlation, thinking/output split, and slash PTY coverage were completed in prior slices.

The new v9 target is stricter. It is not a first-generation Rust migration; it is a shell-contract and reference-alignment tranche. The main remaining work is to retarget the reference harness to the v9 shell contract, then make the live Rust TUI satisfy those stricter invariants.

Known current issue: `make tui-references` has been observed failing because the extractor still expects an older static HTML file name. The first TUI slice must fix reference harness signal before any renderer work.

## Remaining Phases

### TUI-0 — Reference Harness Retarget

Goal: make the reference harness understand v9 without losing legacy coverage.

Tasks:

- Add or update the extractor path for `tui-references/autocode_tui_v9_corrected_static.html` and `tui-references/autocode_tui_v9_screens_manifest.json`.
- Add a v9 manifest such as `autocode/tests/tui-references/manifest_v9.yaml`.
- Preserve the current legacy 14-scene manifest as `manifest_v14_legacy.yaml`, or keep the existing file with equally clear naming. Do not silently replace it.
- Make `make tui-references` run legacy hard gates and v9 strict-xfail/default-unpromoted gates during the transition.
- Update `autocode/tests/tui-references/README.md` and related testing docs to state which manifest is legacy and which is v9 canonical.
- Keep v9 scenes strict-xfail or non-promoted until live captures prove the product state exists.

Exit gate:

- `make tui-references` no longer fails due to missing legacy static HTML.
- Legacy gates still protect existing behavior.
- v9 scenes are visible to the harness but not falsely promoted.
- Docs describe the transition state honestly.

### TUI-1 — AppShell Architecture

Goal: make the live Rust TUI conform to the v9 shell contract.

Tasks:

- Centralize layout around `Header`, `MainRegion`, optional `Drawer`, optional one-row `QueueStrip`, `Composer`, and `Footer`.
- Enforce exactly one live composer and one footer across idle, active, recovery, approval, picker, and focus states.
- Ensure focus modes replace only `MainRegion`.
- Keep drawers bounded with internal scroll; never let drawer content push the composer/footer off-screen.
- Keep queue strip exactly one row and truncating, not wrapping.
- Add renderer/runtime predicates for `80x24`, `120x40`, `160x50`, and `200x50`.

Exit gate:

- Track 1 predicates prove composer/footer presence and bottom anchoring across key states and terminal sizes.
- Rust unit tests cover shell layout invariants.

### TUI-2 — Composer-Attached Discovery

Goal: replace modal/centered discovery patterns with composer-attached discovery where v9 requires it.

Tasks:

- Implement or retarget `/` slash picker as composer-attached.
- Implement or retarget `@` file picker as composer-attached.
- Implement or retarget `#` symbol picker as composer-attached.
- Reconcile `Ctrl+Shift+P` / command palette behavior with v9: useful, but not the default slash-command surface.
- Bind command, model/provider, file, symbol, and session data from backend-owned sources where available.
- Enforce focus safety: letters edit text while composer focus is active; dangerous single-key actions are disabled in composer focus.

Exit gate:

- `06_slash_picker`, `07_file_picker`, and `08_symbol_picker` have honest live triggers or remain strict-xfail with precise gaps.
- PTY smoke proves picker open/cancel/type behavior does not corrupt the composer.

### TUI-3 — Transcript, Drawer, Queue, And Recovery Runtime

Goal: make high-stress runtime states terminal-native and stable.

Tasks:

- Separate submitted prompts from the live composer; submitted prompts are immutable transcript entries.
- Route streaming tool output, stderr, selected tool output, and live command output into bounded drawers instead of dumping large logs into transcript.
- Implement queue states explicitly: `draft`, `queued`, `blocked`, `needs-review`, and `submitted`.
- Keep `[draft]` counts separate from queued counts.
- Preserve draft text and queue impact visibility during recovery, restore, and retry flows.
- Add large-paste/bracketed-paste behavior that remains usable and does not break layout.
- Keep warnings, errors, gateway failures, and recovery choices visible without hiding the composer.

Exit gate:

- `02_active`, `03_drawer`, `04_queue_strip`, `05_queue_drawer`, `14_recovery`, `21_large_paste`, and `22_copy_fallback` are either honest live gates or strict-xfail with exact missing product gaps.
- Multi-turn PTY smoke verifies active, recovery, and queued flows.

### TUI-4a — Operational Focus Modes

Goal: implement low-blast-radius focus modes that replace only the middle region.

Screens:

- `09_plan_inline`
- `15_restore_focus`
- `16_sessions`
- `17_search_focus`
- `18_transcript_review`
- `19_status`
- `20_settings`

Tasks:

- Keep each mode as a `MainRegion` replacement, not a new shell.
- Show effective state, not vague labels, especially in status/settings.
- Make restore impacts visible before confirmation.
- Keep single-key list actions disabled unless focus is explicitly in list/review mode.

Exit gate:

- Focus transitions are deterministic and footer announces focus mode.
- Composer remains visible and recoverable with `i` or equivalent focus return.

### TUI-4b — Approval Focus Modes

Goal: implement evidence-first approval and escalation surfaces without broad unsafe scopes.

Screens:

- `10_review_approval`
- `11_diff_focus`
- `12_protected_path`
- `13_network_ci_denied`
- `23_mcp_read_approval`

Tasks:

- Approval panels must show operation type, exact target, patch/command hash where applicable, requester, matched rule, policy source, network state, reversibility, and expiration/scope.
- Prefer narrow scopes: exact patch, exact file for this turn, exact command invocation, or exact MCP read call.
- Keep protected-path approval separate from network/remote approval.
- Require explicit confirmation for dangerous operations.
- Ensure composer focus never interprets `a`, `r`, `x`, or similar as approval/reject/delete/restore.

Exit gate:

- Approval PTY tests prove scope text and focus safety.
- No approval screen offers broad session-wide escalation unless explicitly approved by the user in a later plan.

### TUI-4c — Telemetry And Inspection Focus Modes

Goal: expose power-user inspection without turning the default UI into a dashboard.

Screens:

- `24_subagent_trace`
- `27_command_center`

Tasks:

- Keep subagent trace and command center opt-in.
- Do not add permanent rails for subagents, plans, tasks, risk, queue, or settings.
- Bind to structured backend events where available instead of parsing display strings.
- Preserve prompt-first idle state.

Exit gate:

- Inspection surfaces are reachable and useful, but absent from the default idle layout.
- Track 1 and PTY smoke confirm default prompt-first behavior remains intact.

### TUI-5 — Visual Fidelity Ratchet

Goal: promote v9 scenes from strict-xfail/reference-only into real visual gates after product states exist.

Tasks:

- Compare live captures to v9 PNG references in `tui-references/screens/`.
- Use `make tui-reference-gap` and `make tui-scene-matrix` to track deltas.
- Add or update VHS captures only after structural invariants are green.
- Rebaseline VHS PNGs only with explicit user signoff.
- Track spacing, density, contrast hierarchy, narrow terminal behavior, ASCII fallback, drawer height, queue one-line behavior, and composer/footer anchoring.

Exit gate:

- v9 scenes are promoted one family at a time with stored evidence under `autocode/docs/qa/test-results/`.
- Visual changes are backed by live captures, not static mock output.

## v9 Screen Mapping

| v9 screen | Primary phase | Acceptance focus |
|---|---|---|
| `01_idle` | TUI-1, TUI-5 | prompt-first shell, one composer/footer |
| `02_active` | TUI-1, TUI-3, TUI-5 | submitted prompt separate from live input |
| `03_drawer` | TUI-1, TUI-3 | bounded drawer cannot push composer |
| `04_queue_strip` | TUI-1, TUI-3 | one-line queue strip |
| `05_queue_drawer` | TUI-1, TUI-3 | queued draft editor is not live composer |
| `06_slash_picker` | TUI-2 | composer-attached slash picker |
| `07_file_picker` | TUI-2 | composer-attached file picker |
| `08_symbol_picker` | TUI-2 | composer-attached symbol picker |
| `09_plan_inline` | TUI-4a | useful plan without permanent dashboard |
| `10_review_approval` | TUI-4b | evidence-first approval |
| `11_diff_focus` | TUI-4b | focus mode replaces middle only |
| `12_protected_path` | TUI-4b | narrow protected-path approval |
| `13_network_ci_denied` | TUI-4b | network/CI denial separate from file approval |
| `14_recovery` | TUI-3 | draft preserved through recovery |
| `15_restore_focus` | TUI-4a | queue/session impact visible before restore |
| `16_sessions` | TUI-2, TUI-4a | session selection without shell duplication |
| `17_search_focus` | TUI-4a | focused search in middle region |
| `18_transcript_review` | TUI-4a | transcript review with composer visible |
| `19_status` | TUI-4a | effective status and policy resolution |
| `20_settings` | TUI-4a | settings as focus mode |
| `21_large_paste` | TUI-3 | paste handling preserves layout |
| `22_copy_fallback` | TUI-3, TUI-4a | copy fallback is visible and safe |
| `23_mcp_read_approval` | TUI-4b | scoped MCP read approval |
| `24_subagent_trace` | TUI-4c | opt-in subagent inspection |
| `25_ascii_fallback` | TUI-1, TUI-5 | ASCII fallback preserves structure |
| `26_exact_80x24` | TUI-1 | exact small-terminal contract |
| `27_command_center` | TUI-4c | opt-in command center |

## Required Validation Matrix

Every TUI implementation slice must store a filled checklist artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-tui-verification.md`.

Required commands depend on touched files, but the full TUI gate is:

```bash
make tui-regression
make tui-references
make tui-reference-gap
make tui-scene-matrix
uv run python autocode/tests/vhs/run_visual_suite.py
cd autocode/rtui && cargo test
cd autocode/rtui && cargo clippy -- -D warnings
```

Relevant PTY smoke commands from `autocode/tests/pty/README.md` must be run for any runtime or interaction change.

If a validation command cannot run, the QA artifact must state why, what evidence was collected instead, and whether the gap blocks promotion.

## Explicit Non-Goals Until Backend Is Complete

- No TUI implementation before backend harness solidification unless the user explicitly overrides.
- No v9 scene promotion without a live product capture.
- No replacement of the legacy 14-scene manifest in the first retargeting slice.
- No permanent dashboard, permanent side rails, or always-visible power-user panels.
- No broad approval/session scopes.
- No TUI work that hides backend harness false-pass, infra-classification, artifact, or retry issues.

## Review Questions

- Does this plan fully capture the TUI work remaining after the backend harness closeout?
- Is the manifest-versioning strategy correct: preserve legacy coverage while adding v9 coverage?
- Are the phase cuts right, especially the split between TUI-4a, TUI-4b, and TUI-4c?
- Is any v9 screen or shell-contract invariant missing?
- Are any backend dependencies required before the TUI can implement a listed screen honestly?
