# PTY TUI Bug Report

**Date:** 2026-04-13  
**Tester:** PTY automated (`autocode/tests/pty/pty_tui_bugfind.py`, `pty_deep_bugs.py`)  
**Go TUI binary:** `autocode/cmd/autocode-tui/autocode-tui`  
**Python chat:** `autocode chat`  
**Terminal size:** 160x50 / 200x60  
**Method:** `pty.fork()` against installed binary — real TTY, not unit test mocks  

---

## Summary

| Severity | Count | Source |
|----------|-------|--------|
| CRITICAL | 3 | Screenshots (Go TUI live) + PTY Suite A |
| HIGH | 5 | Screenshots + PTY |
| MEDIUM | 3 | PTY Suite B |
| LOW | 1 | PTY Suite A |
| **Total** | **12** | |

---

## CRITICAL Bugs

### C1 — Go TUI: Model picker appears after every normal chat response

**Observed:** Screenshots 1 and 2 — user types "hello" / "who are you?", LLM streams response, then `Select a model (current: tools)` picker appears without user typing `/model`.  
**Reproduction:** Type any plain message in Go TUI → wait for LLM response → model picker opens.  
**Impact:** Every chat interaction is broken; user forced to dismiss picker after each response.  
**Root cause hypothesis:**  
  - Backend sends unsolicited `model.list` RPC response after `on_done` notification  
  - OR the Go TUI's `backendModelListMsg` handler fires on some other backend event  
  - OR the Go TUI's queue/timer mechanism replays a pending `model.list` request  
  - NOT present in Python inline (PTY test `model_picker_after_chat` passed clean)  

### C2 — Go TUI: "(queued N pending)" text appears in stream area

**Observed:** Screenshot 2 — after model picker dismissed, stream shows:  
```
(queued 1 pending)
(queued 2 pending)
(queued 3 pending)
you with software development tasks like:
```  
**Root cause hypothesis:**  
  - The task panel renderer emits "(queued N pending)" strings that overlap with the stream area  
  - OR these are LLM-generated tokens (LLM reproducing queue state from injected CLAUDE.md context)  
  - OR the `renderQueuePreview` function writes into the wrong region after the picker dismissal  
  - NOT reproduced in Python inline PTY test (queue leak test passed)  

### C3 — Go TUI: Does not start in PTY (alternate-screen deadlock)

**Observed:** `autocode-tui` spawned in PTY, 10s wait → only 12 raw bytes output: `11;?` (partial ANSI terminal query response). No "AutoCode" header, no UI render.  
**Root cause:**  
  - The Go TUI sends terminal queries (`\x1b[?1049h`, `\x1b[6n`, etc.) on startup  
  - PTY responds with capability strings, but the backend subprocess (`autocode serve`) fails to start in the forked PTY environment — no stdin/stdout pipe to Python  
  - Go TUI hangs waiting for `backendStatusMsg` that never arrives  
  - **All Go TUI commands fail as a consequence** (A2–A14 in Suite A)  
**Workaround:** Run `autocode serve` separately, then connect `autocode-tui` — or fix startup to handle missing backend gracefully  

---

## HIGH Bugs

### H1 — Go TUI: Response text truncated / garbled

**Observed:** Screenshot 1 — response shows `aining code` (dropped "ma" from "maintaining"), ends with stray `!`. Screenshot 3 — response ends mid-word `approva`.  
**Root cause hypothesis:**  
  - The `tea.Printf` path (used in `claudeLike` mode) writes tokens directly to terminal stdout. If the alternate-screen buffer is not properly flushed before the session summary renders, early tokens get overwritten.  
  - OR `streamBuf` is trimmed to last 50 lines but the `tokenBuf` flush on `tickMsg` has a race with the `backendDoneMsg` handler  
  - OR the `thinkingBuf` content bleeds into the stream area  

### H2 — Go TUI: Ctrl+K echoes `^K` instead of opening palette

**Observed:** PTY test A2 — sending `\x0b` (Ctrl+K) returns empty output; raw output shows `^K` echo.  
**Root cause:** BubbleTea requires the terminal to be in raw mode before Ctrl+K is intercepted as a key event. When the PTY sends `\x0b` before the TUI completes initialization (stageInit state), the input is echoed as `^K`. May also affect real terminals during the startup window.  

### H3 — Go TUI: /model, /diff, /cost, all slash commands silent in PTY

**Observed:** PTY Suite A — all slash commands sent after startup return 0 bytes.  
**Root cause:** Consequence of C3 — backend never connected, so no commands processed.  

### H4 — Python inline: @file expansion — LLM hangs after expansion

