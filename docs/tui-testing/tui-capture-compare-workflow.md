# TUI Capture And Compare Workflow

Step-by-step guide for rerunning the screenshot-first parity workflow.

This is the repeatable path for:

- checking current TUI status
- generating fresh live captures
- comparing them to `tui-references`
- storing evidence paths in a QA artifact

This is not a substitute for the four-track testing strategy. It sits on top of
that strategy and turns the current state into visible evidence.

## 1. Build The Binary

```bash
cd autocode/rtui
cargo build --release
```

Optional override if you want a different binary:

```bash
export AUTOCODE_TUI_BIN=/abs/path/to/autocode-tui
```

## 2. Run The Baseline Matrix

Run these before generating screenshots so you know whether you are looking at a
healthy or already-broken build.

```bash
make tui-regression
make tui-references
cd autocode
uv run python tests/pty/pty_smoke_rust_comprehensive.py
```

Interpretation:

- `make tui-regression` answers: runtime invariants still hold
- `make tui-references` answers: current hard-gated reference scenes still pass
- `pty_smoke_rust_comprehensive.py` answers: real binary + backend path still works

## 3. Generate The Screenshot Bundle

```bash
make tui-reference-gap
```

This produces:

- `autocode/docs/qa/tui-reference-comparison/<stamp>/live/`
- `autocode/docs/qa/tui-reference-comparison/<stamp>/compare/`
- `autocode/docs/qa/test-results/<stamp>-tui-reference-gap.md`

What this bundle is for:

- side-by-side visual review
- scene-by-scene gap logging
- evidence for review comments and follow-up planning

What it is not:

- a pixel-perfect regression gate
- proof that blocked scenes are now implemented

## 4. Capture Targeted Mid-Run States

Use this when the interesting UI only exists during a run, not at the end.

List the named reference-scene presets:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --list-presets
```

Run one preset:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --name active-demo --preset active
```

Run an ad hoc scripted sequence:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py \
  --name sessions-demo \
  --steps '[0.8, "/sessions\r", 2.0]'
```

Outputs land under:

- `autocode/docs/qa/tui-frame-sequences/<stamp>/<name>/`

Each run stores:

- a boot frame
- frames after each sleep/input step
- a final frame
- `PNG` and `TXT` versions of each frame

## 5. Compare Against The Right Reference

Use:

- `docs/tui-testing/tui-reference-scene-trigger-guide.md` for the 14-scene map
- `autocode/tests/tui-references/manifest.yaml` for the extracted reference contract
- `tui-references/autocode_tui_mockup_pages-to-jpg-*.jpg` for the visual target

When comparing, separate these failure types:

- `missing surface`: the product does not expose the scene yet
- `wrong state`: the scene exists but the trigger/capture path is wrong
- `visual drift`: the right surface is visible, but layout or chrome differs
- `harness issue`: the capture is wrong even though the live TUI behaved correctly

## 6. Record The Gap Analysis

Use a markdown artifact under:

- `autocode/docs/qa/test-results/<stamp>-<topic>.md`

Minimum structure:

1. scope and commands run
2. evidence paths
3. scene-by-scene findings
4. blocker classification
5. recommended implementation order

The existing examples are:

- `autocode/docs/qa/test-results/20260421-070327-tui-reference-gap.md`
- `autocode/docs/qa/test-results/20260421-130754-tui-reference-gap-analysis.md`

## 7. Use The Correct Follow-Up Path

If the gap is mostly runtime correctness:

- fix Track 1 / PTY problems first

If the gap is mostly visible scene structure:

- work in Track 4 and rerun `make tui-references`

If the gap is mostly terminal rendering drift:

- rerun VHS and decide whether a baseline update is intended

If the gap is a blocked feature scene:

- use `docs/tui-testing/tui-system-feature-coverage-guide.md`

## Frequent Commands

```bash
make tui-regression
make tui-references
make tui-reference-gap
cd autocode && uv run python tests/pty/pty_smoke_rust_comprehensive.py
cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --list-presets
cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --name demo --preset sessions
```
