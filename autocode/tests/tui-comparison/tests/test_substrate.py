"""Substrate tests for tui-comparison Track 1.

Covers both a **positive control** (real autocode startup → hard
invariants pass) and a **negative control** (injected bad/empty frame →
hard invariant fails truthfully). Codex Entry 1144 Suggested Change #3
explicitly requires the negative control.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).resolve().parent.parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from predicates import (  # noqa: E402
    PredicateClass,
    run_predicates,
)


# -------------------------------------------------------------------------
# NEGATIVE CONTROL — a bad/empty frame MUST produce a hard-invariant failure
# -------------------------------------------------------------------------

def test_negative_control_empty_capture_fails_hard_invariant():
    """An empty capture should fail `no_crash_during_capture`."""
    report = run_predicates(b"", rows=50, cols=160)
    hard_no_crash = next(r for r in report.hard if r.name == "no_crash_during_capture")
    assert not hard_no_crash.passed, (
        "negative control: empty raw bytes should FAIL the no-crash hard "
        "invariant; if this passes, the harness is not detecting a bad "
        "capture and would let a real regression through"
    )
    # Also: `all_hard_passed` must be False for this malformed input
    assert not report.all_hard_passed


def test_negative_control_queue_debug_leak_fails_hard_invariant():
    """Injected 'steering_queue' text should fail the queue-leak invariant."""
    # Build a synthetic raw blob with enough bytes to clear the no-crash
    # threshold, but containing a clear queue-debug leak marker.
    bad_raw = (b"\x1b[2J\x1b[H" + b"normal line\n" * 40 +
               b"<<STEER: queue drain\n" + b"AutoCode\n" + b"> \n")
    report = run_predicates(bad_raw, rows=50, cols=160)
    hard_no_leak = next(r for r in report.hard if r.name == "no_queue_debug_leak")
    assert not hard_no_leak.passed, (
        "negative control: injected <<STEER debug marker must fail the "
        "queue-leak hard invariant"
    )


# -------------------------------------------------------------------------
# POSITIVE CONTROL — a real autocode startup capture passes hard invariants
# -------------------------------------------------------------------------

def test_positive_control_autocode_startup_hard_invariants_pass():
    """Run real autocode startup; all hard invariants should pass."""
    # Skip if binary is absent — test is run-as-available
    try:
        from launchers import autocode as autocode_launcher
        binary = autocode_launcher.find_binary()
    except FileNotFoundError:
        pytest.skip("autocode TUI binary not built (run `cargo build --release` first)")

    # Lazy-import the capture module so headless test envs without
    # termios/pty still import this test file.
    from capture import CaptureOptions, capture

    # Point at the mock backend so the positive control is deterministic
    # and does not require a live gateway or API keys.
    from pathlib import Path
    mock_backend = Path(__file__).resolve().parents[2] / "pty" / "mock_backend.py"
    if not mock_backend.exists():
        pytest.skip(f"mock backend not found at {mock_backend}")

    opts = CaptureOptions(
        argv=[str(binary)],
        cols=160,
        rows=50,
        boot_budget_s=3.0,
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
        env_extra={
            "LITELLM_MASTER_KEY": os.environ.get("LITELLM_MASTER_KEY", ""),
            "AUTOCODE_PYTHON_CMD": str(mock_backend),
        },
        steps=[],
    )
    result = capture(opts)
    report = run_predicates(result.raw, rows=50, cols=160)

    # Some hard predicates may fail if the binary is stale or the backend
    # can't start. Report the details instead of a generic assert so a
    # regression report is informative.
    failures = [r for r in report.hard if not r.passed]
    if failures:
        detail_lines = [f"  - {r.name}: {r.detail}" for r in failures]
        pytest.fail(
            "positive control: autocode startup should pass all hard "
            f"invariants, but {len(failures)} failed:\n"
            + "\n".join(detail_lines)
            + f"\n\nCaptured raw bytes: {len(result.raw)}"
        )


# -------------------------------------------------------------------------
# Structural tests — predicate classification contract
# -------------------------------------------------------------------------

def test_hard_and_soft_predicates_are_classified_correctly():
    """Every predicate must be explicitly classified HARD or SOFT."""
    # Run against trivial input just to materialize the report structure
    report = run_predicates(b"\x1b[H" + b"x" * 200, rows=50, cols=160)
    for r in report.hard:
        assert r.classification == PredicateClass.HARD, (
            f"predicate {r.name} is in hard list but has class "
            f"{r.classification}"
        )
    for r in report.soft:
        assert r.classification == PredicateClass.SOFT, (
            f"predicate {r.name} is in soft list but has class "
            f"{r.classification}"
        )


def test_report_json_roundtrip():
    """The JSON shape is stable and includes both hard + soft summaries."""
    import json

    report = run_predicates(b"", rows=50, cols=160)
    parsed = json.loads(report.to_json())
    assert "hard" in parsed
    assert "soft" in parsed
    assert "summary" in parsed
    assert parsed["summary"]["all_hard_passed"] is False  # empty capture


# -------------------------------------------------------------------------
# Turn-predicate deterministic fixtures — per Codex Entry 1151 Suggested
# Change #3. Validate basic_turn / spinner / response predicates without
# requiring a live capture. Synthetic raw bytes exercise each predicate's
# pass AND fail path.
# -------------------------------------------------------------------------

def _find_hard(report, name: str):
    matches = [r for r in report.hard if r.name == name]
    assert len(matches) == 1, f"predicate {name!r} missing from hard set"
    return matches[0]


def test_turn_predicates_na_on_startup_scenario():
    """Turn-scoped predicates must return PASS with N/A detail on startup."""
    # Startup-shape capture: header + composer marker, no user prompt
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"\r\n"
        + b"\r\n" * 30
        + b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
        b"suggest master\r\n"
    )
    report = run_predicates(synthetic, scenario="startup", rows=50, cols=160)

    for pname in (
        "basic_turn_returns_to_usable_input",
        "spinner_observed_during_turn",
        "response_followed_user_prompt",
    ):
        r = _find_hard(report, pname)
        assert r.passed, f"{pname} should PASS with N/A on startup, got {r.detail!r}"
        assert "N/A" in r.detail, f"{pname} should mark detail N/A on startup"


def test_turn_predicates_pass_on_complete_turn_fixture():
    """All three turn predicates pass when fixture has user prompt + spinner + response."""
    # Synthetic first-prompt-text capture with:
    #   - header
    #   - user prompt echo "hello"
    #   - braille spinner
    #   - substantive response line
    #   - composer visible after turn
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"\r\n"
        b"> hello\r\n"                                              # user prompt echoed
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6 (1s)\r\n"                # ⠙ Thinking... (1s)
        b"The answer to your question is that autocode is an AI coding assistant.\r\n"  # response
        b"\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"                # composer regained
        b"tools openrouter suggest mock-session-001\r\n"
    )
    report = run_predicates(synthetic, scenario="first-prompt-text", rows=50, cols=160)

    basic = _find_hard(report, "basic_turn_returns_to_usable_input")
    assert basic.passed, f"basic_turn should PASS on good fixture; detail={basic.detail}"

    spin = _find_hard(report, "spinner_observed_during_turn")
    assert spin.passed, f"spinner should PASS (⠙ + 'Thinking' present); detail={spin.detail}"

    resp = _find_hard(report, "response_followed_user_prompt")
    assert resp.passed, f"response should PASS (substantive line after prompt); detail={resp.detail}"


def test_basic_turn_fails_when_composer_missing_after_turn():
    """basic_turn must FAIL if the composer never returned after the prompt."""
    # Fixture: prompt was sent, spinner + response content appear, but the
    # composer row is never re-rendered (simulates a TUI stuck post-response)
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"> hello\r\n"
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6\r\n"
        b"Response content line one has substantial text here to pass response pred\r\n"
        # No composer marker visible in final frame — simulates a hang
    )
    report = run_predicates(synthetic, scenario="first-prompt-text", rows=50, cols=160)

    basic = _find_hard(report, "basic_turn_returns_to_usable_input")
    assert not basic.passed, (
        "basic_turn should FAIL when composer is absent after a turn; "
        f"detail={basic.detail}"
    )


def test_spinner_observed_fails_when_no_activity_seen():
    """spinner_observed_during_turn must FAIL on a turn with zero spinner evidence."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"> hello\r\n"
        b"Response content without any spinner chars or verb markers at all.\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="first-prompt-text", rows=50, cols=160)

    spin = _find_hard(report, "spinner_observed_during_turn")
    assert not spin.passed, (
        "spinner should FAIL when no braille chars or verb markers present; "
        f"detail={spin.detail}"
    )


