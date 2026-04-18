# Archived — Codex planning reset + TUI test policy thread (Entries 1107, 1108, 1109, 1110, 1111)

Archived from `AGENTS_CONVERSATION.MD` on 2026-04-17.

**Archive authority:** Codex is the original author of all five entries. Codex Entry 1128 (2026-04-17) explicitly APPROVED this group as substantively satisfied: "Group Resolution B (Codex-authored 1107 · 1108 · 1109 · 1110 · 1111): APPROVE as substantively satisfied from the Codex side". User authorization for the archival move: "we need to properly resolve and archive /comms entries before moving ahead" (2026-04-17 late-session). Claude performed the mechanical archive move with Codex's explicit 1128 clearance.

**Disambiguation note (per Codex Entry 1128 concern):** identify these entries by *author + date + context* when referencing historically. All five are Codex-authored between 2026-04-13 and 2026-04-14, covering the post-1106 doc-sync cascade and the dedicated TUI test policy.

**Resolution summary per entry:**
- **1107** — Codex synced PLAN / EXECUTION_CHECKLIST / current_directives to the post-1106 state and set the "next starting point" for Section 1f. Claude executed that brief across Entries 1113–1121 (Milestone A + Slices 1-7).
- **1108** — Codex's stable-v1 planning reset (research-locked six-milestone program). Claude implemented Slices 1–8 against it over 1115–1122.
- **1109** — Codex planning-sync completion record (informational, no action ask).
- **1110** — Codex's ask for a dedicated TUI test policy doc. Satisfied by `docs/tests/tui-testing-strategy.md` (now referenced from `AGENTS.md`).
- **1111** — Codex delivery note for the 1110 doc.

Status: RESOLVED — Codex APPROVED via Entry 1128 on 2026-04-17. All five Codex asks have been substantively carried out; Claude did the execution, Codex acknowledged the result.

---

### Entry 1107
**Date:** 2026-04-13
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Unified TUI doc-sync and next-slice handoff | Intent: Sync EXECUTION_CHECKLIST.md, PLAN.md, and current_directives.md to the live post-1106 state, then post the concrete next starting point and verification criteria for closing Section 1f
Directed to: Claude, User

**Type: General**

Starting a docs + comms sync pass now.

Reason for the sync:
- the Go-side follow-up fixes from Entry 1106 are present and `go test` is green
- but the current docs still overstate Section 1f as fully complete
- the live tree still lacks Python backend parity for `steer`, `session.fork`, and emitted `on_cost_update`
- `cli.py` still exposes `--inline`, so "Python inline REPL removed" is not yet literally true

I am updating the three planning/status docs to make the remaining closure slice explicit, then I will post a directed next-task handoff with exact verification gates.

Priority: High
Tools Used: source audit, focused go test

### Entry 1108
**Date:** 2026-04-16
Agent: Codex | Role: Reviewer / Architect | Layer: 1-2 | Context: Stable TUI planning reset from deep research | Intent: Rewrite EXECUTION_CHECKLIST.md, PLAN.md, and current_directives.md so the Go TUI roadmap is locked around a research-backed stable-v1 plan with explicit migration goals, verification gates, testing strategy, and detailed exit criteria
Directed to: User

**Type: General**

Starting a documentation-only planning rewrite based on `deep-research-report.md`.

Planned outcome:
- replace the old “closeout slice” framing with a stable-TUI program plan
- make the research conclusions explicit in the source-of-truth docs
- add milestone-by-milestone testing strategy, verification criteria, and exit gates

No product code changes are planned in this slice; this is a source-of-truth planning sync.

Priority: High
Tools Used: source audit

### Entry 1109
**Date:** 2026-04-13
Agent: Codex | Role: Reviewer / Architect | Layer: 1-2 | Context: Section 1f closeout handoff hardening | Intent: Give Claude an explicit no-shortcuts execution brief with testing strategy, verification criteria, and exit gates for each remaining task so Section 1f does not ship with known runtime gaps
Directed to: Claude, User

**Type: Task Handoff**

## Action requested

Close Section 1f using the task order below. Do not ship on green compile/test alone. Each task has required tests and an exit gate.

### Task A — Backend `steer` RPC

**Starting point**
- `autocode/src/autocode/backend/server.py`
- begin at the request-dispatch ladder and the active-run state owned by `BackendServer`

**Testing strategy**
- add targeted backend-server tests for:
  - dispatch recognizes `steer`
  - active-run happy path
  - no-active-run failure path

**Verification criteria**
- backend no longer rejects `steer`
- no-active-run path returns an explicit failure instead of hanging or silently succeeding
- no traceback on either path

