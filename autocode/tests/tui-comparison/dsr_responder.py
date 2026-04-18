"""Minimal DSR (Device Status Report) responder shim.

Some TUIs (notably codex) send terminal-query escape sequences on startup
and wait for responses before rendering. A raw PTY master doesn't answer
those queries, so the child hangs. This shim watches captured bytes for
known queries and writes minimal valid responses back through the PTY.

**Intentionally not a full terminal emulator.** We only handle 4 queries:

1. ``ESC[6n``       — DSR cursor position  → reply ``ESC[{row};{col}R``
2. ``ESC[c``        — Primary DA           → reply ``ESC[?62c`` (VT520)
3. ``ESC[?u``       — kitty keyboard flags → reply ``ESC[?0u`` (disabled)
4. ``OSC 10;?``     — foreground color    → reply ``OSC 10;rgb:ff/ff/ff ST``

If a scenario needs something else, add it here — don't try to ship a
pyte-backed pseudo-emulator.

Every response written is logged on the returned ``DsrResponder`` so
the capture run can persist what was faked into ``profile.yaml::dsr_responses_served``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import ClassVar

SHIM_VERSION = "1"

# Pattern → (label, response_factory) — the factory takes (match, row, col) and returns bytes
_DSR_CURSOR_POSITION = re.compile(rb"\x1b\[6n")
_DSR_PRIMARY_DA = re.compile(rb"\x1b\[c")
_DSR_KITTY_KEYBOARD = re.compile(rb"\x1b\[\?u")
_DSR_OSC_FG = re.compile(rb"\x1b\]10;\?\x1b\\")  # OSC 10 ; ? ST
_DSR_OSC_FG_BEL = re.compile(rb"\x1b\]10;\?\x07")  # OSC 10 ; ? BEL (alt terminator)


@dataclass
class DsrResponder:
    """Scan a byte stream for DSR queries and write minimal responses.

    Construct once per capture, feed every read() chunk into ``process()``
    (which returns the chunk unchanged for further consumption), and it
    writes responses back to ``pty_fd`` as side effects. Summary lives
    on ``served``.
    """

    pty_fd: int
    cursor_row: int = 1
    cursor_col: int = 1

    # Log of what we served — drives profile.yaml::dsr_responses_served
    served: list[str] = field(default_factory=list)

    shim_version: ClassVar[str] = SHIM_VERSION

    def process(self, chunk: bytes) -> bytes:
        """Return ``chunk`` unchanged; dispatch DSR replies as side effect.

        Safe to call with partial chunks — any query straddling a chunk
        boundary will just be missed on one pass and picked up on the
        next (the child will resend after its own timeout or proceed
        without).
        """
        if _DSR_CURSOR_POSITION.search(chunk):
            self._write_back(
                f"\x1b[{self.cursor_row};{self.cursor_col}R".encode("ascii"),
                "cursor_position",
            )
        if _DSR_PRIMARY_DA.search(chunk):
            # VT520 primary device attributes — minimal modern terminal
            self._write_back(b"\x1b[?62c", "primary_da_vt520")
        if _DSR_KITTY_KEYBOARD.search(chunk):
            # Kitty keyboard protocol disabled (0 flags)
            self._write_back(b"\x1b[?0u", "kitty_keyboard_disabled")
        if _DSR_OSC_FG.search(chunk) or _DSR_OSC_FG_BEL.search(chunk):
            # Neutral white foreground
            self._write_back(b"\x1b]10;rgb:ff/ff/ff\x1b\\", "osc10_fg_white")
        return chunk

    def _write_back(self, data: bytes, label: str) -> None:
        try:
            os.write(self.pty_fd, data)
            self.served.append(label)
        except OSError:
            # PTY closed underneath us; nothing to do
            pass


def summary_for_profile(responder: DsrResponder) -> dict:
    """Serialize responder state for profile.yaml."""
    return {
        "shim_version": DsrResponder.shim_version,
        "responses_served": responder.served,
    }
