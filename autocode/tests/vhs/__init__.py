"""AutoCode TUI visual snapshot pipeline.

Despite the directory name, this uses ``pyte`` (pure-Python terminal
emulator) + ``Pillow`` (image rendering) instead of the upstream VHS tool,
because VHS requires ``ttyd`` which cannot be installed without root on this
host. The shape of the pipeline matches VHS semantically:

1. spawn the real ``autocode-tui`` binary in a PTY
2. replay a scripted keystroke sequence
3. feed the captured ANSI output into a ``pyte`` Screen
4. paint the Screen grid to a PNG via Pillow
5. optionally diff against a stored reference PNG
"""

from __future__ import annotations
