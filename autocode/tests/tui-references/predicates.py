"""Reference-contract predicates.

Each predicate consumes a ``pyte.Screen`` + its flattened ``text`` (produced
via ``autocode/tests/tui-comparison/predicates.render_screen``) plus the
extracted scene record from ``manifest.yaml`` and returns a
``ReferenceCheck`` describing whether the live TUI capture matches the
reference scene contract.

Predicates are deterministic and text-level — no SSIM, no image metrics,
no fuzzy thresholds. The pass/fail truth is anchored text + layout zone
presence.

Stubbed scenes (``populated=false`` in the manifest) short-circuit to a
single N/A check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class ReferenceVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NA = "n/a"


@dataclass
class ReferenceCheck:
    """One predicate's outcome against one scene."""

    name: str
    verdict: ReferenceVerdict
    detail: str = ""


@dataclass
class ReferenceReport:
    """Collected predicate outcomes for a single scene."""

    scene_id: str
    label: str
    checks: list[ReferenceCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.verdict is not ReferenceVerdict.FAIL for c in self.checks)

    def failures(self) -> list[ReferenceCheck]:
        return [c for c in self.checks if c.verdict is ReferenceVerdict.FAIL]

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "label": self.label,
            "all_passed": self.all_passed,
            "checks": [
                {
                    "name": c.name,
                    "verdict": c.verdict.value,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


# ----------------------------------------------------------------- manifest IO

class _SceneLike(Protocol):
    scene_id: str
    label: str
    page_number: int
    populated: bool
    anchors: list[str]
    region_classes: list[str]
    class_counts: dict[str, int]


def _as_scene(obj: _SceneLike | dict[str, Any]) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    return {
        "scene_id": obj.scene_id,
        "label": obj.label,
        "page_number": obj.page_number,
        "populated": obj.populated,
        "anchors": list(obj.anchors),
        "region_classes": list(obj.region_classes),
        "class_counts": dict(obj.class_counts),
    }


# ------------------------------------------------------------------- predicates

# Minimum non-empty rows for the PTY frame to count as "captured at all".
# Named so the predicate detail can't silently drift from the threshold.
# Full-frame presence is NOT this floor's job — that belongs to the
# hud / composer / keybind predicates below.
_CAPTURE_SANITY_ROW_FLOOR: int = 5


# Composer shapes. Mirrors the tui-comparison set plus the mockup's
# panel-bordered variants.
_COMPOSER_MARKERS: tuple[str, ...] = (
    "Ask AutoCode",
    "❯ Ask",
    "> Ask",
    "│ > │",
    "│ ❯ │",
)
_OVERLAY_STAGE_PROMPTS: tuple[str, ...] = ("Picker>", "Palette>")

# Characteristic HUD tokens. The mockups put these on one or two rows at
# the top of the terminal window. A live Go TUI capture is allowed to
# arrange them across up to 4 rows to absorb line wrapping.
_HUD_TOKENS: tuple[str, ...] = (
    "tasks:",
    "agents:",
    "sandbox",
    "t:",
    "a:",
)

# Keybind hints appear in a footer row on the mockup.
_KEYBIND_TOKENS: tuple[str, ...] = (
    "Ctrl",
    "Esc",
)


def _top_strip(text: str, rows: int = 6) -> str:
    return "\n".join(text.split("\n")[:rows])


def _bottom_strip(text: str, rows: int = 6) -> str:
    lines = text.split("\n")
    return "\n".join(lines[-rows:])


def _nonempty_rows(text: str) -> int:
    return sum(1 for line in text.split("\n") if line.strip())


def _find_first(haystack: str, needles: tuple[str, ...]) -> str | None:
    for needle in needles:
        if needle in haystack:
            return needle
    return None


def _normalize_frame_line(line: str) -> str:
    candidate = line.lstrip()
    while candidate[:1] in {"│", "┃", "|"}:
        candidate = candidate[1:].lstrip()
    return candidate


def _line_has_composer_marker(line: str) -> bool:
    if _find_first(line, _COMPOSER_MARKERS) is not None:
        return True
    normalized = _normalize_frame_line(line)
    if _find_first(normalized, _COMPOSER_MARKERS + _OVERLAY_STAGE_PROMPTS) is not None:
        return True
    stripped = normalized.strip(" │┃|")
    return stripped in {">", "❯"}


def _pred_tokens_in_strip(
    *,
    name: str,
    strip: str,
    tokens: tuple[str, ...],
    strip_label: str,
) -> ReferenceCheck:
    """Pass if any of ``tokens`` appears in ``strip``."""
    found = [tok for tok in tokens if tok in strip]
    return ReferenceCheck(
        name=name,
        verdict=ReferenceVerdict.PASS if found else ReferenceVerdict.FAIL,
        detail=(
            f"matched: {sorted(found)}"
            if found
            else f"no expected token found in {strip_label}"
        ),
    )


def _pred_hud_present(text: str) -> ReferenceCheck:
    return _pred_tokens_in_strip(
        name="hud_present",
        strip=_top_strip(text, rows=6),
        tokens=_HUD_TOKENS,
        strip_label="the top 6 rows",
    )


def _pred_composer_present(text: str) -> ReferenceCheck:
    bottom_lines = _bottom_strip(text, rows=10).split("\n")
    marker = next(
        (line for line in bottom_lines if _line_has_composer_marker(line)),
        None,
    )
    return ReferenceCheck(
        name="composer_present",
        verdict=ReferenceVerdict.PASS if marker else ReferenceVerdict.FAIL,
        detail=(
            f"matched composer row {marker!r}"
            if marker
            else "no composer marker found in the bottom 10 rows"
        ),
    )


def _pred_keybind_footer_present(text: str) -> ReferenceCheck:
    return _pred_tokens_in_strip(
        name="keybind_footer_present",
        strip=_bottom_strip(text, rows=4),
        tokens=_KEYBIND_TOKENS,
        strip_label="the bottom 4 rows",
    )


def _pred_anchor_text_coverage(
    text: str, anchors: list[str], threshold: float = 0.25,
) -> ReferenceCheck:
    """Fraction of scene-specific *short tokens* found in the live text.

    The manifest anchors are long concatenated strings (whole-row textual
    content from the mockup). A live capture will never match them byte-for-
    byte — that would only prove our renderer imitates JPEG. What matters
    is that key recognizable tokens survive the PTY round-trip.
    """
    if not anchors:
        return ReferenceCheck(
            name="anchor_text_coverage",
            verdict=ReferenceVerdict.NA,
            detail="no anchors in manifest for this scene",
        )
    tokens = _derive_signal_tokens(anchors)
    if not tokens:
        return ReferenceCheck(
            name="anchor_text_coverage",
            verdict=ReferenceVerdict.NA,
            detail="no discriminating tokens derivable from anchors",
        )
    hits = [t for t in tokens if t in text]
    ratio = len(hits) / len(tokens)
    passed = ratio >= threshold
    return ReferenceCheck(
        name="anchor_text_coverage",
        verdict=ReferenceVerdict.PASS if passed else ReferenceVerdict.FAIL,
        detail=(
            f"{len(hits)}/{len(tokens)} signal tokens matched ({ratio:.0%}); "
            f"threshold={threshold:.0%}; missing={sorted(set(tokens)-set(hits))[:6]}"
        ),
    )


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_/+.-]{3,}")


# Common tokens that appear across the whole template and are therefore not
# scene-discriminating. Keeps us from counting "sonnet-4.7" or "sandbox:local"
# as evidence of any particular scene.
_GLOBAL_TOKENS: frozenset[str] = frozenset(
    {
        "sonnet-4.7",
        "think",
        "med",
        "dev",
        "compiler-rs",
        "parser",
        "parser-fix",
        "feat/parser-fix",
        "tasks:6",
        "agents:2",
        "sandbox:local",
        "Ctrl+Enter",
        "Shift+Enter",
        "Ctrl+R",
        "Ctrl+Shift+P",
        "working",
        "accept-edits",
        "send",
        "newline",
        "interrupt",
        "history",
        "palette",
        "focus",
    }
)


def _derive_signal_tokens(anchors: list[str]) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        for match in _TOKEN_RE.finditer(anchor):
            tok = match.group(0)
            if tok in _GLOBAL_TOKENS:
                continue
            if len(tok) > 40:
                continue
            if tok in seen:
                continue
            seen.add(tok)
            tokens.append(tok)
            if len(tokens) >= 16:
                return tokens
    return tokens


# ------------------------------------------------------------------ scene-specific

def _pred_scene_recovery_cards(text: str) -> ReferenceCheck:
    """Recovery scene (07) must show the six safe-option action cards."""
    expected_labels = (
        "retry", "inspect", "restore", "rewind", "compact", "planning",
    )
    lower = text.lower()
    found = [lbl for lbl in expected_labels if lbl in lower]
    # 4+ of 6 is a reasonable pass threshold — small wording drift is fine.
    passed = len(found) >= 4
    return ReferenceCheck(
        name="recovery_cards_visible",
        verdict=ReferenceVerdict.PASS if passed else ReferenceVerdict.FAIL,
        detail=f"matched {len(found)}/6 recovery action labels: {found}",
    )


def _pred_scene_narrow_layout(text: str, cols: int) -> ReferenceCheck:
    """Narrow scene (14) must render without overflowing the column budget."""
    lines = text.split("\n")
    max_line = max((len(line) for line in lines), default=0)
    passed = max_line <= cols + 2  # +2 slack for pyte cell alignment
    return ReferenceCheck(
        name="narrow_layout_fits",
        verdict=ReferenceVerdict.PASS if passed else ReferenceVerdict.FAIL,
        detail=f"widest rendered line = {max_line} cells (cols={cols})",
    )


_ACTIVE_TURN_MARKERS: tuple[str, ...] = ("working", "running", "streaming", "● ", "┃ ")


def _pred_scene_active_streaming(text: str) -> ReferenceCheck:
    """Active scene (02) must show evidence of an in-flight turn."""
    return _pred_tokens_in_strip(
        name="active_turn_indicator",
        strip=text,
        tokens=_ACTIVE_TURN_MARKERS,
        strip_label="the captured frame",
    )


def _pred_scene_overlay_header(text: str, *, expected: str) -> ReferenceCheck:
    return ReferenceCheck(
        name="overlay_header_visible",
        verdict=ReferenceVerdict.PASS if expected in text else ReferenceVerdict.FAIL,
        detail=(
            f"matched overlay header {expected!r}"
            if expected in text
            else f"missing overlay header {expected!r}"
        ),
    )


def _pred_scene_overlay_filter(text: str) -> ReferenceCheck:
    has_filter = "[filter:" in text.lower()
    return ReferenceCheck(
        name="overlay_filter_visible",
        verdict=ReferenceVerdict.PASS if has_filter else ReferenceVerdict.FAIL,
        detail=(
            "filter line visible"
            if has_filter
            else "no overlay filter line found"
        ),
    )


def _pred_scene_overlay_selection(text: str) -> ReferenceCheck:
    def _normalize_overlay_row(line: str) -> str:
        candidate = line.strip()
        while candidate[:1] in {"│", "┃", "|"}:
            candidate = candidate[1:].lstrip()
        return candidate

    selected = [
        _normalize_overlay_row(line)
        for line in text.split("\n")
        if _normalize_overlay_row(line).startswith("▶ ")
    ]
    return ReferenceCheck(
        name="overlay_selection_visible",
        verdict=ReferenceVerdict.PASS if selected else ReferenceVerdict.FAIL,
        detail=(
            f"selected row(s): {selected[:2]}"
            if selected
            else "no selected overlay row found"
        ),
    )


def _pred_scene_overlay_entries(
    text: str,
    *,
    expected_tokens: tuple[str, ...],
    minimum_hits: int = 1,
) -> ReferenceCheck:
    lower = text.lower()
    hits = [token for token in expected_tokens if token.lower() in lower]
    passed = len(hits) >= minimum_hits
    return ReferenceCheck(
        name="overlay_entries_visible",
        verdict=ReferenceVerdict.PASS if passed else ReferenceVerdict.FAIL,
        detail=(
            f"matched {len(hits)}/{len(expected_tokens)} entry token(s): {hits}"
            if passed
            else f"matched only {len(hits)}/{len(expected_tokens)} entry token(s): {hits}"
        ),
    )


def _pred_scene_signal_tokens(
    text: str,
    *,
    name: str,
    expected_tokens: tuple[str, ...],
    minimum_hits: int = 2,
) -> ReferenceCheck:
    lower = text.lower()
    hits = [token for token in expected_tokens if token.lower() in lower]
    passed = len(hits) >= minimum_hits
    return ReferenceCheck(
        name=name,
        verdict=ReferenceVerdict.PASS if passed else ReferenceVerdict.FAIL,
        detail=(
            f"matched {len(hits)}/{len(expected_tokens)} token(s): {hits}"
            if passed
            else f"matched only {len(hits)}/{len(expected_tokens)} token(s): {hits}"
        ),
    )


# ------------------------------------------------------------------ public API

def run_scene_predicates(
    text: str,
    scene: _SceneLike | dict[str, Any],
    *,
    cols: int,
) -> ReferenceReport:
    """Run all applicable predicates for the given scene against the live text.

    Stubbed scenes short-circuit to a single N/A check.
    """
    scene_d = _as_scene(scene)
    scene_id = str(scene_d["scene_id"])
    label = str(scene_d.get("label", ""))
    populated = bool(scene_d.get("populated", False))

    report = ReferenceReport(scene_id=scene_id, label=label)

    if not populated:
        report.checks.append(
            ReferenceCheck(
                name="scene_populated",
                verdict=ReferenceVerdict.NA,
                detail="scene is stubbed in manifest; predicates not run",
            )
        )
        return report

    # Structural predicates only — content-anchor matching is skipped
    # because the mockup's anchors contain demo-specific values (user
    # handle, branch name, timer) that no real session will reproduce.
    report.checks.append(_pred_hud_present(text))
    report.checks.append(_pred_composer_present(text))
    report.checks.append(_pred_keybind_footer_present(text))

    if scene_id == "recovery":
        report.checks.append(_pred_scene_recovery_cards(text))
    if scene_id == "narrow":
        report.checks.append(_pred_scene_narrow_layout(text, cols=cols))
    if scene_id == "active":
        report.checks.append(_pred_scene_active_streaming(text))
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="active_surface_tokens",
                expected_tokens=("Planning", "Read(src/utils/parser.ts)", "tests/parser.test.ts"),
            )
        )
    if scene_id == "ready":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="ready_surface_tokens",
                expected_tokens=("Restore", "recent session", "last branch activity"),
            )
        )
    if scene_id == "multi":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="multi_surface_tokens",
                expected_tokens=("jobs running", "[prioritized]", "[blocked: tests]"),
            )
        )
    if scene_id == "plan":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="plan_surface_tokens",
                expected_tokens=("Seven steps queued", "Run targeted parser tests", "VALIDATION"),
            )
        )
    if scene_id == "review":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="review_surface_tokens",
                expected_tokens=("REVIEW NEEDED", "src/utils/parser.ts", "[a]pprove"),
            )
        )
    if scene_id == "cc":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="cc_surface_tokens",
                expected_tokens=("Delegate", "SUBAGENTS", "matrix tests"),
            )
        )
    if scene_id == "sessions":
        report.checks.append(
            _pred_scene_overlay_header(text, expected="Select a session:")
        )
        report.checks.append(_pred_scene_overlay_filter(text))
        report.checks.append(_pred_scene_overlay_selection(text))
        report.checks.append(
            _pred_scene_overlay_entries(
                text,
                expected_tokens=("Mock session", "mock-session-001"),
                minimum_hits=1,
            )
        )
    if scene_id == "palette":
        report.checks.append(
            _pred_scene_overlay_header(text, expected="Command Palette")
        )
        report.checks.append(_pred_scene_overlay_filter(text))
        report.checks.append(_pred_scene_overlay_selection(text))
        report.checks.append(
            _pred_scene_overlay_entries(
                text,
                expected_tokens=("/help", "/model", "Show available commands"),
                minimum_hits=2,
            )
        )
    if scene_id == "restore":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="restore_surface_tokens",
                expected_tokens=("5 checkpoints", "extractImports guard", "diff from here"),
            )
        )
    if scene_id == "diff":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="diff_surface_tokens",
                expected_tokens=("files changed", "APPROVAL PATTERN", "src/utils/resolver.ts"),
            )
        )
    if scene_id == "grep":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="grep_surface_tokens",
                expected_tokens=("14 hits across 5 files", "@attach", "extractImports"),
            )
        )
    if scene_id == "escalation":
        report.checks.append(
            _pred_scene_signal_tokens(
                text,
                name="escalation_surface_tokens",
                expected_tokens=(
                    "Permission escalation",
                    ".github/workflows/ci.yml",
                    "Approve this edit only",
                ),
            )
        )

    rows = _nonempty_rows(text)
    report.checks.append(
        ReferenceCheck(
            name="nonempty_row_floor",
            verdict=(
                ReferenceVerdict.PASS
                if rows >= _CAPTURE_SANITY_ROW_FLOOR
                else ReferenceVerdict.FAIL
            ),
            detail=(
                f"{rows} non-empty rows rendered "
                f"(capture-sanity floor: {_CAPTURE_SANITY_ROW_FLOOR})"
            ),
        )
    )

    return report


