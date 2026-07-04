"""Marker-based shell command sync helpers for external harness adapters."""

from __future__ import annotations

import re
import uuid

_MARKER_RE_TEMPLATE = r"(?m)^__AUTOCODE_SYNC__:{marker}:(-?\d+)\s*$"


def new_command_marker() -> str:
    """Create a unique marker for one command execution."""
    return uuid.uuid4().hex


def build_marker_wrapped_command(command: str, marker: str) -> str:
    """Wrap a shell command so it emits a unique completion marker."""
    return (
        f"({command}); "
        "__autocode_status=$?; "
        f"printf '\\n__AUTOCODE_SYNC__:{marker}:%s\\n' \"$__autocode_status\"; "
        'exit "$__autocode_status"'
    )


def strip_marker_output(output: str, marker: str) -> tuple[str, int | None]:
    """Strip the completion marker from command output and return its status."""
    if not output:
        return "", None

    marker_re = re.compile(_MARKER_RE_TEMPLATE.format(marker=re.escape(marker)))
    matches = list(marker_re.finditer(output))
    if not matches:
        return output.rstrip(), None

    match = matches[-1]
    cleaned = (output[:match.start()] + output[match.end():]).rstrip()
    return cleaned, int(match.group(1))
