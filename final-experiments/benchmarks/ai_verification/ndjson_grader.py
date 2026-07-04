"""NDJSON grader for AI verification harness.

Deterministic exit-code checker using pytest-compatible assertions over
the NDJSON event stream.  Supports ``must_have`` and ``must_not_have``
predicate strings.

Predicate language (intentionally minimal):
  - ``"<event_type> event present"`` — passes if any event has that type
  - ``"<event_type> event with <field>"`` — passes if any event has that type
    AND the named field is present (non-empty for strings, non-zero for ints)
  - ``"item_started with kind=<value>"`` — passes if any item_started event
    has ``kind`` equal to the given value
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class GraderResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def grade_ndjson(
    raw_lines: list[str],
    must_have: list[str],
    must_not_have: list[str],
) -> GraderResult:
    events = _parse_raw_events(raw_lines)
    failures: list[str] = []
    warnings: list[str] = []

    for predicate in must_have:
        warning = _malformed_predicate_warning(predicate)
        if warning is not None:
            warnings.append(warning)
        if not _check_predicate(events, predicate, expect_present=True):
            failures.append(f"must_have FAILED: {predicate}")

    for predicate in must_not_have:
        warning = _malformed_predicate_warning(predicate)
        if warning is not None:
            warnings.append(warning)
        if not _check_predicate(events, predicate, expect_present=False):
            failures.append(f"must_not_have FAILED: {predicate}")

    return GraderResult(
        passed=len(failures) == 0,
        failures=failures,
        warnings=warnings,
    )


def _parse_raw_events(raw_lines: list[str]) -> list[dict]:
    events = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return events


def _check_predicate(events: list[dict], predicate: str, *, expect_present: bool) -> bool:
    event_type = _extract_event_type(predicate)
    kind_value = _extract_kind_value(predicate)
    field_name = _extract_field_name(predicate)
    result_contains = _extract_result_contains(predicate)
    cache_ratio_threshold = _extract_cache_hit_ratio_threshold(predicate)

    matched = False
    for event in events:
        if event.get("type") != event_type:
            continue
        if kind_value is not None and event.get("kind") != kind_value:
            continue
        if field_name is not None:
            val = event.get(field_name)
            if val is None:
                continue
            if isinstance(val, (int, float)) and val == 0:
                continue
            if isinstance(val, str) and not val:
                continue
            if isinstance(val, dict) and not val:
                continue
        if result_contains is not None and result_contains not in str(event.get("result", "")):
            continue
        if cache_ratio_threshold is not None:
            if not _event_meets_cache_hit_ratio(event, cache_ratio_threshold):
                continue
        matched = True
        break

    return matched if expect_present else not matched


def _extract_event_type(predicate: str) -> str:
    lower = predicate.lower().strip()
    for suffix in (" event present", " event with ", " event"):
        idx = lower.find(suffix)
        if idx > 0:
            return lower[:idx]
    parts = lower.split()
    if parts:
        return parts[0]
    return ""


def _extract_kind_value(predicate: str) -> str | None:
    lower = predicate.lower()
    if "kind=" in lower:
        idx = lower.index("kind=")
        rest = lower[idx + 5:]
        end = rest.find(" ")
        return rest[:end] if end > 0 else rest
    return None


def _extract_field_name(predicate: str) -> str | None:
    lower = predicate.lower()
    if " with usage" in lower:
        return "usage"
    if " event with " in lower:
        idx = lower.index(" event with ")
        rest = lower[idx + 12:]
        end = rest.find(" ")
        return rest[:end] if end > 0 else rest
    return None


def _extract_result_contains(predicate: str) -> str | None:
    marker = " result contains "
    if marker not in predicate:
        return None
    return predicate.split(marker, maxsplit=1)[1]


def _extract_cache_hit_ratio_threshold(predicate: str) -> float | None:
    lower = predicate.lower()
    marker = "cache_hit_ratio>="
    if marker not in lower:
        return None
    parts = lower.split(marker, maxsplit=1)[1].split()
    if not parts:
        return float("inf")
    raw = parts[0]
    try:
        return float(raw)
    except ValueError:
        return float("inf")


def _malformed_predicate_warning(predicate: str) -> str | None:
    lower = predicate.lower()
    marker = "cache_hit_ratio>="
    if marker not in lower:
        return None
    parts = lower.split(marker, maxsplit=1)[1].split()
    if not parts:
        return f"WARN: malformed predicate {predicate!r}"
    try:
        float(parts[0])
    except ValueError:
        return f"WARN: malformed predicate {predicate!r}"
    return None


def _event_meets_cache_hit_ratio(event: dict, threshold: float) -> bool:
    usage = event.get("usage")
    if not isinstance(usage, dict):
        return False
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    cached_tokens = usage.get("cached_input_tokens", 0)
    try:
        input_count = int(input_tokens)
        cached_count = int(cached_tokens)
    except (TypeError, ValueError):
        return False
    if input_count <= 0:
        return False
    return (cached_count / input_count) >= threshold
