# pty/ — Live PTY Smoke Harnesses and Mock Backends

**One of four TUI testing dimensions.** See
`docs/tui-testing/tui-testing-strategy.md` for the matrix and how to pick
between them. The enforced per-change checklist lives at
`docs/tui-testing/tui_testing_checklist.md`.

This tree answers: **"Does the real `autocode-tui` binary work
end-to-end in a real terminal, with either the real Python backend or
a deterministic mock?"**

Not this tree's job:

- Runtime invariants on a mock backend → `autocode/tests/tui-comparison/` (Track 1)
- Design-target parity against the mockup bundle → `autocode/tests/tui-references/` (Track 4)
- Self-vs-self PNG regression → `autocode/tests/vhs/`

---

## Contents

- [Purpose](#purpose)
- [Scripts inventory](#scripts-inventory)
- [Backend stubs](#backend-stubs)
- [How to run](#how-to-run)
- [Environment requirements](#environment-requirements)
- [Artifacts](#artifacts)
- [Adding a harness](#adding-a-harness)
- [Caveats](#caveats)

---

## Purpose

Live PTY tests prove the real binary + real backend path is still
coherent. They complement the Track 1 gate by hitting **code paths the
mock backend cannot cover** (live LLM gateway, real startup timeouts,
real narrow-terminal rendering, bug-hunting scenarios).

Most live-gateway harnesses are rate-limit-aware: they use a trivial
prompt (e.g. `/help`) or mock where possible.

---

## Scripts inventory

### Executable test harnesses (run as Python scripts)

| Script | Scope | Requires |
|---|---|---|
| `pty_smoke_rust_m1.py` | M1 evidence: backend spawn + `on_status` render + `/exit` clean exit | Rust binary + mock backend |
| `pty_smoke_rust_comprehensive.py` | Broader Rust smoke (currently S1 on_status + S2 /exit; S3–S6 for streaming/plan/Ctrl+C/fork are aspirational in docstring but not implemented yet) | Rust binary + mock backend |
| `pty_e2e_real_gateway.py` | **STALE — hardcodes deleted `autocode/build/autocode-tui`; retarget or delete before using** | was Go TUI; needs Rust retarget |

Each script is designed to be run directly:

```bash
python3 autocode/tests/pty/<script>.py
```

Most scripts exit non-zero on any regression and print a summary of
bug counts. Artifacts land under `autocode/docs/qa/test-results/`
with `<YYYYMMDD-HHMMSS>-` prefix.

**Historical note:** `pty_phase1_fixes_test.py`, `pty_smoke_backend_parity.py`,
`pty_tui_bugfind.py`, `pty_narrow_terminal_test.py`, `pty_deep_bugs.py` were
Go-era harnesses deleted on 2026-04-19 after the Rust cutover. Rust-flavored
replacements live in `pty_smoke_rust_*.py`.

---

## Backend stubs

Non-executable stubs used by the harnesses above (not standalone
tests):

| Stub | Role |
|---|---|
| `mock_backend.py` | Deterministic JSON-RPC mock. Triggers in the chat body: `__ASK_USER__`, `__WARNING__`, `__SLOW__`. Shared with `autocode/tests/tui-comparison/`. |
| `silent_backend.py` | Starts, reads stdin, **never** emits `on_status`. Used to exercise the TUI's 15 s startup-timeout path. |
| `dead_backend.py` | Sleeps forever. Legacy variant; prefer `silent_backend.py`. |

Stubs are selected via `AUTOCODE_PYTHON_CMD=<path>` when spawning the
Rust TUI. The Rust binary appends `serve` as argv[1]; stubs ignore it
via their shebang (`#!/usr/bin/env python3`) and their `__main__` block.

---

## How to run

**M1 scaffold evidence (most commonly run after any TUI change):**

```bash
python3 autocode/tests/pty/pty_smoke_rust_m1.py
```

**Broader smoke (S1 + S2 only today):**

```bash
python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py
```

**Live gateway end-to-end (STALE — needs retarget):**

```bash
# pty_e2e_real_gateway.py currently hardcodes the deleted Go binary path.
# Do not use until retargeted to autocode/rtui/target/release/autocode-tui
# and updated to honor $AUTOCODE_TUI_BIN.
```

---

## Environment requirements

**Rust TUI binary.** All harnesses spawn
`autocode/rtui/target/release/autocode-tui` or whatever
`$AUTOCODE_TUI_BIN` points at. Build it with:

```bash
cd autocode/rtui && cargo build --release
```

**Mock backend.** Shipped in this directory; no install needed.

**Live gateway (only for `pty_e2e_real_gateway.py`).** The LiteLLM
gateway must be running and reachable. Auth is derived via
`LITELLM_MASTER_KEY` → `LITELLM_API_KEY` → `OPENROUTER_API_KEY`. Per
the repo's operating rules: **never restart the gateway yourself** —
if it's down, report and wait.

---

## Artifacts

Bug-finder harnesses emit timestamped markdown artifacts under
`autocode/docs/qa/` (path varies per script — see each script's
header). Failing runs produce a concise bug report with severities
(LOW / MEDIUM / HIGH / CRITICAL) and example outputs.

---

## Adding a harness

1. Start a new Python script in this directory. Use `pty.fork()` +
   `select`, or reuse the driver from
   `autocode/tests/tui-comparison/capture.py` if the scenario shape
   fits.
2. If the harness needs a new backend behavior, add a trigger keyword
   to `mock_backend.py::_handle_chat()` (e.g. `__DIFF_STREAM__` for a
   new streaming shape).
3. If the harness needs a brand-new backend shape (e.g. a backend
   that emits malformed JSON), add a new stub alongside
   `silent_backend.py` / `dead_backend.py`.
4. Document the new script in this README's inventory table.
5. Consider whether Track 1 (`autocode/tests/tui-comparison/`) can
   absorb the scenario instead — if it's deterministic and mockable,
   Track 1 is the better home because it runs in CI.

---

## Caveats

- **PTY is not hermetic.** Wall-clock timing, terminal environment,
  and host load all affect runs. Budget generously and treat one-off
  hangs as environmental, not as test signal — unless they're
  reproducible.
- **Live-gateway harness is rate-limit-aware.** Keep new harnesses
  under that umbrella small-and-trivial; do NOT add a harness that
  makes many real LLM calls. Broad benchmarking lives in
  `benchmarks/`.
- **Python inline and Go TUI were deleted at M11 (2026-04-19).** New
  harnesses must target the Rust binary at
  `autocode/rtui/target/release/autocode-tui`; do not add harnesses on
  the legacy Go or Python-inline paths.
- **Kitty keyboard-protocol sequences** (`CSI-u`) can leak into pyte
  grids if not stripped. See `autocode/tests/vhs/renderer.py` for the
  pre-filter; `tui-comparison/predicates.py` reuses that logic.