def test_response_followed_generalized_prompt_detection_passes_on_non_hello_body():
    """Per Codex Entry 1171 Concern #2: the prompt detector must accept
    any `> <body>` echo, not just a hard-coded "hello". Proves
    error-state / spinner-cadence scenarios can legitimately enforce
    this invariant instead of getting N/A credit.
    """
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"> __WARNING__ deliberate test\r\n"                          # non-"hello" prompt body
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6 (1s)\r\n"
        b"Warning emitted and the response contains enough real text.\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    resp = _find_hard(report, "response_followed_user_prompt")
    assert resp.passed, f"response should PASS on generalized prompt body; detail={resp.detail}"
    assert "substantial content after prompt" in resp.detail


def test_response_followed_ignores_composer_placeholder_as_prompt_line():
    """The `❯ Ask AutoCode…` composer placeholder must NOT be mistaken
    for a user-prompt echo. Without a real prompt body the predicate
    must report "no user-prompt echo visible".
    """
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"                 # composer placeholder
        b"some other long line of output that could otherwise trick the check\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    resp = _find_hard(report, "response_followed_user_prompt")
    assert not resp.passed, f"response should FAIL; detail={resp.detail}"
    assert "no user-prompt echo visible" in resp.detail


def test_response_followed_fails_when_only_prompt_echo():
    """response_followed_user_prompt must FAIL when only the prompt is visible."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"> hello\r\n"
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6\r\n"
        # No substantive content after the prompt — response never rendered
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="first-prompt-text", rows=50, cols=160)

    resp = _find_hard(report, "response_followed_user_prompt")
    assert not resp.passed, (
        "response should FAIL when no substantive content follows user prompt; "
        f"detail={resp.detail}"
    )


# -------------------------------------------------------------------------
# picker_filter_accepts_input fixtures (Phase 2 Scenario 1 — model-picker)
# -------------------------------------------------------------------------

def test_picker_filter_na_on_non_picker_scenarios():
    """picker_filter_accepts_input returns PASS with N/A on non-picker scenarios."""
    synthetic = b"\x1b[2J\x1b[HAutoCode header\r\n> hello\r\n"
    for scen in ("startup", "first-prompt-text"):
        report = run_predicates(synthetic, scenario=scen, rows=50, cols=160)
        pred = _find_hard(report, "picker_filter_accepts_input")
        assert pred.passed, f"picker predicate should PASS N/A on {scen}"
        assert "N/A" in pred.detail


def test_picker_filter_passes_when_filter_header_visible():
    """Picker open AND `[filter: cod]` visible → predicate PASSES."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Select a model:  [filter: cod]\r\n"
        b"  coding         (tools, openrouter)\r\n"
        b"  coding_cloud   (cloud)\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="model-picker", rows=50, cols=160)
    pred = _find_hard(report, "picker_filter_accepts_input")
    assert pred.passed, f"picker predicate should PASS; detail={pred.detail}"
    assert "filter header visible" in pred.detail


