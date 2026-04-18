# AutoCode TUI Visual Snapshot Pipeline

Pure-Python (`pyte` + `Pillow`) pipeline for capturing and diffing PNG
snapshots of the AutoCode Go BubbleTea TUI. Named after upstream
[charm.sh/vhs](https://github.com/charmbracelet/vhs) for familiarity — the
VHS tool itself needs `ttyd` which couldn't be installed without root on
this host, so we built the same shape with lighter deps.

---

## Contents

- [Purpose and scope](#purpose-and-scope)
- [What this pipeline can and cannot do](#what-this-pipeline-can-and-cannot-do)
- [Files and responsibilities](#files-and-responsibilities)
- [Data flow](#data-flow)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Where artifacts are stored](#where-artifacts-are-stored)
- [Adding a new scenario (walkthrough)](#adding-a-new-scenario-walkthrough)
- [Baseline update policy](#baseline-update-policy)
- [Cross-tool comparison (Claude Code, Pi Code, OpenCode)](#cross-tool-comparison-claude-code-pi-code-opencode)
- [Tolerance + how to read the diff image](#tolerance--how-to-read-the-diff-image)
- [CI integration](#ci-integration)
- [Troubleshooting](#troubleshooting)
- [Caveats and known limits](#caveats-and-known-limits)
- [Future work](#future-work)

---

## Purpose and scope

Text-level PTY tests (`autocode/tests/pty/*.py`) already catch:
- startup crashes
- slash-command routing
- warning/error classification
- queue leakage into visible output

They do **not** catch:
- visual regressions (color drift, layout shift, overlapping frames)
- alt-screen handling glitches
- picker cursor/marker placement
- rendering differences when the TUI is swapped with a different
  terminal agent for migration parity

This pipeline fills that gap by rendering the TUI's ANSI output stream
to PNG and comparing against a committed baseline.

---

## What this pipeline can and cannot do

### Can

- Capture the TUI rendering produced by **real scripted scenarios**
- Detect **self-vs-self regressions** — if the layout/text/colors shift
  between runs, the diff image highlights the changed pixels
- Act as a regression gate for Milestone A picker-filter behavior
  (`model_picker_filtered` scenario)
- Produce timestamped summary artifacts that can be attached to comms
  posts or review notes

### Cannot (and why)

- **Reproduce a specific terminal emulator's exact rendering.** `pyte`
  emulates a generic xterm-compatible terminal. Alacritty / WezTerm /
  Ghostty render the same ANSI stream differently (font metrics,
  subpixel antialias, cursor block shape). Cross-tool comparison is
  **structural**, not pixel-perfect — see caveats below.
- **Capture alt-screen teardown state.** When the TUI exits via Ctrl+D,
  BubbleTea restores the saved primary buffer and the pyte Screen shows
  that post-exit state instead of the running TUI. All scenarios run
  with `graceful_exit=False` for this reason; the process is SIGTERM'd
  while still in alt-screen.
- **Parse kitty keyboard-protocol sequences** (CSI-u). `pyte` mis-parses
  those and leaks literals like `0;1u` into the cell grid. The renderer
  strips them via a regex pre-filter (`_KITTY_KEYBOARD_PROTO` in
  `renderer.py`) before feeding pyte.
- **Handle animated spinner frames deterministically.** The TUI emits a
  rotating spinner character; between captures the frame differs by a
  few cells. Tolerance absorbs this — see "Tolerance" below.

---

## Files and responsibilities

```
tests/vhs/
├── __init__.py             # marks the package + module-docstring
├── capture.py              # PTY spawn, scripted keystroke replay, byte drain
├── renderer.py             # pyte Screen → PNG via Pillow + DejaVu Sans Mono
├── differ.py               # Pillow ImageChops pixel diff + highlight-image output
├── scenarios.py            # canonical SCENARIOS list (name, steps, geometry)
├── run_visual_suite.py     # CLI runner (--update / default diff mode)
├── reference/              # committed baseline PNGs per scenario
│   ├── startup.png
│   ├── model_picker_open.png
│   ├── model_picker_filtered.png
│   └── palette_open.png
└── README.md               # this file

tests/unit/
└── test_vhs_differ.py      # 9 unit tests for the pixel-diff logic
```

Each module is deliberately small and single-purpose. Read them in the
order above and the whole pipeline fits in about 700 LOC.

---

## Data flow

```
Scenario                       capture.py                     renderer.py
  │                                │                              │
  │─── name + keystrokes ─────────▶│                              │
  │                                │  spawn pty_openpty            │
  │                                │  fork + execve autocode-tui   │
  │                                │  drain initial frames         │
  │                                │  for each step:               │
  │                                │    write keystrokes           │
  │                                │    drain byte deltas          │
  │                                │  SIGTERM (not Ctrl+D)         │
  │                                │                               │
  │                                │─── raw ANSI bytes ───────────▶│
  │                                │                              strip kitty-u
  │                                │                              pyte.ByteStream
  │                                │                              pyte.Screen
  │                                │                                 │
  │                                │                                 ▼
  │                                │                              Cell grid
  │                                │                                 │
  │                                │                              Pillow paint
  │                                │                              DejaVu Sans Mono
  │                                │                                 │
  │                                │                                 ▼
  │                                │                              candidate.png
  │
  │          differ.py
  │          ──────────
  │  candidate + reference ── ImageChops.difference
  │                               ├── per-channel max via lighter-of-RGB
  │                               ├── threshold mask via .point()
  │                               ├── mismatched pixel count via histogram
  │                               └── Image.composite(highlight, dim_ref, mask)
  │                                   → candidate.diff.png
  │
  │          run_visual_suite.py
  │          ────────────────────
  │  aggregate per-scenario results + write summary markdown
```

**Key invariant:** everything downstream of the scenario is deterministic
given the same ANSI bytes. Non-determinism is concentrated in
`capture.py` (real-time scheduling, spinner frames, backend latency) —
which is why tolerance exists.

---

## Dependencies

- **`pyte`** — pure-Python terminal emulator. `uv add --dev pyte`.
  Version pinned in `autocode/pyproject.toml` dev-deps.
- **`Pillow`** — image library. `uv add --dev Pillow`. Used for rendering
  and pixel diff. No numpy dependency.
- **DejaVu Sans Mono** — monospace font. Expected at
  `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf` on most Linux
  hosts. Override via `RenderOptions(font_path=...)` in
  `renderer.py`.

**No external binaries.** No `ttyd`, no `ffmpeg`, no `ImageMagick`. The
pipeline runs in any Python environment with the two dev deps above.

---

## Usage

### First run: capture baselines

```bash
cd /home/bs01763/projects/ai/lowrescoder
uv run python autocode/tests/vhs/run_visual_suite.py --update
```

This captures every scenario defined in `scenarios.py::SCENARIOS` and
**overwrites** the stored reference PNG at
`autocode/tests/vhs/reference/<name>.png`.

Commit the updated reference PNGs alongside code changes that
intentionally change visual output (see
[Baseline update policy](#baseline-update-policy)).

### Regression run

```bash
uv run python autocode/tests/vhs/run_visual_suite.py
```

Captures a fresh candidate under
`autocode/docs/qa/vhs/candidates/<stamp>/<name>.png`, diffs against the
committed reference, writes a highlight-diff image
(`<scenario>.diff.png`) showing changed pixels in red over a dimmed
reference, and exits non-zero on any mismatch above tolerance.

A summary markdown lands at
`autocode/docs/qa/test-results/<stamp>-vhs-visual-suite.md` with
per-scenario status, mismatch ratio, max channel delta, and paths.

### Tighten / loosen tolerance

```bash
# Near-exact match (0.1%)
uv run python autocode/tests/vhs/run_visual_suite.py --pixel-ratio 0.001

# Lenient (5%) — for scenarios known to have wide spinner jitter
uv run python autocode/tests/vhs/run_visual_suite.py --pixel-ratio 0.05
```

Default is 1%.

---

## Where artifacts are stored

Three layers, in increasing volatility:

| Layer | Path | Committed to git? |
|---|---|---|
| Baselines | `autocode/tests/vhs/reference/*.png` | Yes — these are the regression gate |
| Candidates + diff images | `autocode/docs/qa/vhs/candidates/<stamp>/` | No — per-run only |
| Summary markdown | `autocode/docs/qa/test-results/<stamp>-vhs-visual-suite.md` | Depends on QA retention policy |

**Disk budget:** each candidate run produces 4 PNGs (~80KB total) +
optional diff PNGs (~50KB each when mismatches exist) + a ~2KB summary
markdown. Roughly ~250KB per run. Ten runs ≈ 2.5MB. Not disk-hungry.

---

## Adding a new scenario (walkthrough)

Scenario: we want a baseline for the `/cost` slash command.

### 1. Append to `scenarios.py`

```python
SCENARIOS: list[Scenario] = [
    # ...existing scenarios...
    Scenario(
        name="cost_view",
        steps=[
            0.8,            # wait for header to render
            "/cost\n",      # invoke /cost
            1.0,            # wait for session-store query + render
        ],
        drain_maxwait_s=5.0,
        graceful_exit=False,
    ),
]
```

### 2. Capture the baseline

```bash
uv run python autocode/tests/vhs/run_visual_suite.py --update
```

This generates `autocode/tests/vhs/reference/cost_view.png`. Open the
file and eyeball it — if the render matches what you see in a live TUI,
proceed. If not, tune the `steps` delays (see
[Troubleshooting](#troubleshooting)) and re-capture.

### 3. Commit the reference + scenario change

```bash
git add autocode/tests/vhs/scenarios.py autocode/tests/vhs/reference/cost_view.png
git commit -m "vhs: add cost_view scenario"
```

### 4. Verify regression mode sees zero mismatch

```bash
uv run python autocode/tests/vhs/run_visual_suite.py
```

Expected: `cost_view` reports `ok — mismatch 0/... (0.0000%)` (or at
least `within tolerance`).

---

## Baseline update policy

When to `--update`:

- The TUI layout intentionally changed (new panel, new column, header
  redesign)
- A scenario's input/timing changed (e.g., you tuned the delay)
- Terminal geometry changed (default is 160×50 — changing this will
  invalidate all baselines)
- Font changed (DejaVu Sans Mono is our anchor; different font → all
  baselines invalid)

When NOT to `--update`:

- The diff highlights a bug you haven't fixed yet. Fix the bug, then
  re-run regression mode. Don't bury a regression under a new baseline.
- Spinner noise is making the diff flaky. Loosen `--pixel-ratio` or
  redesign the scenario to pause *after* the spinner tick stops.

**Merge-conflict handling:** PNG files are binary. If two branches both
update the same reference PNG, git can't auto-merge. Resolution:

1. Checkout the feature branch.
2. Rerun `--update` to regenerate the PNG from the current scenario
   state on that branch.
3. Commit the regenerated PNG.
4. Merge.

Don't try to manually diff binary PNG blobs.

---

## Cross-tool comparison (Claude Code, Pi Code, OpenCode)

Goal: show that AutoCode's TUI renders "close enough" to another coding
TUI for migration parity.

### What works

- **Structural comparison:** same ANSI stream → same pyte Screen → same
  PNG. If both tools emit similar ANSI for the same user input, the
  pipeline shows it.

### What doesn't

- **Pixel-for-pixel comparison against a real terminal screenshot**
  (e.g. a Ghostty screenshot of Claude Code). Different font, different
  antialias, different palette. You'll get 100% mismatch even if the
  layouts are visually identical.

### Recommended workflow for cross-tool

1. **Capture the other tool using the same pipeline shape.** Spawn the
   other tool's binary (e.g., `claude`) in a PTY at 160×50, collect its
   ANSI output stream, feed through `feed_ansi_to_screen()`, and render
   via `render_screen_to_png()`. This keeps font + palette + rendering
   constant across tools.
2. **Drop the produced PNG into
   `autocode/tests/vhs/reference/<scenario>-foreign.png`** (a naming
   convention; the runner will only diff against same-name references).
3. **Write a small comparison helper** that diffs two
   `autocode/tests/vhs/reference/<name>.png` files of different tool
   origins. Not provided out of the box.

A proper cross-tool harness is **future work** (see below). Today the
committed references are AutoCode-only self-baselines.

---

## Tolerance + how to read the diff image

Two knobs:

- `--pixel-ratio` (default 0.01) — fraction of pixels that may mismatch
  before the scenario fails
- `threshold` inside `differ.py` (default 10) — per-channel RGB delta
  below which a pixel is considered "unchanged" (absorbs antialias
  jitter)

### Diff image reading

When a mismatch is detected, `run_visual_suite.py` writes
`<scenario>.diff.png` next to the candidate PNG. The image has two
layers:

- **Dimmed reference** (reference PNG with each RGB channel divided by
  3) — gives spatial context so you can see WHERE on the screen the
  diff is
- **Red (default) mask** — every pixel whose candidate differs from
  reference by more than `threshold` on any channel

Interpreting:

- A few scattered red dots → antialias jitter or spinner frame; probably
  fine, consider loosening `--pixel-ratio`
- A contiguous red block in the status bar → status text or model name
  changed
- Red covering a whole row → a new line was inserted; baseline is stale
- Red covering the cursor region → cursor blink or focus state
  difference — usually harmless

### Adjusting threshold

The `threshold` is hard-coded at `10` in `differ.py::diff_images`. If
you need a different value, expose it via a CLI flag or pass it
explicitly at the call site in `run_visual_suite.py`. Bump it up when
rendering on a host with noticeably different antialias (e.g., a Mac
with subpixel AA); keep it at 10 on Linux CI hosts.

---

## CI integration

The visual suite is **not** wired into CI today. To add it:

### GitHub Actions (sketch)

```yaml
- name: TUI visual regression
  run: |
    uv sync --group dev
    uv run python autocode/tests/vhs/run_visual_suite.py
- name: Upload diff artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: vhs-diff-${{ github.run_id }}
    path: autocode/docs/qa/vhs/candidates/
```

### Pre-commit (sketch)

```yaml
- repo: local
  hooks:
    - id: vhs-regression
      name: TUI visual regression
      entry: uv run python autocode/tests/vhs/run_visual_suite.py
      language: system
      pass_filenames: false
      stages: [pre-push]
```

### Make target (sketch)

```make
vhs-test:
	uv run python autocode/tests/vhs/run_visual_suite.py

vhs-update:
	uv run python autocode/tests/vhs/run_visual_suite.py --update
```

Run on a **single fixed host** (or container) to avoid font/antialias
drift across CI agents.

---

## Troubleshooting

### Candidate PNG is mostly black

**Cause:** the scenario's drain didn't give the TUI enough time to
render its alt-screen content, OR the TUI printed a clear-screen code
right before capture ended.

**Fix:** increase `drain_maxwait_s` in the Scenario definition, OR add a
terminal sleep (float) after the last keystroke in `steps`.

### Candidate PNG has garbage text like `0;1u`

**Cause:** pyte couldn't parse the kitty keyboard-protocol CSI-u
sequence. This should be handled by
`renderer.py::_KITTY_KEYBOARD_PROTO`.

**Fix:** inspect the raw ANSI. If new escape-sequence families are
leaking, extend `_KITTY_KEYBOARD_PROTO` to cover them.

### All scenarios report 100% mismatch on a fresh run

**Cause:** font metrics changed (different host, different font version,
different DPI).

**Fix:** regenerate baselines with `--update` on the target host.
Commit the new baselines.

### `no reference at ...` warning

**Cause:** the scenario name exists in `scenarios.py` but no
corresponding `reference/<name>.png` is committed.

**Fix:** run `--update` once to seed it.

### Scenario intermittently hits > tolerance mismatch

**Cause:** spinner frame or status-bar timestamp jitter.

**Fix:** either (a) tune scenario timing to pause at a quiescent moment,
(b) loosen `--pixel-ratio`, or (c) add a mask that excludes
spinner/clock cells (not implemented today; future work).

### Binary not found at `build/autocode-tui`

**Cause:** the Go binary wasn't built after a source change, or the
canonical output path is stale.

**Fix:** rebuild into `autocode/build/autocode-tui` (the same binary path
the PTY / Track 1 / Track 4 harnesses use):

```bash
cd /home/bs01763/projects/ai/lowrescoder/autocode/cmd/autocode-tui
GOROOT=/usr/lib/go-1.24 PATH=/usr/lib/go-1.24/bin:$PATH \
  go build -o /home/bs01763/projects/ai/lowrescoder/autocode/build/autocode-tui .
```

Override the resolved path with `AUTOCODE_TUI_BIN=<path>` when running
the suite — matches the PTY harness convention.

### Visual suite is slow

**Cause:** sequential scenario execution + fixed per-scenario
`drain_maxwait_s`.

**Fix:** short-term, tighten `drain_maxwait_s`. Long-term, parallelize
scenario capture (see future work).

---

## Caveats and known limits

- **Not hermetic w.r.t. wall clock.** Fixed sleeps in scenarios mean a
  slow host can miss a frame or a fast host can capture pre-render
  state. Tolerance absorbs small shifts; egregious hosts need timing
  tuning.
- **Palette is approximate.** `renderer.py::_NAMED_COLORS` is a
  reasonable dark-terminal default, not a faithful clone of any
  specific emulator. Cross-tool comparisons that matter should
  re-capture both tools through the same renderer.
- **Alt-screen restoration on exit.** Every scenario runs with
  `graceful_exit=False` for this reason. If you write a scenario that
  must capture a post-exit state, you'll need a different capture
  strategy.
- **Kitty keyboard-protocol CSI-u sequences** — stripped before pyte,
  so the renderer doesn't see them. If the TUI's rendering ever depends
  on them being parsed (unlikely), the strip will mask the bug.
- **Spinner / cursor blink** — small-area diffs between runs. 1%
  tolerance is designed around this.

---

## Future work

- **Deterministic replay harness** — instead of wall-clock sleeps, drive
  the PTY read loop to drain until a stable-screen invariant holds
  (e.g., no new bytes for 200ms or a known terminator byte arrives).
- **More scenarios:** approval prompts, queue-indicator variations,
  narrow-terminal layouts (50 cols), streaming during tool call,
  resize-mid-render.
- **Spinner/clock masking** — annotate scenarios with cell regions
  known to be non-deterministic so the differ ignores them explicitly
  rather than via whole-image tolerance.
- **Wire into `docs/tests/tui-testing-strategy.md`** validation matrix
  so visual-suite green is required before closing any TUI-visual
  change.
- **Cross-tool comparison harness** — a small helper that spawns
  another coding-TUI binary (`claude`, `opencode`, `codex`, `pi`)
  through the same capture pipeline, stores foreign-reference PNGs,
  and produces a side-by-side diff page.
- **Parallel scenario capture** — each Scenario is independent; run
  them concurrently.
- **Dynamic color-palette calibration** — detect the real terminal's
  palette via OSC 4 query before capture and match it in the renderer.
- **CI integration** — the snippets in "CI integration" above are not
  installed yet.
