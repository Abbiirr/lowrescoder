# Manual QA Checklist — Phase 2D-E UI Bug Fixes

> Run `uv run hybridcoder chat` in Windows Terminal (or your platform's terminal).
> Ollama must be running with a model available.

## Prerequisites

- [ ] Windows Terminal (or iTerm2/Alacritty on macOS/Linux)
- [ ] Ollama running: `ollama serve`
- [ ] Model pulled: `ollama pull qwen3-8b` (or configured model)

---

## BUG-1: Separator Width

- [ ] Resize terminal to 80 columns — separator spans full width
- [ ] Resize terminal to 120 columns — separator spans full width
- [ ] Resize terminal to 200 columns — separator spans full width (no 120-char cap)
- [ ] Welcome banner separator matches terminal width
- [ ] After any separator, the next prompt starts on its own line (not appended like `──────❯`)

## BUG-2/7: Escape-to-Cancel

- [ ] Send a message, press Escape during "Thinking..." — see "Cancelled." message
- [ ] Send a message, press Escape during streaming — response stops, "Cancelled." printed
- [ ] Press Ctrl+C during streaming — generation cancels (message printed)
- [ ] After cancel, terminal is not left in raw mode (type normally)
- [ ] After cancel, next prompt works correctly

## BUG-2/7: Double Ctrl+C to Exit

- [ ] Press Ctrl+C once at idle — see "Press Ctrl+C again to quit" message
- [ ] Press Ctrl+C twice at idle — app exits with "Goodbye."
- [ ] Press Ctrl+D at idle — app exits with "Goodbye."

## BUG-4: Title Truncation

- [ ] Send a very long first message (100+ chars) as session title
- [ ] Run `/sessions` — titles are truncated with "..."
- [ ] Run `/resume` — titles are truncated with "..."
- [ ] No horizontal overflow in session listings

## BUG-5/6: Clean Prompt (No Borders)

- [ ] No `╭` or `╰` border characters visible around input
- [ ] Single green `❯` prompt character visible
- [ ] No empty ghost box between turns
- [ ] Clean visual flow: response → separator → prompt
- [ ] User input is visually separated from model output (separator printed immediately after the submitted `❯ ...` turn)

## BUG-8: Thinking Indicator

- [ ] "Thinking..." appears before every LLM response
- [ ] Inline mode: "Thinking..." stays in scrollback (no ANSI cursor tricks), and the response streams below it

## Slash Commands

- [ ] `/help` — lists all 14 commands
- [ ] `/model` — shows current model
- [ ] `/model <name>` — switches model
- [ ] `/mode` — shows current mode
- [ ] `/mode auto` — switches to auto mode
- [ ] `/shell on` / `/shell off` — toggles shell
- [ ] `/thinking` — toggles thinking visibility
- [ ] `/clear` — clears terminal screen
- [ ] `/copy` — copies last assistant message
- [ ] `/new` — starts new session
- [ ] `/sessions` — lists sessions
- [ ] `/compact` — compacts session (needs 5+ messages)
- [ ] `/freeze` — shows "not needed in inline mode"
- [ ] `/init` — creates .hybridcoder/memory.md
- [ ] `/exit` — exits app

## Edge Cases

- [ ] Press Escape at idle (no active generation) — no crash
- [ ] Rapid Escape presses during streaming — no crash, clean cancel
- [ ] Tab completion works after cancel
- [ ] Empty input (just Enter) — skipped, no error
- [ ] Whitespace-only input — skipped, no error

## Status Bar

- [ ] Bottom toolbar shows Model, Provider, Mode
- [ ] After agent response, Tokens count appears
- [ ] After file edit, Edits/Files count appears
- [ ] Shift+Tab cycles through modes (read-only → suggest → auto)
- [ ] Submitting input does not leave the editable prompt in scrollback (prompt is erased); the submitted turn still appears as `❯ ...`

---

## Test Results

| Tester | Date | Platform | Terminal | Issues Found |
|--------|------|----------|----------|-------------|
| | | | | |