def test_picker_filter_fails_when_picker_never_opened():
    """Picker scenario but no `Select a model` header → predicate FAILS truthfully."""
    # Simulates a broken capture where /model was sent but the picker
    # never rendered — predicate must not silently pass.
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="model-picker", rows=50, cols=160)
    pred = _find_hard(report, "picker_filter_accepts_input")
    assert not pred.passed, f"picker predicate should FAIL; detail={pred.detail}"
    assert "picker header not visible" in pred.detail


def test_composer_present_false_positive_on_picker_row_fixed():
    """Per Codex Entry 1160 Concern #1: a frame with only `❯ coding` (picker
    selection row, no composer) must NOT satisfy `composer_present` when
    evaluated as a non-picker scenario.

    This is the regression test Codex asked for: proves the false positive
    is gone AND the tightened markers distinguish picker-row from composer.
    """
    picker_only_frame = (
        b"\x1b[2J\x1b[H"
        b"Select a model:  [filter: cod]\r\n"
        b"  \xe2\x9d\xaf coding\r\n"                                 # ❯ coding (picker row)
        b"  Type to filter \xc2\xb7 Up/Down select \xc2\xb7 Enter apply\r\n"
        # NO composer marker — Ask AutoCode / ❯ Ask / > Ask absent
    )

    # Evaluate as `first-prompt-text` (non-picker). Should FAIL because
    # the tightened predicate no longer accepts bare ❯.
    report = run_predicates(picker_only_frame, scenario="first-prompt-text", rows=50, cols=160)
    composer = _find_hard(report, "composer_present")
    assert not composer.passed, (
        "composer_present should FAIL on picker-only frame when scenario is "
        f"non-picker; bare ❯ must not satisfy the predicate; detail={composer.detail}"
    )

    # Same bytes evaluated as `model-picker` scenario — should PASS with N/A
    # because the picker intentionally replaces the composer.
    report_picker = run_predicates(picker_only_frame, scenario="model-picker", rows=50, cols=160)
    composer_picker = _find_hard(report_picker, "composer_present")
    assert composer_picker.passed and "N/A" in composer_picker.detail, (
        f"composer_present should PASS N/A on picker scenario; detail={composer_picker.detail}"
    )


