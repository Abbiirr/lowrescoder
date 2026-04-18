"""Live PTY parity tests for the 4 MVP reference scenes — **design-target
ratchet**, not a regression gate.

Reuses the existing ``autocode/tests/tui-comparison/`` substrate (capture
driver, DSR responder, autocode launcher, pyte render helper) so there is
no duplicated process-launch code.

**Why every scene is xfail'd (and why `strict=True`):**

The reference contract encodes the design target described by
``tui-references/AutoCode TUI _standalone_.html`` — that target is not
yet shipped in the Go TUI (no HUD chip row, no composer box, no tool
cards, no narrow-layout branch, no recovery action cards). Each scene's
xfail reason names the concrete gap. Using ``strict=True`` means:

- while the gap remains, ``XFAIL`` is the expected outcome — CI stays
  green.
- as soon as the matching feature ships and the predicates start passing,
  pytest reports ``XPASS`` as a **failure**, forcing whoever landed the
  feature to flip the decorator off and turn the test into a real
  regression check — the ratchet.

This file is not a "gate". It becomes a gate one scene at a time, only
after the matching UI work lands and the xfail decorator is removed.

Environment:

- Requires the Go TUI binary at ``autocode/build/autocode-tui`` or
  ``$AUTOCODE_TUI_BIN`` set.
- Mock backend at ``autocode/tests/pty/mock_backend.py`` handles JSON-RPC.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
# _HERE = <repo>/autocode/tests/tui-references → parents[0]=tests,
# parents[1]=autocode, parents[2]=<repo>
_REPO_ROOT = _HERE.parents[2]
_BIN_PATH = _REPO_ROOT / "autocode" / "build" / "autocode-tui"
_MANIFEST_PATH = _HERE / "manifest.yaml"
_TUI_COMPARISON_DIR = _HERE.parent / "tui-comparison"

# The sibling tui-comparison tree lives under a hyphenated directory which
# Python's normal import machinery cannot reach. capture.py does a bare
# ``from dsr_responder import ...`` fallback, so drop that directory on
# sys.path before importlib pulls the file-by-path.
if str(_TUI_COMPARISON_DIR) not in sys.path:
    sys.path.insert(0, str(_TUI_COMPARISON_DIR))


def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f"spec failed for {path}"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def predicates_mod():
    return _load_module(
        "autocode_tui_references_predicates",
        _HERE / "predicates.py",
    )


@pytest.fixture(scope="module")
def capture_mod():
    return _load_module(
        "autocode_tui_comparison_capture",
        _TUI_COMPARISON_DIR / "capture.py",
    )


@pytest.fixture(scope="module")
def render_mod():
    return _load_module(
        "autocode_tui_comparison_predicates",
        _TUI_COMPARISON_DIR / "predicates.py",
    )


@pytest.fixture(scope="module")
def launcher_mod():
    return _load_module(
        "autocode_tui_comparison_launchers_autocode",
        _TUI_COMPARISON_DIR / "launchers" / "autocode.py",
    )


@pytest.fixture(scope="module")
def scenes(predicates_mod):
    if not _MANIFEST_PATH.is_file():
        pytest.skip(f"manifest not generated; run extract_scenes.py first ({_MANIFEST_PATH})")
    records = predicates_mod.load_scene_records(_MANIFEST_PATH)
    return {record["scene_id"]: record for record in records}


@pytest.fixture(scope="module", autouse=True)
def _skip_if_no_binary():
    if not _BIN_PATH.is_file():
        pytest.skip(
            f"autocode TUI binary not found at {_BIN_PATH}; "
            f"run `go build -o {_BIN_PATH} ./autocode/cmd/autocode-tui`"
        )


# ------------------------------------------------------------- capture helper

def _capture_and_render(
    *,
    capture_mod,
    render_mod,
    launcher_mod,
    cols: int,
    rows: int,
    steps: list[float | str],
    boot_budget_s: float = 6.0,
    drain_quiet_s: float = 1.2,
    drain_maxwait_s: float = 6.0,
):
    launch = launcher_mod.spec(use_mock_backend=True, boot_budget_s=boot_budget_s)
    opts = capture_mod.CaptureOptions(
        argv=launch.argv,
        cols=cols,
        rows=rows,
        boot_budget_s=launch.boot_budget_s,
        drain_quiet_s=drain_quiet_s,
        drain_maxwait_s=drain_maxwait_s,
        env_extra=launch.env_extra,
        steps=steps,
    )
    result = capture_mod.capture(opts)
    _, text = render_mod.render_screen(result.raw, rows=rows, cols=cols)
    return result, text


def _assert_scene_passes(
    predicates_mod,
    text: str,
    scene: dict[str, Any],
    *,
    cols: int,
) -> Any:
    report = predicates_mod.run_scene_predicates(text, scene, cols=cols)
    failures = report.failures()
    if failures:
        pretty = "\n".join(
            f"  - {c.name}: {c.detail}" for c in failures
        )
        raise AssertionError(
            f"Scene {scene['scene_id']} ({scene.get('label', '')}) "
            f"failed {len(failures)} predicate(s):\n{pretty}"
        )
    return report


# ---------------------------------------------------------------- scene tests
# Every MVP scene is xfail'd with ``strict=True`` — see the module docstring
# for the ratchet semantics. Flip the decorator off per-scene as the matching
# UI feature lands.


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Mockup page 01 shows a HUD chip-row (model·think·branch·tokens·$·timer·"
        "Δ·tasks·agents·q·sandbox) + composer-box + keybind footer. Live Go TUI "
        "on idle currently shows only a welcome banner. Flip to non-xfail once "
        "the Ready-state HUD + composer chrome ships."
    ),
)
def test_scene_ready(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["ready"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[0.6],  # let on_status render; no input.
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Mockup page 02 shows HUD + tool-chain panel (Read/Search/Edit/Run) + "
        "inline diff hunks + live test-output panel + composer. Live Go TUI "
        "renders a plain token stream when a turn is in flight. Flip once "
        "the Active-turn chrome (tool cards + diff hunks) ships."
    ),
)
def test_scene_active(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["active"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        # Send a message; mock backend streams "Hello from the mock backend!"
        # and the spinner-with-working-status renders while it is in-flight.
        steps=["hello\r", 0.4, 1.0],
        boot_budget_s=4.0,
        drain_quiet_s=0.6,
        drain_maxwait_s=3.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Mockup page 14 shows a narrow-geometry adaptation: rail → tabs, drawer "
        "bounded to 3 rows, composer + transcript always visible. Live Go TUI "
        "has no narrow-layout branch yet. Flip once narrow-layout mode ships."
    ),
)
def test_scene_narrow(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["narrow"]
    # Narrow TUI geometry; well below the 80-col convention, matching page 14.
    cols, rows = 68, 30
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[0.6],
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Recovery action cards (Mockup page 07) — 6 safe-option buttons "
        "(retry · inspect · restore · rewind · compact · planning) — are not "
        "implemented in the Go TUI. No mock-backend trigger drives the TUI "
        "into a halted state yet either. Flip after the recovery-cards UI "
        "and a __HALT_FAILURE__ mock-backend trigger both land."
    ),
)
def test_scene_recovery(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["recovery"]
    cols, rows = 160, 50
    # No backend trigger yet drives the TUI into a halted/recovery state; the
    # mock backend happily streams a reply for any message. Slice 2 (or the
    # recovery-cards implementation slice) should add `__HALT_FAILURE__`
    # handling so this test can drive the real state.
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[0.6],
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)
