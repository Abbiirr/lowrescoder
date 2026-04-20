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
- [The ratchet — how `strict=True` xfail works](#the-ratchet--how-stricttrue-xfail-works)
- [Flipping a scene off xfail (DoD for a UI feature slice)](#flipping-a-scene-off-xfail-dod-for-a-ui-feature-slice)
- [Adding a new MVP scene](#adding-a-new-mvp-scene)
- [Caveats](#caveats)
- [Slice 2+ roadmap](#slice-2-roadmap)

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
- Run a live PTY capture of the real Rust TUI against each of the 4 MVP
  scenes and assert the scene's structural predicates.
- Signal via pytest **XPASS** the instant a UI feature lands that closes
  one of the design-to-implementation gaps. `strict=True` xfail turns
  that XPASS into a suite failure, forcing the developer to flip the
  decorator and promote the scene to a hard regression gate.

### Cannot

- **Pixel-diff against the mockup JPG exports.** The JPG exports use a
  font (`JetBrains Mono`), theme (Tokyo Night), and renderer we do not
  currently match in any pyte pipeline. Pixel-level fidelity is Slice 2
  + Slice 3 work (themed parallel renderer and optional headless
  Chromium rendering).
- **Drive every scene into state.** Today only 4 of 14 scenes are MVP
  populated, and one of those (`recovery`) requires a mock-backend
  `__HALT_FAILURE__` trigger that does not yet exist. That trigger is a
  Slice 2 deliverable.
- **Prove parity when all xfails are still XFAIL.** Strict-XFAIL tests
  encode the contract but do not themselves prove live parity. Parity is
  claimed one scene at a time, as each xfail decorator is removed by the
  developer who shipped the matching UI feature.

---

## Files and responsibilities

```
autocode/tests/tui-references/
├── __init__.py              # package marker + docstring
├── extract_scenes.py        # HTML bundler decoder + scene walker + YAML emitter
├── manifest.yaml            # auto-generated; 14 scenes (4 populated)
├── predicates.py            # reference-contract predicates + stdlib YAML reader
├── test_reference_scenes.py # 4-scene live PTY ratchet (strict=True xfail)
└── README.md                # this file

autocode/tests/unit/
├── test_tui_reference_extractor.py   # 12 unit tests locking the scene-extraction contract
└── test_tui_reference_predicates.py  # 31 unit tests covering every predicate + the YAML reader

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
                                 manifest.yaml  (14 scenes, 4 populated)
                                        │
                                        ▼
                          predicates.load_scene_records()
                                        │
                                        ▼
                          scene contract (region classes +
                          anchors + class_counts)

                                 test_reference_scenes.py
                                 ────────────────────────
 autocode-tui (Go binary) ──▶ PTY capture (tests/tui-comparison substrate)
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
                          @pytest.mark.xfail(strict=True) gate
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
- **Rust TUI binary**: set `$AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui` to retarget the harness at the Rust implementation. All 4 `strict=True` xfails will be re-evaluated at M11 cutover per the Rust migration plan.
- **Mock backend** at `autocode/tests/pty/mock_backend.py` — already in
  tree; no edits needed for Slice 1.

Slice 2 will add `scikit-image` and `imagehash` as dev-deps for the
non-blocking region-SSIM metric. Not required for Slice 1.

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

43 tests, ~0.12 s.

### Run the live PTY ratchet (requires the Rust TUI binary)

```bash
make tui-references
```

Or directly:

```bash
uv run pytest autocode/tests/tui-references/ -v
```

Expected outcome today: **4 XFAILED**. Each one's reason names the
concrete design-to-implementation gap that is blocking promotion.

---

## Scene inventory

All 14 scenes from the bundle live in `manifest.yaml`. MVP coverage is
4; the other 10 are stubbed with captured anchor data so they can be
promoted without re-extracting.

| # | scene_id | Label | MVP | Gap blocking promotion |
|---|---|---|---|---|
| 01 | ready | 01 Ready | ✓ | HUD chip row + composer box + keybind footer |
| 02 | active | 02 Active | ✓ | Tool-chain panel + inline diff hunks + test-output panel |
| 03 | multi | 03 Multitasking | — | stubbed |
| 04 | plan | 04 Plan | — | stubbed |
| 04 | review | 04 Review | — | stubbed |
| 05 | cc | 05 Command center | — | stubbed |
| 07 | recovery | 07 Recovery | ✓ | 6 safe-option recovery cards + `__HALT_FAILURE__` mock-backend trigger |
| 08 | restore | 08 Restore | — | stubbed |
| 09 | sessions | 09 Sessions | — | stubbed |
| 10 | palette | 10 Palette | — | stubbed |
| 11 | diff | 11 Diff focus | — | stubbed |
| 12 | grep | 12 Search | — | stubbed |
| 13 | escalation | 13 Escalation | — | stubbed |
| 14 | narrow | 14 Narrow | ✓ | Narrow-layout branch (rail → tabs, drawer bounded to 3 rows) |

---

## The ratchet — how `strict=True` xfail works

Every MVP test is `@pytest.mark.xfail(strict=True, reason="...")`.

- The predicates today **fail** because the UI does not yet match the
  mockup → pytest reports **XFAIL** → the suite stays green. No CI drama.
- When a developer ships the matching UI feature and the predicates
  start passing → pytest reports **XPASS** → `strict=True` turns that
  XPASS into a **suite failure** → the developer must flip the
  decorator off.
- Once the decorator is flipped, the test becomes a **hard regression
  gate** for that scene. Any future change that regresses the layout
  fails CI.

This is the ratchet: the slice ships green and converts gap-by-gap into
enforcement.

---

## Flipping a scene off xfail (DoD for a UI feature slice)

When you implement the UI feature that closes a scene's gap (e.g., the
HUD chip row for `test_scene_ready`):

1. **Run the live test locally**:
   ```bash
   uv run pytest autocode/tests/tui-references/test_reference_scenes.py::test_scene_ready -v
   ```
2. **Expect `XPASS` with `strict=True` → suite failure.** This is the
   signal that the feature closed the gap.
3. **Remove the `@pytest.mark.xfail(...)` decorator** from the test.
4. **Re-run.** The test now gates against regressions — any future
   change that breaks the HUD / composer / keybinds on the Ready scene
   will fail this test.
5. **Commit** the decorator removal alongside the UI feature change.
6. **Update this README's Scene inventory table** — move the scene out
   of the "Gap blocking promotion" column.

Never leave an xfail'd test that is visibly passing on your machine.

---

## Adding a new MVP scene

To promote one of the 10 stubbed scenes (e.g., `palette`) to MVP:

1. Edit `extract_scenes.py` — add `"palette"` to `_MVP_SCENES`.
2. Regenerate: `uv run python autocode/tests/tui-references/extract_scenes.py`.
3. Write a scene-specific predicate in `predicates.py` (e.g., a
   `_pred_scene_palette_entries` check for the palette command list).
4. Wire the scene-specific predicate into `run_scene_predicates()`'s
   scene-id dispatch.
5. Add a test function in `test_reference_scenes.py`. Drive the TUI
   into the scene's state (slash command, keystrokes, mock-backend
   trigger) via the existing PTY substrate.
6. Decorate with `@pytest.mark.xfail(strict=True, reason=...)` naming
   the current gap. Flip it off only when the gap is closed (see
   previous section).
7. Add unit coverage to `test_tui_reference_predicates.py` for any new
   predicate helper.

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

## Slice 2+ roadmap

**Slice 2 (next):**

- Themed parallel renderer: Tokyo Night palette + vendored JetBrains
  Mono font, producing PNG frames that can be visually compared to the
  mockup JPGs without touching `tests/vhs/` self-vs-self baselines.
- Side-by-side HTML artifact report per scene (cropped mockup | live
  render | per-region SSIM scores | failed predicate surface).
- Mock-backend `__HALT_FAILURE__` trigger so `test_scene_recovery` can
  capture a real halted state instead of the default idle frame.
- Dev-deps: `scikit-image`, `imagehash` (both pure-Python on numpy).

**Slice 3 (optional, later):**

- Headless Chromium + xterm.js live-side rendering — accepts stdin ANSI,
  renders with the same JetBrains Mono webfont + Tokyo Night CSS the
  mockup bundle ships, emits PNG. Enables defensible pixel-level diff.
- Opt-in Make target (`make tui-references-highfi`), not on every PR.

**Future:**

- Flip the 4 MVP `strict=True` xfails off as each matching UI feature
  ships (HUD chip row, composer box, tool cards, narrow-layout branch,
  recovery action cards).
- Promote stubbed scenes as new UI features come online.

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