def test_picker_filter_fails_when_picker_open_but_no_filter():
    """Picker opened but filter header missing → predicate FAILS truthfully.

    This catches the case where /model opens the picker but typing didn't
    filter — e.g., the filter-accept handler is broken while the picker
    render itself still works.
    """
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Select a model:\r\n"
        b"  coding         (tools, openrouter)\r\n"
        b"  fast           (fast, cheap)\r\n"
        # No [filter:] header despite user having typed chars
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="model-picker", rows=50, cols=160)
    pred = _find_hard(report, "picker_filter_accepts_input")
    assert not pred.passed, f"picker predicate should FAIL; detail={pred.detail}"
    assert "no filter header" in pred.detail


# -------------------------------------------------------------------------
# approval_prompt_keyboard_interactive fixtures (Phase 2 Scenario 2)
# -------------------------------------------------------------------------

def test_approval_prompt_na_on_non_ask_user_scenarios():
    """approval_prompt_keyboard_interactive returns PASS N/A on non-ask-user scenarios."""
    synthetic = b"\x1b[2J\x1b[HAutoCode header\r\n> hello\r\n"
    for scen in ("startup", "first-prompt-text", "model-picker"):
        report = run_predicates(synthetic, scenario=scen, rows=50, cols=160)
        pred = _find_hard(report, "approval_prompt_keyboard_interactive")
        assert pred.passed, f"approval predicate should PASS N/A on {scen}"
        assert "N/A" in pred.detail


def test_approval_prompt_passes_on_full_modal_fixture():
    """Question + options (❯ glyph + enumerated) + Enter hint → predicate PASSES."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Please choose how to proceed:\r\n"
        b"  \xe2\x9d\xaf 1. Continue\r\n"                    # ❯ 1. Continue
        b"    2. Abort\r\n"
        b"    3. Retry\r\n"
        b"\r\n"
        b"Press Enter to select \xc2\xb7 Esc to cancel\r\n"
    )
    report = run_predicates(synthetic, scenario="ask-user-prompt", rows=50, cols=160)
    pred = _find_hard(report, "approval_prompt_keyboard_interactive")
    assert pred.passed, f"approval predicate should PASS; detail={pred.detail}"
    assert "question, options, and keyboard hint" in pred.detail


def test_approval_prompt_fails_when_question_missing():
    """Options + hint but no question → predicate FAILS."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        # No question line — just options and hint
        b"  \xe2\x9d\xaf 1. Continue\r\n"
        b"    2. Abort\r\n"
        b"Press Enter to select\r\n"
    )
    report = run_predicates(synthetic, scenario="ask-user-prompt", rows=50, cols=160)
    pred = _find_hard(report, "approval_prompt_keyboard_interactive")
    assert not pred.passed, f"approval predicate should FAIL; detail={pred.detail}"
    assert "question text" in pred.detail


