# AutoCode TUI Reference-Driven Testing

Deterministic **design-target ratchet** that checks the live Rust TUI against
the canonical design bundle at
`tui-references/AutoCode TUI _standalone_.html`.

Not to be confused with:

- `autocode/tests/vhs/` — self-vs-self PNG regression for the TUI's own
  output (pixel-diff against committed baselines, our own pipeline).
- `autocode/tests/tui-comparison/` — Phase 1/2 PTY substrate that proves
  **runtime invariants** (no crash, composer visible, picker filter
  works, etc.) against the real Rust TUI binary.

This tree adds a third dimension: "does the live TUI match the **design
target** the product owner handed us in the mockup bundle?"

---

## Contents

- [Purpose](#purpose)
- [What this pipeline can and cannot do](#what-this-pipeline-can-and-cannot-do)
- [Files and responsibilities](#files-and-responsibilities)
- [Data flow](#data-flow)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Scene inventory](#scene-inventory)
- [The ratchet](#the-ratchet)
- [Changing a scene](#changing-a-scene)
- [Caveats](#caveats)
- [Fidelity roadmap](#fidelity-roadmap)

---

## Purpose

The mockup bundle under `tui-references/` is the product owner's specification
of how the TUI should look in 14 named scenarios (`01 Ready`, `02 Active`,
`07 Recovery`, `14 Narrow`, etc.). This harness:

1. Extracts each scene's DOM structure, text anchors, and class distribution
   from the bundle's embedded `<template id="t-<scene>">` elements.
2. Encodes a **structural contract** per scene: required layout regions
   (HUD, composer, keybind footer, scene-specific elements).
3. Drives the real Rust TUI into each scene's plausible state via the
   existing `tests/tui-comparison/` PTY substrate and asserts the
   contract against the captured pyte Screen.

As matching UI features ship in the TUI, the contract flips from "failing
on purpose" to "enforcing a hard regression gate" — one scene at a time,
automatically.

---

## What this pipeline can and cannot do

### Can

- Extract deterministic scene structure from the HTML bundle (no OCR, no
  PyYAML, no `lxml` — stdlib only).
- Run a live PTY capture of the real Rust TUI against all 14 scenes and
  assert the scene's structural predicates.
- Ratchet scene drivers, predicates, and preset wiring together so new
  surfaces become hard regression gates in the same slice they ship.

### Cannot

- **Pixel-diff against the mockup JPG exports.** The JPG exports use a
  font (`JetBrains Mono`), theme (Tokyo Night), and renderer we do not
  currently match in any pyte pipeline. Pixel-level fidelity would
  require future higher-fidelity rendering or comparison tooling.
- **Prove final pixel parity on their own.** The PTY predicates prove
  triggerability and scene structure, not final visual fidelity.

---

## Files and responsibilities

```
autocode/tests/tui-references/
├── __init__.py              # package marker + docstring
├── extract_scenes.py        # HTML bundler decoder + scene walker + YAML emitter
├── manifest.yaml            # auto-generated; 14 scenes (14 populated)
├── predicates.py            # reference-contract predicates + stdlib YAML reader
├── test_reference_scenes.py # 14-scene live PTY regression gate
└── README.md                # this file

autocode/tests/unit/
├── test_tui_reference_extractor.py   # 12 unit tests locking the scene-extraction contract
└── test_tui_reference_predicates.py  # 38 unit tests covering every predicate + the YAML reader

autocode/docs/qa/test-results/
└── 20260418-*-slice1-*.md            # stored artifacts per milestone (extractor, finalization, remediation)
```

---

## Data flow

```
                                 extract_scenes.py
                                 ─────────────────
 tui-references/                 html.parser on bundler
 AutoCode TUI _standalone_.html  + json + zlib + base64
                                        │
                                        ▼
                                 manifest.yaml  (14 scenes, 14 populated)
                                        │
                                        ▼
                          predicates.load_scene_records()
                                        │
                                        ▼
                          scene contract (region classes +
                          anchors + class_counts)

                                 test_reference_scenes.py
                                 ────────────────────────
 autocode-tui (Rust binary) ──▶ PTY capture (tests/tui-comparison substrate)
                                        │
                                        ▼
                                 pyte.Screen + rendered text
                                        │
                                        ▼
                          predicates.run_scene_predicates(text, scene, cols)
                                        │
                                        ▼
                          ReferenceReport → assert all predicates pass
                                        │
                                        ▼
                          scene-specific pytest gate
```

---

## Dependencies

- **stdlib only.** `html.parser`, `json`, `zlib`, `base64`, `re`, `enum`,
  `pathlib`, `dataclasses`, `typing`, `importlib.util`.
- **pyte + Pillow** — reused from `tests/tui-comparison/`; not added by
  this slice.
- **pytest** — test runner.
- **Rust TUI binary** at `autocode/rtui/target/release/autocode-tui` or `$AUTOCODE_TUI_BIN`.
  Tests skip cleanly if the binary is missing.
- **Mock backend** at `autocode/tests/pty/mock_backend.py` — already in
  tree; no edits needed for Slice 1.

Optional future fidelity tooling may add `scikit-image` and `imagehash` for
region-level metrics, but the current hard gate does not depend on them.

---

## Usage

### Regenerate the manifest

```bash
uv run python autocode/tests/tui-references/extract_scenes.py
```

Produces `autocode/tests/tui-references/manifest.yaml`. Run whenever
`tui-references/AutoCode TUI _standalone_.html` changes; commit the new
manifest alongside the bundle.

### Run the unit tests (fast, no PTY)

```bash
uv run pytest autocode/tests/unit/test_tui_reference_extractor.py \
              autocode/tests/unit/test_tui_reference_predicates.py -v
```

50 tests, ~0.12 s.

### Run the live PTY ratchet (requires the Rust TUI binary)

```bash
make tui-references
```

Or directly:

```bash
uv run pytest autocode/tests/tui-references/ -v
```

Expected outcome today: **14 passed**.

### Build the screenshot-first comparison bundle

For visual review work where you want actual side-by-side evidence against
the exported mockup JPGs, use:

```bash
make tui-reference-gap
```

This generates:

- fresh live PNG captures under `autocode/docs/qa/tui-reference-comparison/<stamp>/live/`
- side-by-side sheets under `.../compare/`
- a markdown artifact under
  `autocode/docs/qa/test-results/<stamp>-tui-reference-gap.md`

This is a **manual evidence generator**, not a regression gate.

### Capture the current AutoCode analog for all 14 scenes

If you want a stored sweep of what the current product can actually show for
every reference scene, run:

```bash
make tui-scene-matrix
```

This generates:

- per-scene frame directories under `autocode/docs/qa/tui-frame-sequences/<stamp>/`
- an overview grid for the whole sweep
- a markdown matrix artifact under
  `autocode/docs/qa/test-results/<stamp>-tui-14-scene-capture-matrix.md`

Important: this is a **current-state capture sweep**. As of the current tree,
all 14 scenes have direct capture paths; the remaining gap is visual fidelity
against the mockup JPGs.

### Capture mid-run frames for benchmark or system-feature flows

Some important surfaces are not idle-state frontend chrome:

- planning / todo list
- restore / checkpoints
- subagent / task activity
- review / diff / escalation flows

For those, a final-state snapshot is often the wrong evidence. Use the
frame-sequence helper to grab multiple screenshots while the session is in
flight:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --list-presets
uv run python tests/tui-references/capture_frame_sequence.py \
  --name sessions-demo \
  --preset sessions
```

The helper writes a sequence of `PNG + TXT` frames under:

`autocode/docs/qa/tui-frame-sequences/<stamp>/<name>/`

The canonical trigger map for those presets lives in:

- `docs/tui-testing/tui-reference-scene-trigger-guide.md`
- `docs/tui-testing/tui-system-feature-coverage-guide.md`

---

## Scene inventory

All 14 scenes from the bundle live in `manifest.yaml` and are now populated.

| # | scene_id | Label | PTY gate | Current gap |
|---|---|---|---|---|
| 01 | ready | 01 Ready | ✓ | visual fidelity |
| 02 | active | 02 Active | ✓ | visual fidelity |
| 03 | multi | 03 Multitasking | ✓ | visual fidelity |
| 04 | plan | 04 Plan | ✓ | visual fidelity |
| 05 | review | 05 Review | ✓ | visual fidelity |
| 06 | cc | 06 Command center | ✓ | visual fidelity |
| 07 | recovery | 07 Recovery | ✓ | visual fidelity |
| 08 | restore | 08 Restore | ✓ | visual fidelity |
| 09 | sessions | 09 Sessions | ✓ | visual fidelity |
| 10 | palette | 10 Palette | ✓ | visual fidelity |
| 11 | diff | 11 Diff focus | ✓ | visual fidelity |
| 12 | grep | 12 Search | ✓ | visual fidelity |
| 13 | escalation | 13 Escalation | ✓ | visual fidelity |
| 14 | narrow | 14 Narrow | ✓ | visual fidelity |

---

## The ratchet

The old xfail ratchet is now fully consumed: every current reference scene is a
hard regression gate. Future scene work should keep the same discipline:
surface, trigger, predicate, and gate promotion should land together.

---

## Changing a scene

When you change a shipped reference scene or add a new one:

1. Update `scene_presets.py` if the deterministic trigger changes.
2. Update `build_visual_gap_report.py` if the screenshot bundle should expose the new capture directly.
3. Update `predicates.py` for any new scene-specific token checks.
4. Update `test_reference_scenes.py` so the live PTY gate exercises the shipped trigger.
5. Regenerate `manifest.yaml` if the bundle or populated-scene set changes.
6. Run `make tui-references`, `make tui-scene-matrix`, and `make tui-reference-gap`.

---

## Caveats

- **Hyphenated directory name.** `autocode/tests/tui-references/` has
  a hyphen, matching the sibling `autocode/tests/tui-comparison/`
  convention. Python's normal import machinery cannot reach it; the
  test module loads siblings via `importlib.util.spec_from_file_location`
  and adds `tests/tui-comparison/` to `sys.path` so `capture.py`'s
  `from dsr_responder import ...` fallback resolves. This produces a
  `ruff N999` warning on the `__init__.py` that matches the sibling's
  pre-existing baseline.
- **Hand-rolled YAML.** The emitter writes a narrow shape (flat
  scalars + string lists + scalar-valued maps) and the reader
  understands only that shape via lookahead-based nested parsing.
  Arbitrary YAML will NOT work. This is intentional — avoids a PyYAML
  dep for a single auto-generated file. The comment header in
  `manifest.yaml` explicitly forbids hand edits.
- **`_CAPTURE_SANITY_ROW_FLOOR = 5`** is a capture-sanity check, not a
  full-frame-presence signal. The strong layout signal lives in
  `hud_present` / `composer_present` / `keybind_footer_present`.
  Named constant is the single source of truth so the comment and the
  implementation cannot drift.
- **Demo content is not tested.** The mockup's anchor text includes
  demo-specific values (user handle `abir@ws-02`, branch
  `feat/parser-fix`, etc.) a real session will never produce. Predicates
  check structure — region classes, layout zones, scene-specific
  semantics — not content fidelity. Content coverage is the artifact
  layer's job in Slice 2.

---

## Fidelity roadmap

Stage 2 / 3 implementation is complete: all 14 reference scenes are now live
PTY gates and all 14 have direct capture paths in the scene matrix.

Current focus:

- tighten typography, spacing, density, and information hierarchy against the
  screenshot bundle from
  `autocode/docs/qa/test-results/20260422-092151-tui-reference-gap.md`
- use `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
  as the first authoritative renderer-pass verification note for the rebuilt
  release binary
- use `autocode/docs/qa/test-results/20260422-112207-tui-stage4-search-escalation-cc-split-pass.md`
  as the current structural-fidelity slice covering the untitled shell,
  review/diff/grep/escalation/cc split-detail surfaces, and the restored Track 1 spinner gates
- use `autocode/docs/qa/test-results/20260422-113800-tui-stage4-recovery-density-pass.md`
  as the current recovery-fidelity slice covering the structured halted/error
  surface with context and action detail
- use `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
  as the fullscreen-compliance slice that replaces the centered shell and
  codifies the user-locked render contract
- use `autocode/docs/qa/test-results/20260422-081639-tui-stage4-ready-active-density-pass.md`
  as the ready/active fidelity slice that lands the quiet idle surface, the
  structured active surface, and the mid-run active screenshot fix in the gap
  report
- use `autocode/docs/qa/test-results/20260422-152822-tui-stage4-overlay-narrow-pass.md`
  as the overlay / narrow fidelity slice that compacts the fullscreen
  `sessions` / `palette` cards and keeps the narrow ready HUD/footer readable
- refine the remaining scene-specific emphasis, density, hierarchy, and
  real-data-binding gaps so the live TUI moves from "structurally correct" to
  "visually close"
- keep `make tui-references`, `make tui-scene-matrix`, and
  `make tui-reference-gap` green while these fidelity adjustments land

Optional future work:

- add higher-fidelity rendering or image metrics if the current pyte/Pillow
  evidence bundle becomes too weak for late-stage polish
- add an opt-in headless Chromium path if pixel-level validation becomes worth
  the extra dependency cost

---

## Review chain

See `AGENTS_CONVERSATION.MD` Entries 1182 → 1200 for the full research →
strategy-lock → Slice 1 delivery → remediation → APPROVE chain. Key
references:

- Entry 1184: Codex APPROVE of the HTML-first, deterministic-first,
  fidelity-later direction.
- Entry 1187–1188: strategy lock-in (stdlib parser, no visual-metric
  deps in Slice 1).
- Entry 1193 → 1197: Codex NEEDS_WORK → Claude remediation → Codex
  APPROVE.
- Entry 1200: Codex reviewer-side closeout.
