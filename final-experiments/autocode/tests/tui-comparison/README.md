# tui-comparison — Track 1 Runtime-Invariant Harness

**One of four TUI testing dimensions.** See
`docs/tui-testing/tui-testing-strategy.md` for the matrix and how to pick
between them.

This tree answers: **"Does the Rust TUI still satisfy its runtime
invariants?"** — no crash, composer visible, warnings not rendered as
errors, pickers filterable, spinners tick, queues not leaking, etc.

Not this tree's job:

- Visual regressions → `autocode/tests/vhs/`
- Design-target parity against the mockup bundle → `autocode/tests/tui-references/`
- Live-gateway end-to-end → `autocode/tests/pty/`

---

## Contents

- [Purpose](#purpose)
- [Files and responsibilities](#files-and-responsibilities)
- [How to run](#how-to-run)
- [Scenarios](#scenarios)
- [Predicates (hard vs soft)](#predicates-hard-vs-soft)
- [Artifacts](#artifacts)
- [Mock backend vs live gateway](#mock-backend-vs-live-gateway)
- [Adding a scenario](#adding-a-scenario)
- [Caveats](#caveats)

---

## Purpose

Runtime-invariant gate. Runs the real `autocode-tui` Rust binary in a PTY,
drives each scenario's scripted input, and asserts a set of
deterministic predicates on the pyte-rendered output. Hard predicates
fail the build. Soft predicates are Track 3 (style-gap) backlog data
and do not gate.

Canonical architecture source: **`PLAN.md` §1g** — specifically the
Track 1 section and the "Predicate Classification" section listing the
11 enforced hard invariants.

Review chain: `AGENTS_CONVERSATION.MD` Entries 1137 → 1175 (Phase 1 + 2
land + remediation).

---

## Files and responsibilities

```
autocode/tests/tui-comparison/
├── __init__.py              # package marker
├── capture.py               # PTY fork + scripted-input driver + DSR responder glue
├── dsr_responder.py         # shim that answers child TUI's terminal queries so it doesn't hang
├── predicates.py            # hard + soft predicates on a pyte Screen
├── profile.py               # TermProfile — captures terminal env for artifact provenance
├── run.py                   # CLI runner (one scenario at a time → 5 artifacts)
├── launchers/
│   ├── __init__.py
│   └── autocode.py          # LaunchSpec for the autocode binary + mock-backend env
├── scenarios/               # one file per driven scenario — NAME + steps + drain timings
│   ├── startup.py
│   ├── first_prompt_text.py
│   ├── model_picker.py
│   ├── ask_user_prompt.py
│   ├── error_state.py
│   ├── orphaned_startup.py
│   └── spinner_cadence.py
└── tests/
    └── test_substrate.py    # 35 unit tests covering the predicates + helpers in isolation
```

---

## How to run

**Full Track 1 via Makefile (what CI runs):**

```bash
make tui-regression
```

Runs the 7 scenarios sequentially, then the substrate unit tests.
Fails with non-zero exit on any hard-invariant predicate failure.

**One scenario at a time:**

```bash
uv run python autocode/tests/tui-comparison/run.py startup
uv run python autocode/tests/tui-comparison/run.py first-prompt-text
uv run python autocode/tests/tui-comparison/run.py model-picker
uv run python autocode/tests/tui-comparison/run.py ask-user-prompt
uv run python autocode/tests/tui-comparison/run.py error-state
uv run python autocode/tests/tui-comparison/run.py orphaned-startup
uv run python autocode/tests/tui-comparison/run.py spinner-cadence
```

Each run produces a timestamped artifact directory with the 5 files
listed under [Artifacts](#artifacts) and exits non-zero if any hard
predicate fails.

**Substrate unit tests only (no PTY, no binary — ~1 s):**

```bash
uv run pytest autocode/tests/tui-comparison/tests/ -v
```

---

## Scenarios

The 7 currently-driven scenarios (see `run.py::SCENARIO_MODULES`):

| Name | Drives the TUI into | What it proves |
|---|---|---|
| `startup` | Cold boot, no input | Startup reaches usable state; no crash |
| `first-prompt-text` | Send one plain message → drain reply | Basic turn cycle is clean |
| `model-picker` | Open `/model`, type filter chars | Picker filter accepts input, composer is N/A |
| `ask-user-prompt` | Send a chat that triggers an `on_ask_user` modal | Keyboard-interactive approval prompt renders |
| `error-state` | Mid-session WARNING to stderr | Warning renders dim, not as a red `Error:` banner |
| `orphaned-startup` | Silent backend (never emits `on_status`) | Startup timeout fires with canonical banner |
| `spinner-cadence` | `__SLOW__` trigger → long pause | Spinner actually rotates over time (≥2 distinct braille glyphs) |

---

## Predicates (hard vs soft)

Hard predicates (currently 11) gate `make tui-regression`. Soft
predicates are Track 3 backlog data. Full list lives in
`predicates.py` and is documented in `PLAN.md` §1g "Predicate
Classification".

The 11 enforced hard invariants:

1. `no_crash_during_capture`
2. `composer_present` (N/A for picker + ask-user scenarios)
3. `no_queue_debug_leak`
4. `basic_turn_returns_to_usable_input`
5. `spinner_observed_during_turn`
6. `response_followed_user_prompt`
7. `picker_filter_accepts_input`
8. `approval_prompt_keyboard_interactive`
9. `warnings_render_dim_not_red_banner`
10. `startup_timeout_fires_when_backend_absent`
11. `spinner_frame_updates_over_time`

Every predicate is scenario-aware: for scenarios it does not apply to,
the predicate returns `PASS` with `detail="N/A — scenario <name> has no
turn"` (or similar). This keeps the gate honest across the mixed set.

---

## Artifacts

Each run writes five files under
`autocode/docs/qa/tui-comparison/regression/<run-id>/<scenario>/`:

| File | Contents |
|---|---|
| `autocode.raw` | Raw ANSI byte stream captured from the PTY |
| `autocode.txt` | pyte-rendered stripped text (same view the predicates saw) |
| `autocode.png` | Rendered PNG via the sibling VHS renderer (skipped if Pillow unavailable) |
| `autocode.profile.yaml` | TermProfile — TERM, COLORTERM, rows, cols, boot_budget_s, DSR shim version, DSR responses served |
| `predicates.json` | Hard + soft verdicts with per-predicate `detail` fields |

Per-run IDs are `YYYYMMDD-HHMMSS` local time. Artifacts are not
committed — regenerate on demand.

---

## Mock backend vs live gateway

Track 1 uses a **deterministic mock backend** via `AUTOCODE_PYTHON_CMD`
(`autocode/tests/pty/mock_backend.py`). No external gateway, no
rate-limit exposure, no LLM-quality variance.

- Scenario triggers in mock backend: `__ASK_USER__`, `__WARNING__`,
  `__SLOW__` (see `autocode/tests/pty/mock_backend.py`).
- `orphaned-startup` uses `autocode/tests/pty/silent_backend.py` (never
  emits `on_status`, triggers the 15 s startup-timeout path).
- Live-gateway coverage is the **separate** responsibility of
  `autocode/tests/pty/` — see that tree's README.

---

## Adding a scenario

1. Create `scenarios/<name>.py`:
   ```python
   from dataclasses import dataclass
   NAME = "<name>"

   @dataclass
   class ScenarioSpec:
       name: str
       steps: list[float | str]   # float = sleep seconds; str = bytes to send
       drain_quiet_s: float
       drain_maxwait_s: float

   def spec() -> ScenarioSpec:
       return ScenarioSpec(name=NAME, steps=[...], drain_quiet_s=..., drain_maxwait_s=...)
   ```
2. If the scenario needs a non-default launcher (e.g., silent backend),
   export `LAUNCHER_KWARGS = {...}`.
3. Register in `run.py::SCENARIO_MODULES`.
4. Register in `Makefile::tui-regression`.
5. Add any new predicate family to `predicates.py` with its
   `_TURN_SCENARIOS` / similar set membership so it returns N/A on
   scenarios it does not apply to.
6. Add unit coverage to `tests/test_substrate.py`.

---

## Caveats

- **Hyphenated directory.** `tui-comparison/` has a hyphen; Python's
  normal import machinery cannot reach it. `run.py` adds the directory
  to `sys.path` at the top. Tests that want to reuse the substrate (see
  `autocode/tests/tui-references/test_reference_scenes.py`) also do this.
  This produces a pre-existing `ruff N999` warning baseline on the
  `__init__.py` files.
- **Boot budgets matter.** Scenarios that exercise a timeout (e.g.,
  `orphaned-startup`) MUST set `LAUNCHER_KWARGS = {"boot_budget_s":
  <value>}` exceeding the TUI's timeout threshold, or the capture will
  end before the timeout fires.
- **DSR responder.** Many terminal-control sequences (`CSI 6n`, `CSI c`,
  `CSI ?u`, `OSC 10;?`) must be answered synchronously or the TUI
  hangs. `dsr_responder.py` handles this transparently.
- **PNG is optional.** If Pillow or the VHS renderer fails to import,
  the `.png` is skipped with a `.png.skipped` marker file. The
  `.raw` and `.txt` are the primary gate signal.
- **Rust TUI binary:** set `$AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui` to retarget the harness at the Rust implementation. The launcher in `launchers/autocode.py` resolves the binary from this env var.
