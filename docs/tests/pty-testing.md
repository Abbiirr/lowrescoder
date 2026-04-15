# PTY Testing Guide

Interactive terminal bugs regularly escape mocked unit tests. If a change affects terminal startup, key handling, rendering, streaming, scrollback, slash commands, or subprocess-backed chat flows, a real pseudo-terminal check should be part of validation whenever the agent can run one locally.

## When To Use PTY Tests

Run a PTY-backed check when you touch any of these:
- Go Bubble Tea TUI startup, rendering, keyboard handling, palette behavior, queueing, streaming, status bar, or backend wiring
- Python inline chat or Textual TUI behavior that depends on real terminal input/output
- ANSI rendering, scrollback, alternate-screen behavior, cursor movement, or terminal resize handling
- Any bug report that came from a screenshot, transcript, or "it looks wrong in the terminal" feedback

Unit tests are still required. PTY checks are the runtime complement, not a replacement.

## What PTY Testing Catches

PTY runs are useful for bugs that mocks miss:
- stderr warnings rendered as fatal UI errors
- startup hangs while waiting for terminal queries or backend handshakes
- key chords that echo literally instead of being intercepted
- view corruption caused by concurrent printing and live rendering
- regressions that only appear with a real TTY, real terminal size, or real subprocess pipes

## Minimum Expectation

If the environment supports it, do at least one real PTY validation for interactive changes:
1. Start the real entrypoint inside a PTY.
2. Send the smallest input that exercises the changed path.
3. Assert on visible terminal behavior, not just internal state.
4. Save the transcript or script output under `docs/qa/test-results/`.

If PTY validation is not possible, say why in your final report.

## Manual PTY Smoke Check

For a quick human-driven transcript capture:

```bash
script -q /tmp/autocode-pty.typescript
uv run autocode chat
exit
```

Then copy or summarize the relevant transcript into `docs/qa/test-results/`.

This is good for confirming:
- startup prompt appears
- slash commands visibly respond
- the app exits cleanly
- no obvious tracebacks, panics, or malformed redraws appear

## Scripted PTY Harness Pattern

Use Python's standard library so the harness stays cheap and portable.

```python
import errno
import fcntl
import os
import pty
import select
import struct
import termios
import time


def set_winsize(fd: int, rows: int = 50, cols: int = 160) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def spawn(argv: list[str]) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    set_winsize(master_fd)
    set_winsize(slave_fd)
    pid = os.fork()
    if pid == 0:
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        for fd in (0, 1, 2):
            os.dup2(slave_fd, fd)
        os.execvp(argv[0], argv)
    os.close(slave_fd)
    return master_fd, pid


def read_until_quiet(fd: int, quiet: float = 1.0, maxwait: float = 10.0) -> bytes:
    buf = b""
    deadline = time.monotonic() + maxwait
    last = time.monotonic()
    while time.monotonic() < deadline:
        timeout = max(0.05, min(quiet, deadline - time.monotonic()))
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            if time.monotonic() - last >= quiet:
                break
            continue
        try:
            chunk = os.read(fd, 8192)
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last = time.monotonic()
    return buf
```

Keep the first automated scenario minimal:
- spawn app
- wait for startup prompt or header
- send one input
- assert the expected visible string is present
- assert obvious failure strings are absent

## Recommended Assertions

Every PTY script should check for:
- expected startup marker such as `AutoCode`, `❯`, or another stable prompt string
- the specific visible outcome for the feature under test
- absence of `panic:`, `Traceback`, and obviously wrong fallback UI

For chat/TUI flows, also check for:
- unexpected model or provider pickers
- queue/debug text leaking into the chat stream
- old spinner or placeholder text appearing after a refactor
- commands returning nothing when they should visibly respond

## Good Scope

A good PTY test is narrow:
- one startup test
- one focused reproduction for the changed behavior
- one explicit regression assertion for the bad output you are preventing

Avoid trying to automate every possible terminal interaction in one script. If the script becomes a mini end-to-end framework, it will rot.

## Suggested Workflow

1. Add or update ordinary unit tests first.
2. Reproduce the interactive path in a PTY.
3. Fix the bug.
4. Re-run the focused PTY scenario.
5. Store the transcript or harness output in `docs/qa/test-results/`.

## Reporting

When you used PTY validation, report:
- which entrypoint you ran
- whether it was manual or scripted
- the exact command
- the artifact path with the transcript or captured output
- what behavior the PTY check proved

That keeps "tested interactively" from turning into an unverifiable claim.