def test_approval_prompt_fails_when_options_missing():
    """Question + hint but no option markers → predicate FAILS."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Please choose how to proceed:\r\n"
        # No enumerated options, no glyphs — just a paragraph after the question
        b"something happened, you decide.\r\n"
        b"Press Enter to submit\r\n"
    )
    report = run_predicates(synthetic, scenario="ask-user-prompt", rows=50, cols=160)
    pred = _find_hard(report, "approval_prompt_keyboard_interactive")
    assert not pred.passed, f"approval predicate should FAIL; detail={pred.detail}"
    assert "option markers" in pred.detail


def test_approval_prompt_fails_on_prose_only_option_words():
    """Per Codex Entry 1167 Concern #2: bare option words in prose must
    NOT satisfy the predicate. Question + hint are present, and the
    prose mentions Continue/Abort/Retry, but there is no glyph and no
    enumeration — predicate must FAIL truthfully.
    """
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Please choose how to proceed:\r\n"
        # Prose-style line — mentions option names but no selectable structure
        b"You could Continue, Abort, or Retry depending on the situation.\r\n"
        b"Press Enter to submit\r\n"
    )
    report = run_predicates(synthetic, scenario="ask-user-prompt", rows=50, cols=160)
    pred = _find_hard(report, "approval_prompt_keyboard_interactive")
    assert not pred.passed, (
        "approval predicate should FAIL when options are only present as "
        f"prose words without glyph/enumeration; detail={pred.detail}"
    )
    assert "option markers" in pred.detail


def test_composer_present_na_on_ask_user_scenario():
    """Per the ask-user scenario being modal, composer_present must N/A PASS."""
    # Ask-user modal renders question + options and blurs the composer.
    # composer_present should therefore short-circuit to PASS with N/A.
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"Please choose how to proceed:\r\n"
        b"  \xe2\x9d\xaf 1. Continue\r\n"
        b"    2. Abort\r\n"
        b"Press Enter to select\r\n"
        # No composer marker at all — this is expected on ask-user
    )
    report = run_predicates(synthetic, scenario="ask-user-prompt", rows=50, cols=160)
    composer = _find_hard(report, "composer_present")
    assert composer.passed and "N/A" in composer.detail, (
        f"composer_present should PASS N/A on ask-user scenario; detail={composer.detail}"
    )


# -------------------------------------------------------------------------
# warnings_render_dim_not_red_banner fixtures (Phase 2 Scenario 3)
# -------------------------------------------------------------------------

def test_warnings_dim_banner_na_on_non_error_scenarios():
    """Non-error-state scenarios short-circuit to PASS with N/A."""
    synthetic = b"\x1b[2J\x1b[HAutoCode\r\n\xe2\x9a\xa0 [backend] WARNING: x\r\n"
    for scen in ("startup", "first-prompt-text", "model-picker", "ask-user-prompt"):
        report = run_predicates(synthetic, scenario=scen, rows=50, cols=160)
        pred = _find_hard(report, "warnings_render_dim_not_red_banner")
        assert pred.passed, f"predicate should PASS N/A on {scen}"
        assert "N/A" in pred.detail


def test_warnings_dim_banner_passes_on_deliberate_mid_session_dim_marker():
    """Deliberate mid-session warning visible on a ⚠-prefixed dim line → PASS."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"\xe2\x9a\xa0 [backend] WARNING: mock backend starting\r\n"
        b"> __WARNING__ deliberate test\r\n"
        b"\xe2\x9a\xa0 [backend] WARNING: deliberate mid-session warning from mock backend\r\n"
        b"Warning emitted.\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    pred = _find_hard(report, "warnings_render_dim_not_red_banner")
    assert pred.passed, f"predicate should PASS; detail={pred.detail}"
    assert "deliberate mid-session warning rendered" in pred.detail


def test_warnings_dim_banner_fails_when_warning_inside_error_banner():
    """If WARNING text ends up inside an `Error:` banner → FAIL."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"\xe2\x9a\xa0 [backend] WARNING: ok dim warning\r\n"
        # Cross-pollution — this should never happen but we assert the
        # predicate catches it if severity classification breaks.
        b"Error: [backend] WARNING: should have been dim\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    pred = _find_hard(report, "warnings_render_dim_not_red_banner")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"
    assert "leaked into the red `Error:` banner" in pred.detail


def test_warnings_dim_banner_fails_on_startup_only_warning():
    """Per Codex Entry 1171 Concern #1: the ever-present startup warning
    alone must NOT satisfy the predicate. Without the deliberate
    mid-session trigger text, Scenario 3 has not actually proven the
    `__WARNING__` path; predicate must FAIL truthfully.
    """
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        # Only the startup warning from mock_backend.py's initial print
        b"\xe2\x9a\xa0 [backend] WARNING: mock backend starting \xe2\x80\x94 this is a test warning\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    pred = _find_hard(report, "warnings_render_dim_not_red_banner")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"
    assert "deliberate mid-session" in pred.detail


def test_warnings_dim_banner_fails_when_deliberate_warning_not_dim():
    """Deliberate warning visible but on a non-⚠ line → FAIL."""
    # Simulates the severity classifier demoting the warning to plain
    # text (no ⚠ prefix). Distinct from the cross-pollution case: here
    # the text isn't in an `Error:` banner, it's just un-prefixed.
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"deliberate mid-session warning from mock backend\r\n"
    )
    report = run_predicates(synthetic, scenario="error-state", rows=50, cols=160)
    pred = _find_hard(report, "warnings_render_dim_not_red_banner")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"
    assert "NOT on a ⚠-prefixed dim scrollback line" in pred.detail


# -------------------------------------------------------------------------
# startup_timeout_fires_when_backend_absent fixtures (Phase 2 Scenario 4)
# -------------------------------------------------------------------------

def test_startup_timeout_na_on_non_orphan_scenarios():
    """Non-orphaned-startup scenarios short-circuit to PASS with N/A."""
    synthetic = b"\x1b[2J\x1b[HAutoCode up and running\r\n"
    for scen in ("startup", "first-prompt-text", "error-state"):
        report = run_predicates(synthetic, scenario=scen, rows=50, cols=160)
        pred = _find_hard(report, "startup_timeout_fires_when_backend_absent")
        assert pred.passed, f"predicate should PASS N/A on {scen}"
        assert "N/A" in pred.detail


def test_startup_timeout_passes_when_banner_visible():
    """Orphaned-startup frame with the canonical banner → PASS."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 Edge-native AI coding assistant\r\n"
        b"Error: Backend not connected (startup timeout). Commands requiring the backend will fail.\r\n"
        b"\xe2\x9d\xaf Ask AutoCode\xe2\x80\xa6\r\n"
    )
    report = run_predicates(synthetic, scenario="orphaned-startup", rows=50, cols=160)
    pred = _find_hard(report, "startup_timeout_fires_when_backend_absent")
    assert pred.passed, f"predicate should PASS; detail={pred.detail}"
    assert "startup-timeout text present" in pred.detail