# ------------------------------------------------------------------- manifest read

def load_scene_records(manifest_path: str | Any) -> list[dict[str, Any]]:
    """Parse the slim YAML manifest produced by ``extract_scenes.py``.

    Stdlib-only. This reader only understands the shape emitted by our
    writer: top-level scalars plus a ``scenes:`` list where each scene is
    a flat dict of scalars with two optional nested containers —
    ``anchors`` / ``region_classes`` (string lists) and ``class_counts``
    (map string→int).

    Nested containers appear either as an inline empty sentinel
    (``class_counts: {}`` / ``region_classes: []``) or as a bare heading
    followed by indented list items or ``key: value`` pairs. On a bare
    heading the reader peeks the next non-empty line to pick the shape,
    then consumes the block accordingly. A prior version unconditionally
    treated bare headings as empty lists and routed nested map entries
    onto the scene root; the lookahead fixes that.
    """
    path = Path(str(manifest_path))
    raw_lines = path.read_text(encoding="utf-8").splitlines()

    # Filter comments / blanks up front so lookahead is cheap.
    logical: list[tuple[int, str]] = []  # (indent, stripped)
    for raw in raw_lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        logical.append((indent, raw.strip()))

    def _strip_inline_comment(s: str) -> str:
        idx = s.find("  #")
        return s[:idx] if idx >= 0 else s

    def _parse_scalar(raw: str) -> Any:
        raw = _strip_inline_comment(raw).strip()
        if raw == "":
            return ""
        if raw.startswith('"') and raw.endswith('"'):
            return (
                raw[1:-1]
                .replace('\\"', '"')
                .replace("\\n", "\n")
                .replace("\\\\", "\\")
            )
        if raw in ("true", "false"):
            return raw == "true"
        if raw == "[]":
            return []
        if raw == "{}":
            return {}
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    def _peek_next(i: int) -> tuple[int, str] | None:
        if i + 1 < len(logical):
            return logical[i + 1]
        return None

    scenes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    i = 0
    while i < len(logical):
        indent, stripped = logical[i]

        # Top-level pre-amble (`version:`, `scene_count:`, `scenes:`) — skip.
        if indent == 0:
            i += 1
            continue

        # Scene record opens with `- scene_id: <id>`.
        if stripped.startswith("- scene_id:"):
            if current is not None:
                scenes.append(current)
            _, _, value = stripped.partition(":")
            current = {"scene_id": _parse_scalar(value)}
            i += 1
            continue

        if current is None:
            i += 1
            continue

        # Scene field.
        key, sep, rest = stripped.partition(":")
        if not sep:
            i += 1
            continue
        key = key.strip()
        rest_val = rest.strip()

        if rest_val != "":
            # Scalar (or inline empty sentinel like `[]` / `{}`).
            current[key] = _parse_scalar(rest_val)
            i += 1
            continue

        # Bare heading — decide list vs map vs empty via lookahead.
        peek = _peek_next(i)
        if peek is None or peek[0] <= indent:
            # No indented follow-up; assume empty list by convention.
            current[key] = []
            i += 1
            continue

        peek_indent, peek_stripped = peek
        if peek_stripped.startswith("- "):
            # Consume an indented list block.
            items: list[Any] = []
            j = i + 1
            while j < len(logical):
                j_indent, j_stripped = logical[j]
                if j_indent <= indent or not j_stripped.startswith("- "):
                    break
                items.append(_parse_scalar(j_stripped[2:]))
                j += 1
            current[key] = items
            i = j
            continue

        if ":" in peek_stripped:
            # Consume an indented map block.
            mapping: dict[str, Any] = {}
            j = i + 1
            while j < len(logical):
                j_indent, j_stripped = logical[j]
                if j_indent <= indent:
                    break
                if j_stripped.startswith("- "):
                    break  # list item at deeper indent — not our block
                sub_k, sub_sep, sub_v = j_stripped.partition(":")
                if not sub_sep:
                    break
                mapping[sub_k.strip()] = _parse_scalar(sub_v)
                j += 1
            current[key] = mapping
            i = j
            continue

        # Fallback — unknown shape; keep empty to avoid data corruption.
        current[key] = []
        i += 1

    if current is not None:
        scenes.append(current)

    # Normalize missing optional containers to their empty defaults so
    # callers can unconditionally `scene["class_counts"].get(...)` etc.
    for s in scenes:
        s.setdefault("anchors", [])
        s.setdefault("region_classes", [])
        s.setdefault("class_counts", {})
    return scenes


__all__ = [
    "ReferenceCheck",
    "ReferenceReport",
    "ReferenceVerdict",
    "load_scene_records",
    "run_scene_predicates",
]
