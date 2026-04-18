# PTY TUI Bug Report

**Date:** 2026-04-13  
**Tester:** PTY automated (pty_tui_bugfind.py)  
**Go TUI binary:** `/home/bs01763/projects/ai/lowrescoder/autocode/build/autocode-tui`  
**Python chat:** `/home/bs01763/.local/bin/autocode chat`  

## Summary

1 bugs found.

| # | Severity | Label | Detail |
|---|---------|-------|--------|
| 1 | MEDIUM | B7_todo_write: old 'Thinking…' spinner text still present (verb rotation not applied) | 
  ↳ queued (1 pending): use todo_write to plan: step 1, step 2
 · queue: 1⠙  |

## Full Findings Log

```
======================================================================
AutoCode PTY Bug Finder — Full Suite
Go TUI: /home/bs01763/projects/ai/lowrescoder/autocode/build/autocode-tui
Python: /home/bs01763/.local/bin/autocode chat
Terminal size: 160x50
======================================================================

══════════════════════════════════════════════════════════════════════
SUITE A — Go TUI (autocode-tui)
══════════════════════════════════════════════════════════════════════

[A1] Startup render — wait up to 10s for AutoCode header
  ✓ A1_startup — header appeared

[A2] Ctrl+K command palette
  ✓ A2_ctrl_k — palette opened

[A3] /model picker
  ✓ A3_model_picker — picker opened as expected

[A4] /diff command
  ✓ A4_diff — got diff content (3296 bytes)

[A5] /cost command
  ✓ A5_cost — usage info returned

[A6] /undo command
  ✓ A6_undo — undo responded appropriately

[A7] /export command
  ✓ A7_export — export confirmed

[A8] /help command
  ✓ A8_help — help responded

[A9] Slash completion (type '/')
  ✓ A9_slash_completion — completions appeared

[A10] Rapid empty Enter presses (should not crash)
  ✓ A10_rapid_enter — no crash on rapid empty enter

[A11] Ctrl+C interrupt during idle
  ✓ A11_ctrl_c — no crash (798 bytes)

[A12] Very long input (500 chars)
  ✓ A12_long_input — no crash on 500-char input

[A13] Arrow keys in idle state
  ✓ A13_arrow_keys — no unexpected picker on arrow keys

[A14] /model picker — type to filter, then Escape
  ✓ A14_model_filter — filter header visible in model picker

══════════════════════════════════════════════════════════════════════
SUITE B — Python inline chat (autocode chat)
══════════════════════════════════════════════════════════════════════

[B1] Startup — wait for prompt
  ✓ B1_startup — started (1061 bytes)

[B2] /cost in Python inline
  ✓ B2_cost_py — usage returned

[B3] /diff in Python inline
  ✓ B3_diff_py — diff output returned

[B4] /undo in Python inline
  ✓ B4_undo_py — undo responded

[B5] /model in Python inline
  ✓ B5_model_py — model responded

[B6] @file mention expansion
  ✓ B6_file_expansion — @file expanded into message

[B7] todo_write tool registration check

  ❌ [MEDIUM] B7_todo_write: old 'Thinking…' spinner text still present (verb rotation not applied)
     
  ↳ queued (1 pending): use todo_write to plan: step 1, step 2
 · queue: 1⠙ ⠹ ⠸ ⠼ Think⠴ ⠦ ⠧ ⠇ ⠏ Thinking… (13⠋ ⠙ ⠹ Shipp⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏ ⠋ Reinventing… (13s)⠙ Reinventing… (14⠹ 
  ✓ B7_todo_write — todo_write appears to be wired

[B8] RulesLoader — rules injected at session start?
  ✓ B8_rules_loader — model knows CLAUDE.md invariants — RulesLoader active

══════════════════════════════════════════════════════════════════════
DONE — 1 bugs found
══════════════════════════════════════════════════════════════════════

  MEDIUM (1)
    • B7_todo_write: old 'Thinking…' spinner text still present (verb rotation not applied)
      
  ↳ queued (1 pending): use todo_write to plan: step 1, step 2
 · queue: 1⠙ ⠹ ⠸ ⠼ Think⠴ ⠦ ⠧ ⠇ ⠏ Thinking… (
```