def test_startup_timeout_fails_when_banner_absent():
    """Orphaned-startup frame without the banner → FAIL truthfully."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode \xe2\x94\x80 loading...\r\n"
        # No banner; stuck in stageInit
    )
    report = run_predicates(synthetic, scenario="orphaned-startup", rows=50, cols=160)
    pred = _find_hard(report, "startup_timeout_fires_when_backend_absent")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"
    assert "no startup-timeout" in pred.detail


# -------------------------------------------------------------------------
# spinner_frame_updates_over_time fixtures (Phase 2 Scenario 5)
# -------------------------------------------------------------------------

def test_spinner_cadence_na_on_non_cadence_scenarios():
    """Non-spinner-cadence scenarios short-circuit to PASS with N/A."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6\r\n"    # just one ⠙ frame
    )
    for scen in ("startup", "first-prompt-text", "model-picker"):
        report = run_predicates(synthetic, scenario=scen, rows=50, cols=160)
        pred = _find_hard(report, "spinner_frame_updates_over_time")
        assert pred.passed, f"predicate should PASS N/A on {scen}"
        assert "N/A" in pred.detail


def test_spinner_cadence_passes_with_multiple_frames():
    """≥2 distinct braille chars in raw → PASS."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"> __SLOW__\r\n"
        b"\xe2\xa0\x99 Thinking\xe2\x80\xa6\r\n"    # ⠙
        b"\xe2\xa0\xb9 Thinking\xe2\x80\xa6\r\n"    # ⠹
        b"\xe2\xa0\xb8 Thinking\xe2\x80\xa6\r\n"    # ⠸
        b"Done.\r\n"
    )
    report = run_predicates(synthetic, scenario="spinner-cadence", rows=50, cols=160)
    pred = _find_hard(report, "spinner_frame_updates_over_time")
    assert pred.passed, f"predicate should PASS; detail={pred.detail}"
    assert "distinct braille frames" in pred.detail


def test_spinner_cadence_fails_with_only_one_frame():
    """Only one distinct braille glyph → FAIL truthfully."""
    synthetic = (
        b"\x1b[2J\x1b[H"
        b"AutoCode\r\n"
        b"> __SLOW__\r\n"
        # Same ⠙ glyph repeated many times — spinner frozen, not rotating
        b"\xe2\xa0\x99 Thinking...\r\n" * 10
    )
    report = run_predicates(synthetic, scenario="spinner-cadence", rows=50, cols=160)
    pred = _find_hard(report, "spinner_frame_updates_over_time")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"


def test_spinner_cadence_fails_when_no_braille_at_all():
    """Zero braille chars → FAIL truthfully."""
    synthetic = b"\x1b[2J\x1b[HAutoCode\r\nno spinner here\r\n"
    report = run_predicates(synthetic, scenario="spinner-cadence", rows=50, cols=160)
    pred = _find_hard(report, "spinner_frame_updates_over_time")
    assert not pred.passed, f"predicate should FAIL; detail={pred.detail}"
    assert "no braille spinner chars" in pred.detail
