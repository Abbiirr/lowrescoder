"""Live PTY parity tests for the current live-gated reference scenes.

Reuses the existing ``autocode/tests/tui-comparison/`` substrate (capture
driver, DSR responder, autocode launcher, pyte render helper) so there is
no duplicated process-launch code.

The reference contract encodes the design target described by
``tui-references/AutoCode TUI _standalone_.html``. The shipped direct
scenes covered here act as hard regression gates. The still-partial
`/plan` surface remains an honest strict xfail until a real plan panel
exists.

Environment:

- Requires the Rust TUI binary at
  ``autocode/rtui/target/release/autocode-tui`` or ``$AUTOCODE_TUI_BIN`` set.
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
_BIN_PATH = _REPO_ROOT / "autocode" / "rtui" / "target" / "release" / "autocode-tui"
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
    suppress_startup_warning: bool = False,
):
    launch = launcher_mod.spec(
        use_mock_backend=True,
        boot_budget_s=boot_budget_s,
        suppress_startup_warning=suppress_startup_warning,
    )
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


def _assert_plan_surface_materialized(text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    checklist_rows = [
        line for line in lines if line.startswith(("√ ", "● ", "○ "))
    ]
    has_step_language = any(
        "step" in line.lower() or "queued" in line.lower() for line in lines
    )
    has_plan_detail = any(
        "checkpoint" in line.lower() or "editable" in line.lower() for line in lines
    )
    assert len(checklist_rows) >= 2, "expected visible plan checklist rows"
    assert has_step_language, "expected visible step/queue language"
    assert has_plan_detail, "expected checkpoint/editability detail"


# ---------------------------------------------------------------- scene tests


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
        suppress_startup_warning=True,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


def test_scene_active(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["active"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[
            "refactor parser.ts to safely handle missing imports and run tests\r",
            0.4,
            1.0,
        ],
        boot_budget_s=4.0,
        drain_quiet_s=0.6,
        drain_maxwait_s=3.0,
        suppress_startup_warning=True,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


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


def test_scene_recovery(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["recovery"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=["__HALT_FAILURE__\r", 0.4, 1.0],
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


def test_scene_sessions(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["sessions"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[0.8, "/sessions\r", 2.0],
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=4.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


def test_scene_palette(predicates_mod, capture_mod, render_mod, launcher_mod, scenes):
    scene = scenes["palette"]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=[0.8, "\x0b", 0.6],
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=4.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)


@pytest.mark.parametrize(
    ("scene_id", "steps"),
    [
        ("multi", [0.8, "/multi\r", 1.0]),
        ("plan", [0.8, "/plan\r", 1.2]),
        ("review", [0.8, "/review\r", 1.0]),
        ("cc", [0.8, "/cc\r", 1.0]),
        ("restore", [0.8, "/restore\r", 1.0]),
        ("diff", [0.8, "/diff\r", 1.0]),
        ("grep", [0.8, "/grep\r", 1.0]),
        ("escalation", [0.8, "/escalation\r", 1.0]),
    ],
)
def test_scene_stage2_and_stage3_surfaces(
    predicates_mod,
    capture_mod,
    render_mod,
    launcher_mod,
    scenes,
    scene_id,
    steps,
):
    scene = scenes[scene_id]
    cols, rows = 160, 50
    _, text = _capture_and_render(
        capture_mod=capture_mod,
        render_mod=render_mod,
        launcher_mod=launcher_mod,
        cols=cols,
        rows=rows,
        steps=steps,
        boot_budget_s=4.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=4.0,
    )
    _assert_scene_passes(predicates_mod, text, scene, cols=cols)
