#!/usr/bin/env python3
"""Silent mock backend for orphaned-startup PTY regression tests.

Simulates an unreachable Python backend: the process stays alive and
reads stdin, but never writes JSON-RPC over stdout. The TUI's startup
timeout (15s) should then fire and surface a user-visible error about
the backend being unreachable.

Usage: set AUTOCODE_PYTHON_CMD to this script.
"""
from __future__ import annotations

import sys
import time


def main() -> None:
    # Optional stderr note so operator-level tools can distinguish this
    # from a crashed backend. The TUI suppresses `INFO:` severity so this
    # line does not clutter the captured frame.
    print("INFO: silent backend started — intentionally no on_status", file=sys.stderr, flush=True)

    # Read stdin forever; never respond.
    for _line in sys.stdin:
        # Discard.
        pass

    # If stdin ever closes, hang so the TUI teardown is observable.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