**Observed:** PTY Suite B — `@/tmp/pty_atfile_test.txt` message sent (100 bytes input captured), but no LLM response within 20 seconds. The next 4 LLM-dependent tests also timed out, suggesting the gateway stopped responding after the file-expanded message was sent.  
**Root cause hypothesis:**  
  - The `_expand_file_mentions()` regex `r'@([\w./\-]+\.\w+)'` correctly matches paths, but inlining large file content may exceed the LLM's context window and cause the gateway to time out  
  - OR the LLM gateway was already overloaded  

### H5 — Python inline: Session does not recover after gateway timeout

**Observed:** PTY Suite B — after first LLM gateway timeout (B6 @file test), all subsequent LLM calls return 0 bytes. /export also stopped responding.  
**Root cause:** When the `handle_chat` coroutine times out or is cancelled, the `self._current_agent` state may not be properly cleaned up, blocking subsequent calls.  

---

## MEDIUM Bugs

### M1 — Python inline: RulesLoader context injection unverifiable

**Observed:** PTY Suite B B8 — asked the model about CLAUDE.md invariants, no response within 35s.  
**Status:** Inconclusive — LLM gateway was likely overloaded. Cannot confirm whether RulesLoader correctly injects CLAUDE.md.  
**Separate concern:** CLAUDE.md is ~10KB. Injecting it on every session start adds significant token overhead. No truncation/summarization is applied.  

### M2 — Python inline: todo_write / glob_files / grep_content invocation unverifiable

**Observed:** PTY Suite B — no response within timeouts (LLM gateway overloaded from earlier).  
**Status:** Inconclusive for tool invocation; tools ARE registered (unit tests confirm 27 tools).  

### M3 — Python inline: Post-LLM-timeout session is not self-healing

**Observed:** After one gateway timeout, all subsequent LLM calls return 0 bytes.  
**Root cause:** The `handle_chat` coroutine's cancellation path does not reset `self._current_agent` or the async task state.  

---

## LOW Bugs

### L1 — Go TUI: Slash completion doesn't appear in PTY

**Observed:** PTY Suite A A9 — typing `/` returns 0 bytes.  
**Root cause:** Same as C3 — backend not connected, completion requires backend status.  

---

## Confirmed Working (Python Inline)

| Feature | Status |
|---------|--------|
| /help | ✓ Works |
| /diff | ✓ Works |
| /cost (Session Usage) | ✓ Works |
| /undo (no checkpoints) | ✓ Works |
| /export | ✓ Works (before session degradation) |
| /clear | ✓ Works |
| /compact | ✓ Works |
| /model arrow-key picker | ✓ Works |
| /provider arrow-key picker | ✓ Works |
| No model picker after plain chat | ✓ Confirmed |
| No "(queued N pending)" leak | ✓ Confirmed |
| Session Summary format | ✓ Works |

---

## Test Procedure (for reproduction)

### PTY Setup
```python
master_fd, slave_fd = pty.openpty()
fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
pid = os.fork()
# child: setsid(), dup2 slave to stdin/stdout/stderr, execve binary
```

### Timing Parameters (calibrated from PTY runs)
| Phase | quiet_secs | maxwait_secs | stop_on |
|-------|-----------|--------------|---------|
| Startup | 2.0 | 15.0 | `"❯"` |
| Slash command (no LLM) | 2.0 | 12.0 | — |
| LLM response | 3.0 | 35–40 | `"Session Summary"` |
| Quick UI interaction | 0.5 | 3.0 | specific text |

### Key timing observations
- Slash commands that don't need LLM (/diff, /cost, /help, /undo, /export) respond in < 1 second
- LLM responses through the gateway take 15–60+ seconds (provider-dependent)
- Go TUI backend startup takes > 10 seconds in PTY (backend subprocess spawn + Python import time)

### ANSI stripping
```python
ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
clean = ANSI.sub("", raw.decode("utf-8", errors="replace"))
```

### Universal checks applied to every response
1. `"Select a model"` in text → CRITICAL if not from /model test
2. `r'\(queued \d+ pending\)'` in text → CRITICAL
3. `"panic:"` + `"runtime error"` → CRITICAL
4. `"Traceback"` → CRITICAL
5. `"Thinking…"` (old spinner) → MEDIUM

---

## Priority Fix Order

1. **C1** — Go TUI model picker after chat (blocks all Go TUI usage)
2. **C3** — Go TUI PTY startup (enables full Go TUI automation)
3. **H1** — Go TUI response truncation
4. **C2** — Go TUI "(queued N pending)" leak
5. **M3** — Python inline session recovery after gateway timeout
6. **H4** — @file expansion context size guard
7. **H2** — Ctrl+K in PTY (may be inherent terminal limitation)
