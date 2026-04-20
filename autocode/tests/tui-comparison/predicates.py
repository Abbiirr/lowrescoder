"""Predicates — layout/chrome checks operating on a pyte Screen.

Every predicate is classified:

- ``HARD``  — autocode correctness invariant. Failure = Track 1 regression.
- ``SOFT``  — Claude-Code-like style target. Failure = Track 3 backlog
              item (NOT a regression).

Predicates run against a ``pyte.Screen`` (2D cell grid) plus the
stripped text. They return ``PredicateResult`` records that serialize
into ``predicates.json`` for the capture run.

Hard invariants mirror the repo's existing TUI validation policy in
``docs/tests/tui-testing-strategy.md``. Soft targets mirror the gaps
observed in ``docs/plan/tui-style-gap-backlog.md``.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


class PredicateClass(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass
class PredicateResult:
    name: str
    classification: PredicateClass
    passed: bool
    detail: str = ""


@dataclass
class PredicateReport:
    hard: list[PredicateResult] = field(default_factory=list)
    soft: list[PredicateResult] = field(default_factory=list)

    @property
    def all_hard_passed(self) -> bool:
        return all(r.passed for r in self.hard)

    def to_json(self) -> str:
        return json.dumps(
            {
                "hard": {r.name: {"passed": r.passed, "detail": r.detail} for r in self.hard},
                "soft": {r.name: {"passed": r.passed, "detail": r.detail} for r in self.soft},
                "summary": {
                    "hard_passed": sum(1 for r in self.hard if r.passed),
                    "hard_total": len(self.hard),
                    "soft_passed": sum(1 for r in self.soft if r.passed),
                    "soft_total": len(self.soft),
                    "all_hard_passed": self.all_hard_passed,
                },
            },
            indent=2,
            sort_keys=True,
        )

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
        return path


# -- Adapter helpers --------------------------------------------------------

def render_screen(raw: bytes, rows: int, cols: int):
    """Run the captured ANSI bytes through pyte; return (screen, text)."""
    import pyte

    # Strip kitty-protocol CSI-u sequences that pyte mis-parses
    kitty_strip = re.compile(rb"\x1b\[[?>=<0-9;:]*u")
    cleaned = kitty_strip.sub(b"", raw)

    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    stream.feed(cleaned.decode("utf-8", errors="replace"))
    text = "\n".join(screen.display)
    return screen, text


# -- Hard invariants --------------------------------------------------------

def _pred_no_crash(text: str, raw: bytes) -> PredicateResult:
    """If raw is empty, the capture crashed immediately."""
    passed = len(raw) > 32  # anything more than just terminal queries
    return PredicateResult(
        name="no_crash_during_capture",
        classification=PredicateClass.HARD,
        passed=passed,
        detail=f"raw_bytes={len(raw)}",
    )


def _pred_composer_present(text: str, scenario: str) -> PredicateResult:
    """Composer zone visible on screen.

    Per Codex Entry 1160 Concern #1, bare ``>`` / ``❯`` are **too
    permissive** — picker rows like ``❯ coding`` (the selection glyph)
    falsely satisfied the earlier broad marker set. This version:

    1. Returns PASS with N/A for picker scenarios, where the picker
       intentionally REPLACES the composer and its absence is correct.
    2. For all other scenarios, uses composer-specific marker shapes
       (``Ask AutoCode``, ``❯ Ask``, ``> Ask``, ``│ > ``, ``│ ❯ ``).
       A bare selection glyph is insufficient.
    """
    if scenario in _PICKER_SCENARIOS:
        return PredicateResult(
            name="composer_present",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — picker scenario {scenario!r} replaces the composer",
        )
    if scenario in _ASK_USER_SCENARIOS:
        return PredicateResult(
            name="composer_present",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — ask-user scenario {scenario!r} replaces the composer with a modal",
        )
    # Composer-specific markers — each anchored to a composer-line shape,
    # not a bare selection glyph. Includes both Go-era markers and the
    # Rust TUI's minimal `> ` prompt at end-of-line.
    markers = ("Ask AutoCode", "❯ Ask", "> Ask", "│ > ", "│ ❯ ")
    lines = text.split("\n")
    passed = any(any(m in line for m in markers) for line in lines)
    # Rust TUI uses a minimal `> ` prompt at the end of the last line
    # (after the status bar). Check for `> ` in the line or `>` at end of
    # stripped line as a fallback.
    if not passed:
        passed = any("> " in line or line.rstrip().endswith(">") for line in lines)
    return PredicateResult(
        name="composer_present",
        classification=PredicateClass.HARD,
        passed=passed,
        detail=(
            "none of the composer markers found"
            if not passed
            else "composer-specific marker present"
        ),
    )


def _pred_no_queue_leak(text: str) -> PredicateResult:
    """No raw queue debug text like 'queue:' or 'steering_queue' leaks to scrollback."""
    bad = ("<<STEER", "steering_queue", "queue_debug", "[queue]")
    found = [b for b in bad if b in text]
    return PredicateResult(
        name="no_queue_debug_leak",
        classification=PredicateClass.HARD,
        passed=not found,
        detail=("clean" if not found else f"leaked: {found}"),
    )


# -- Turn-scoped hard invariants (apply only to scenarios that involve a turn)

_TURN_SCENARIOS = {
    "first-prompt-text",
    "first-prompt-code",
    "streaming-mid-frame",
    "error-state",
    "spinner-cadence",
}
_PICKER_SCENARIOS = {"model-picker", "provider-picker", "session-picker"}
_ASK_USER_SCENARIOS = {"ask-user-prompt"}
_ERROR_STATE_SCENARIOS = {"error-state"}
_ORPHAN_SCENARIOS = {"orphaned-startup"}
_SPINNER_CADENCE_SCENARIOS = {"spinner-cadence"}


def _pred_basic_turn_returns_to_usable_input(text: str, scenario: str) -> PredicateResult:
    """After a send/response cycle, the composer must be ready for new input.

    Aligns with ``docs/tests/tui-testing-strategy.md`` "Basic Chat Turn"
    requirement and Codex Entry 1141 Suggested Change #3.

    Scenarios without a turn return N/A PASS.
    """
    if scenario not in _TURN_SCENARIOS:
        return PredicateResult(
            name="basic_turn_returns_to_usable_input",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} has no turn",
        )
    # Turn scenarios send "hello" — look for evidence of the user prompt echo
    # and the composer still being present after the response.
    composer_markers = ("❯ Ask", "❯ ", "│ > ", "│ ❯", "> Ask", "Ask AutoCode")
    composer_present = any(m in text for m in composer_markers)
    return PredicateResult(
        name="basic_turn_returns_to_usable_input",
        classification=PredicateClass.HARD,
        passed=composer_present,
        detail=(
            "composer still visible after turn"
            if composer_present
            else "no composer marker after turn — input not regained"
        ),
    )


def _pred_spinner_observed_during_turn(text: str, raw: bytes, scenario: str) -> PredicateResult:
    """A turn scenario must show spinner activity in the captured stream.

    Looks for autocode's braille-spinner chars OR the verb/word markers
    that ride alongside them. Scenarios without a turn return N/A PASS.
    """
    if scenario not in _TURN_SCENARIOS:
        return PredicateResult(
            name="spinner_observed_during_turn",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} has no turn",
        )
    try:
        raw_text = raw.decode("utf-8", errors="replace")
    except Exception:
        raw_text = ""
    braille_chars = "⠙⠹⠸⠼⠴⠦⠧⠇⠏⠋⠛⠓"
    braille_seen = any(ch in raw_text for ch in braille_chars)
    verb_markers = (
        "Thinking",
        "Pondering",
        "Working",
        "Creating",
        "Reasoning",
        "Connecting",
        "Synthesizing",
        "Processing",
    )
    verb_seen = any(v in text for v in verb_markers)
    passed = braille_seen or verb_seen
    return PredicateResult(
        name="spinner_observed_during_turn",
        classification=PredicateClass.HARD,
        passed=passed,
        detail=(
            "spinner activity detected"
            if passed
            else "no spinner chars or verb markers seen during turn"
        ),
    )


def _pred_response_followed_user_prompt(text: str, scenario: str) -> PredicateResult:
    """After the user prompt, there must be substantive content — not just the prompt echo.

    Distinguishes "response rendered" from "prompt merely still visible".
    Scenarios without a turn return N/A PASS.

    Per Codex Entry 1171 Concern #2, the user-prompt detector is
    generalized from the hard-coded "hello" lookup to any ``> <body>``
    (or ``❯ <body>``) echo line whose body is NOT placeholder/chrome —
    so scenarios like ``error-state`` and ``spinner-cadence`` (which
    send ``__WARNING__`` / ``__SLOW__`` triggers) can legitimately
    enforce this invariant instead of getting N/A credit.
    """
    if scenario not in _TURN_SCENARIOS:
        return PredicateResult(
            name="response_followed_user_prompt",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} has no turn",
        )
    lines = text.split("\n")
    placeholder_markers = (
        "Ask AutoCode",
        "Type a message",
        "Use /help",
        "Welcome",
    )
    # Find any line that looks like a user-prompt echo: starts with
    # `> ` or `❯ ` and has a body that isn't a composer placeholder.
    prompt_line_idx = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        body: str | None = None
        if stripped.startswith("> "):
            body = stripped[2:].strip()
        elif stripped.startswith("❯ "):
            body = stripped[2:].strip()
        if not body:
            continue
        if any(ph in body for ph in placeholder_markers):
            continue
        prompt_line_idx = i
        break

    if prompt_line_idx is None:
        return PredicateResult(
            name="response_followed_user_prompt",
            classification=PredicateClass.HARD,
            passed=False,
            detail="no user-prompt echo visible in output — send may have failed",
        )
    # Look for substantial non-chrome content AFTER the user prompt line
    chrome_chars = set("─│╭╮╰╯┌┐└┘━┃✻◆⚠▸·⠙⠹⠸⠼⠴⠦⠧⠇⠏ ")
    for line in lines[prompt_line_idx + 1 :]:
        stripped = line.strip()
        if len(stripped) >= 20 and not all(c in chrome_chars for c in stripped):
            return PredicateResult(
                name="response_followed_user_prompt",
                classification=PredicateClass.HARD,
                passed=True,
                detail=f"substantial content after prompt ({len(stripped)} chars)",
            )
    return PredicateResult(
        name="response_followed_user_prompt",
        classification=PredicateClass.HARD,
        passed=False,
        detail="no substantial response content after user prompt",
    )


def _pred_picker_filter_accepts_input(text: str, scenario: str) -> PredicateResult:
    """For picker scenarios, typed filter text must appear in the picker's filter header.

    autocode's picker renders `Select a model:  [filter: cod]` once the user
    has typed filter chars. Non-picker scenarios return PASS with N/A.

    Unlocks per Codex Entry 1154 Phase 2 Suggested Change #2 — moved from
    "Full Track 1 target set" into the Phase 2 enforced subset.
    """
    if scenario not in _PICKER_SCENARIOS:
        return PredicateResult(
            name="picker_filter_accepts_input",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} is not a picker scenario",
        )
    # Picker must be open AND filter text visible.
    picker_open = any(
        marker in text
        for marker in ("Select a model", "Select a provider", "Select a session")
    )
    if not picker_open:
        return PredicateResult(
            name="picker_filter_accepts_input",
            classification=PredicateClass.HARD,
            passed=False,
            detail="picker header not visible — /model send may have failed",
        )
    # Filter header should include `[filter: cod]` (or whatever was typed).
    # We check for the generic `[filter:` token rather than exact content
    # so this predicate can serve all picker scenarios without coupling
    # to a specific filter string.
    filter_header_visible = "[filter:" in text or "filter: " in text
    return PredicateResult(
        name="picker_filter_accepts_input",
        classification=PredicateClass.HARD,
        passed=filter_header_visible,
        detail=(
            "picker open and filter header visible"
            if filter_header_visible
            else "picker open but no filter header — typing did not filter"
        ),
    )


def _pred_approval_prompt_keyboard_interactive(text: str, scenario: str) -> PredicateResult:
    """For ask-user-prompt scenarios, the modal must render interactively.

    Claude Code's approval/ask-user modals show:
      1. A question line (free-form text — Codex Entry 1154 calls this
         the "prompt" — we look for the mock's literal question text).
      2. Option markers — either ``❯``/``●``/``○`` glyphs or an enumerated
         list (``1.`` / ``2.``).
      3. A keyboard hint — wording like ``Enter`` or numeric keystrokes
         that tells the user how to drive it.

    Non-ask-user scenarios return PASS with N/A so the predicate is a
    no-op outside its enforcement domain. Per PLAN.md §1g, this lives
    in the Phase 1 + Phase 2 enforced subset once Scenario 2 lands.
    """
    if scenario not in _ASK_USER_SCENARIOS:
        return PredicateResult(
            name="approval_prompt_keyboard_interactive",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} has no ask-user modal",
        )

    # 1. Question visible? Mock emits the literal question text.
    question_markers = ("Please choose how to proceed", "choose how to proceed")
    question_visible = any(m in text for m in question_markers)

    # 2. Option markers — interactive glyphs OR enumerated list. Bare
    #    option-word detection was removed per Codex Entry 1167 Concern
    #    #2: prose mentioning the option words must not count as proof
    #    of selectable structure.
    option_glyphs = ("❯", "●", "○")
    option_glyph_visible = any(g in text for g in option_glyphs)
    enumeration_re = re.compile(r"(?m)^\s*\d+\.\s+\S")
    enumerated = bool(enumeration_re.search(text))
    options_visible = option_glyph_visible or enumerated

    # 3. Keyboard hint — the renderer always shows the composer hint OR
    #    explicit keyboard wording in the ask-user view.
    hint_markers = ("Enter", "enter", "Esc", "esc", "(or type", "type your answer")
    hint_visible = any(m in text for m in hint_markers)

    missing = []
    if not question_visible:
        missing.append("question text")
    if not options_visible:
        missing.append("option markers")
    if not hint_visible:
        missing.append("keyboard hint")

    return PredicateResult(
        name="approval_prompt_keyboard_interactive",
        classification=PredicateClass.HARD,
        passed=not missing,
        detail=(
            "question, options, and keyboard hint all visible"
            if not missing
            else f"missing: {', '.join(missing)}"
        ),
    )


def _pred_warnings_render_dim_not_red_banner(text: str, scenario: str) -> PredicateResult:
    """For error-state scenarios, the **deliberate mid-session** WARNING must render DIM.

    autocode's stderr severity classifier splits WARNING lines onto a
    dim ``⚠ [backend] …`` scrollback line, while ERROR/CRITICAL lines
    land in ``m.lastError`` and show as a red ``Error: …`` banner.

    Per Codex Entry 1171 Concern #1, this predicate must prove the
    Scenario 3 ``__WARNING__`` trigger path actually landed — not just
    that *any* warning (like the ever-present startup warning) rendered
    dim. So it verifies:

      1. The line that was emitted mid-session via the ``__WARNING__``
         trigger (``deliberate mid-session warning``) is visible AND is
         on a ``⚠``-prefixed dim scrollback line (not in a red banner).
      2. No ``Error: ... WARNING`` cross-pollution — no WARNING text
         got swept into the red error banner.

    Non-error-state scenarios return PASS with N/A.
    """
    if scenario not in _ERROR_STATE_SCENARIOS:
        return PredicateResult(
            name="warnings_render_dim_not_red_banner",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} is not an error-state scenario",
        )

    # Cross-pollution guard: `Error:` banner must not contain WARNING text.
    banner_re = re.compile(r"Error:\s*(.*)")
    banner_matches = banner_re.findall(text)
    cross_pollution = any("WARNING" in m.upper() for m in banner_matches)
    if cross_pollution:
        return PredicateResult(
            name="warnings_render_dim_not_red_banner",
            classification=PredicateClass.HARD,
            passed=False,
            detail="WARNING text leaked into the red `Error:` banner",
        )

    # Find the line carrying the deliberate mid-session warning text.
    deliberate_marker = "deliberate mid-session warning"
    deliberate_lines = [
        line for line in text.split("\n") if deliberate_marker in line
    ]
    if not deliberate_lines:
        return PredicateResult(
            name="warnings_render_dim_not_red_banner",
            classification=PredicateClass.HARD,
            passed=False,
            detail=(
                "no line containing the deliberate mid-session warning text — "
                "Scenario 3 `__WARNING__` trigger did NOT land"
            ),
        )

    # That deliberate line must be dim-rendered (⚠ prefix on the same line).
    deliberate_dim = any("⚠" in line for line in deliberate_lines)
    if not deliberate_dim:
        return PredicateResult(
            name="warnings_render_dim_not_red_banner",
            classification=PredicateClass.HARD,
            passed=False,
            detail=(
                "deliberate mid-session warning is visible but NOT on a "
                "⚠-prefixed dim scrollback line"
            ),
        )

    return PredicateResult(
        name="warnings_render_dim_not_red_banner",
        classification=PredicateClass.HARD,
        passed=True,
        detail=(
            "deliberate mid-session warning rendered on a ⚠-prefixed dim "
            "line; no WARNING text leaked into the red banner"
        ),
    )


def _pred_startup_timeout_fires_when_backend_absent(text: str, scenario: str) -> PredicateResult:
    """For orphaned-startup scenarios, the TUI must surface a timeout error.

    autocode's ``startupTimeoutMsg`` handler sets ``m.lastError`` to a
    string containing ``Backend not connected (startup timeout)`` after
    15s without an ``on_status`` message. This predicate verifies the
    captured frame includes that signature.

    Non-orphaned-startup scenarios return PASS with N/A.
    """
    if scenario not in _ORPHAN_SCENARIOS:
        return PredicateResult(
            name="startup_timeout_fires_when_backend_absent",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} is not an orphaned-startup scenario",
        )
    signature_markers = (
        "startup timeout",
        "Backend not connected",
    )
    matched = [m for m in signature_markers if m in text]
    return PredicateResult(
        name="startup_timeout_fires_when_backend_absent",
        classification=PredicateClass.HARD,
        passed=bool(matched),
        detail=(
            f"startup-timeout text present: {matched}"
            if matched
            else "no startup-timeout/`Backend not connected` text in frame"
        ),
    )


def _pred_spinner_frame_updates_over_time(raw: bytes, scenario: str) -> PredicateResult:
    """For spinner-cadence scenarios, ≥2 distinct braille chars must appear.

    Scans the full raw ANSI byte stream — not just the final pyte
    frame — because the spinner glyph rotates across renders and only
    the most recent one survives on-screen. Existing ``_pred_spinner_
    observed_during_turn`` accepts one glyph; this tighter predicate
    enforces that the spinner **actually rotates** (multi-frame), which
    proves the render loop is ticking.

    Non-spinner-cadence scenarios return PASS with N/A.
    """
    if scenario not in _SPINNER_CADENCE_SCENARIOS:
        return PredicateResult(
            name="spinner_frame_updates_over_time",
            classification=PredicateClass.HARD,
            passed=True,
            detail=f"N/A — scenario {scenario!r} is not a spinner-cadence scenario",
        )
    try:
        raw_text = raw.decode("utf-8", errors="replace")
    except Exception:
        raw_text = ""
    braille_chars = "⠙⠹⠸⠼⠴⠦⠧⠇⠏⠋⠛⠓"
    distinct = {ch for ch in braille_chars if ch in raw_text}
    return PredicateResult(
        name="spinner_frame_updates_over_time",
        classification=PredicateClass.HARD,
        passed=len(distinct) >= 2,
        detail=(
            f"saw {len(distinct)} distinct braille frames: {''.join(sorted(distinct))}"
            if distinct
            else "no braille spinner chars observed in raw stream"
        ),
    )


HARD_PREDICATES: list[Callable] = [
    _pred_no_crash,
    _pred_composer_present,
    _pred_no_queue_leak,
    _pred_basic_turn_returns_to_usable_input,
    _pred_spinner_observed_during_turn,
    _pred_response_followed_user_prompt,
    _pred_picker_filter_accepts_input,
    _pred_approval_prompt_keyboard_interactive,
    _pred_warnings_render_dim_not_red_banner,
    _pred_startup_timeout_fires_when_backend_absent,
    _pred_spinner_frame_updates_over_time,
]


# -- Soft style targets -----------------------------------------------------

def _pred_composer_has_rounded_border(text: str) -> PredicateResult:
    """Composer area uses rounded Unicode border chars ``╭┌╒╓`` somewhere."""
    rounded_corners = ("╭", "╮", "╰", "╯", "┌", "┐", "└", "┘")
    passed = any(c in text for c in rounded_corners)
    return PredicateResult(
        name="composer_has_rounded_border",
        classification=PredicateClass.SOFT,
        passed=passed,
        detail=(
            "found rounded/box border chars"
            if passed
            else "no rounded-border characters found (Track 3 gap H1)"
        ),
    )


def _pred_spinner_has_interrupt_hint(text: str) -> PredicateResult:
    """Spinner line contains ``interrupt`` or ``esc`` (case-insensitive).

    This is a SOFT target: autocode's current spinner does not include
    the hint, so this is expected to fail on baseline captures and
    flip green once Track 3 backlog item H2 lands.
    """
    lowered = text.lower()
    passed = "interrupt" in lowered or "esc " in lowered or "ctrl+c to interrupt" in lowered
    return PredicateResult(
        name="spinner_has_interrupt_hint",
        classification=PredicateClass.SOFT,
        passed=passed,
        detail=(
            "interrupt hint present"
            if passed
            else "no interrupt-hint text found (Track 3 gap H2)"
        ),
    )


SOFT_PREDICATES: list[Callable] = [
    _pred_composer_has_rounded_border,
    _pred_spinner_has_interrupt_hint,
]


# -- Entry point ------------------------------------------------------------

def run_predicates(
    raw: bytes,
    *,
    scenario: str = "",
    rows: int = 50,
    cols: int = 160,
) -> PredicateReport:
    """Run all hard + soft predicates against the captured bytes.

    ``scenario`` is passed through to predicates that want to decide per
    scenario (e.g., turn-scoped predicates return N/A on scenarios
    without a turn).
    """
    _, text = render_screen(raw, rows, cols)
    report = PredicateReport()
    for fn in HARD_PREDICATES:
        # Hard predicates take variable signatures — normalize by inspection
        params = fn.__code__.co_varnames[: fn.__code__.co_argcount]
        kwargs = {}
        if "text" in params:
            kwargs["text"] = text
        if "raw" in params:
            kwargs["raw"] = raw
        if "scenario" in params:
            kwargs["scenario"] = scenario
        result = fn(**kwargs)
        report.hard.append(result)
    for fn in SOFT_PREDICATES:
        report.soft.append(fn(text))
    return report
