# pty/ — Live PTY Smoke Harnesses and Mock Backends

**One of four TUI testing dimensions.** See
`docs/tests/tui-testing-strategy.md` for the matrix and how to pick
between them.

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
| `pty_phase1_fixes_test.py` | Phase 1 + Phase 3-6 fix regressions (startup, slash commands, classification, streaming) | Go TUI binary + mock backend |
| `pty_smoke_backend_parity.py` | Go TUI startup, `/help`, `/model`, `/cost`, backend parity smoke | Go TUI binary + mock backend |
| `pty_tui_bugfind.py` | Bug-finder — drives the TUI through many scripted scenarios looking for visible regressions | Go TUI binary + mock backend |
| `pty_narrow_terminal_test.py` | Narrow-geometry rendering at ≤80 cols | Go TUI binary + mock backend |
| `pty_e2e_real_gateway.py` | Live gateway end-to-end (trivial prompt only) | Gateway reachable + `LITELLM_MASTER_KEY` |
| `pty_deep_bugs.py` | Deeper slash-command / palette bug hunt on the legacy Python inline path (being removed) | Python inline REPL via `--inline` |

Each script is designed to be run directly:

```bash
uv run python autocode/tests/pty/<script>.py
```

Most scripts exit non-zero on any regression and print a summary of
bug counts. The bug-finder scripts additionally write timestamped
artifacts under `autocode/docs/qa/` (see [Artifacts](#artifacts)).

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
Go TUI.

---

## How to run

**Phase 1 regression (most commonly run before a TUI PR):**

```bash
uv run python autocode/tests/pty/pty_phase1_fixes_test.py
```

**Backend-parity smoke (5 scenarios, ~15 s):**

```bash
uv run python autocode/tests/pty/pty_smoke_backend_parity.py
```

**Bug-finder (broad scripted sweep, ~60 s):**

```bash
uv run python autocode/tests/pty/pty_tui_bugfind.py
```

**Narrow terminal (60×20 cells):**

```bash
uv run python autocode/tests/pty/pty_narrow_terminal_test.py
```

**Live gateway end-to-end (requires running LLM gateway):**

```bash
# Preflight: gateway must be reachable.
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:4000/health

uv run python autocode/tests/pty/pty_e2e_real_gateway.py
```

---

## Environment requirements

**Go TUI binary.** All harnesses spawn `autocode/build/autocode-tui` or
whatever `$AUTOCODE_TUI_BIN` points at. Build it with:

```bash
cd autocode/cmd/autocode-tui \
  && GOROOT=/usr/lib/go-1.24 PATH=/usr/lib/go-1.24/bin:$PATH \
     go build -o ../../build/autocode-tui .
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
- **Python inline is being removed.** `pty_deep_bugs.py` targets the
  legacy inline REPL; do not add new harnesses on that path. Use the Go
  TUI for new work.
- **Kitty keyboard-protocol sequences** (`CSI-u`) can leak into pyte
  grids if not stripped. See `autocode/tests/vhs/renderer.py` for the
  pre-filter; `tui-comparison/predicates.py` reuses that logic.