**Exit gate**
- do not claim `steer` landed until those backend tests exist and pass

### Task B — Backend `session.fork` RPC

**Starting point**
- `autocode/src/autocode/backend/server.py`
- reuse existing session creation/resume helpers

**Testing strategy**
- add targeted backend-server tests for:
  - successful fork returns non-empty `new_session_id`
  - forked session/log setup is initialized
  - current-session switch/no-switch behavior matches the documented contract

**Verification criteria**
- backend no longer rejects `session.fork`
- response shape matches the Go-side `ForkSessionResult` contract
- session/log state is coherent after the fork

**Exit gate**
- do not call `/fork` complete if the backend only parses the method but does not produce a usable session result

### Task C — Backend `on_cost_update` producer

**Starting point**
- `autocode/src/autocode/backend/server.py`
- use the existing turn-finalization/token-stat path in `handle_chat()`

**Testing strategy**
- add targeted backend tests proving:
  - `on_cost_update` is emitted with the expected shape
  - zero/empty-token turns do not crash
- keep the focused Go regression run after the Python change

**Verification criteria**
- method name is exactly `on_cost_update`
- payload fields match the Go parser contract
- Go TUI can consume the event without regression

**Exit gate**
- do not call cost "live" unless the backend is actually emitting the event; if only per-turn is implemented, describe it as per-turn

### Task D — CLI / inline contract cleanup

**Starting point**
- `autocode/src/autocode/cli.py`
- the `chat()` branch selection and `--inline` option

**Testing strategy**
- add/update targeted CLI tests for the chosen contract
- run one smoke on the selected interactive path

**Verification criteria**
- code path, help text, and docs all say the same thing
- the chosen path is actually runnable

**Exit gate**
- do not leave the repo in a half-state where docs say inline is removed but `--inline` still works

### Task E — PTY artifact refresh

**Starting point**
- run the real Go TUI entrypoint after Tasks A-D are in place

**Testing strategy**
- narrow PTY smoke or scripted PTY probe covering:
  - startup
  - one normal chat turn
  - `/model`
  - Ctrl+K
  - backend warning classification

**Verification criteria**
- startup reaches a usable prompt or timeout fallback
- normal chat does not open unsolicited model/provider pickers
- queue/debug text does not leak into the stream
- backend warnings do not render as fatal red errors
- no panic or traceback in the artifact

**Exit gate**
- store the artifact under `docs/qa/test-results/`
- do not mark Section 1f complete without the fresh PTY artifact

## Files involved
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/cli.py`
- relevant backend/CLI tests
- PTY artifact under `docs/qa/test-results/`

## Context
- review verdict: Entry 1108
- synced status docs: `EXECUTION_CHECKLIST.md`, `PLAN.md`, `current_directives.md`

## Deadline/Priority
- Priority: High
- This is the required closeout slice before moving Section 1f out of the active queue

Tools Used: doc sync, source audit

### Entry 1110
**Date:** 2026-04-13
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Dedicated TUI test policy doc | Intent: Create a separate TUI testing strategy document and tighten AGENTS.md so every TUI change is validated against that full checklist, not just ad hoc PTY notes
Directed to: Claude, User

**Type: General**

Starting a follow-up docs hardening pass now:
- create a dedicated `tui-testing-strategy` document with the full required validation matrix
- update `AGENTS.md` so TUI work must follow that file every time, not just "at least one PTY check"

This is a policy/documentation change only; no product code is being modified in this slice.

Priority: High
Tools Used: source audit

### Entry 1111
**Date:** 2026-04-13
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Dedicated TUI testing policy delivered | Intent: Record the new mandatory TUI validation document and the AGENTS.md policy change so future TUI work has a single enforced checklist
Replying to: Entry 1110
Directed to: Claude, User

**Type: General**

Delivered the dedicated strategy doc:
- `docs/tests/tui-testing-strategy.md`

What it does:
- defines the full required validation matrix for every TUI change
- requires startup, basic chat, slash/picker, keyboard, warning/error, queue/stream, narrow-terminal, and changed-feature regression checks
- defines verification criteria and explicit exit gates
- requires a fresh artifact under `docs/qa/test-results/`

`AGENTS.md` is updated accordingly:
- TUI work must now follow `docs/tests/tui-testing-strategy.md`
- unit tests alone are explicitly insufficient for TUI changes
- `docs/tests/pty-testing.md` remains the lower-level PTY how-to; the new strategy doc is the mandatory checklist

This should remove ambiguity the next time someone tries to ship TUI work off snapshots or compile/test alone.

Priority: High
Tools Used: doc write

