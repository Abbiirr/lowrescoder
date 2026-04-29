# Composer

## Purpose

Defines the contract for the boxed composer input area at the bottom of the TUI. The composer is always visible (never hidden during streaming), fixed-allocation at the bottom of the screen, and supports single-line and multi-line editing, history navigation, and fake-cursor behavior when unfocused.

## User-visible TUI surfaces

- Fixed-height boxed input area at the bottom of the screen
- Single-line editing with cursor movement (Left, Right, Home, End)
- Multi-line expansion via `Alt+Enter` (queues draft) or `Ctrl+E` (editor mode)
- History navigation with frecency ranking (Up/Down arrows when stage is Idle)
- Slash-autocomplete dropdown when input starts with `/`
- Fake cursor (dimmed or static) when the window is unfocused
- Real-cursor restoration on window refocus or crash recovery

## Backend contract

The composer is frontend-local state. The backend does not own composer text. The backend receives the final submitted text via the `chat` RPC method:

```ts
interface ChatParams {
  message: string;
  session_id?: string;
}
```

### `preservedDraft` semantics

The composer buffer must survive:
- Backend halt or error (the text is preserved in `RecoveryState.preservedDraft`)
- Window unfocus/blur (text stays in the composer)
- Recovery from a stale request (text is restored from preserved state)

This is a non-negotiable requirement. The user never loses in-progress composer text.

## Event types

No backend events drive the composer directly. The composer emits:
- `chat` request on `Enter` (when not in multi-line mode)
- `command` request on `Enter` when text starts with `/`

## State/reducer behavior

- `Composer` struct in `autocode/rtui/src/ui/composer.rs` owns the buffer
- Key handling:
  - `Enter` (no modifier): submit or insert newline based on mode
  - `Alt+Enter`: queue current draft (see `queue.md`)
  - `Ctrl+U`: clear current line
  - `Backspace`/`Delete`: delete character
  - `Left`/`Right`: move cursor
  - `Home`/`End`: jump to start/end
  - Regular chars: insert at cursor position
- On submit: buffer is sent to backend, then cleared
- On error: buffer content is saved to `preservedDraft` before clearing

## Persistence behavior

- History persisted to `~/.autocode/history.json` with frecency ranking
- Composer buffer is **not** persisted to disk during typing (in-memory only)
- On recovery: `preservedDraft` is restored from the recovery state

## Commands/keybindings

| Key | Action |
|---|---|
| `Enter` | Submit message (single-line) or insert newline (multi-line) |
| `Alt+Enter` | Queue current draft |
| `Ctrl+E` | Open external editor for multi-line input |
| `Ctrl+U` | Clear current input line |
| `Ctrl+C` (single) | Cancel current streaming turn |
| `Ctrl+C` (double) | Exit application |
| `Ctrl+K` | Open command palette |
| `Up` (Idle stage) | Navigate history backward |
| `Down` (Idle stage) | Navigate history forward |
| `/` (start of input) | Trigger slash autocomplete |

## Failure/recovery behavior

- If the backend crashes while the user has text in the composer, the text must be preserved in `RecoveryState.preservedDraft`
- On recovery, the composer is pre-filled with the preserved draft
- If the composer cannot submit (e.g., no backend connection), the text stays in the buffer
- Fake cursor is shown when terminal window loses focus; real cursor restored on focus

## Tests and fixtures

- Composer unit tests in `autocode/rtui/src/ui/composer.rs`
- Reducer key-handling tests in `autocode/rtui/src/state/reducer.rs`
- History persistence: `~/.autocode/history.json` frecency tests
- PTY smoke: composer visibility during streaming scenarios
- Track 4: `ready` scene validates composer presence

## Acceptance criteria

- [ ] Composer always visible at bottom of screen (never hidden during streaming)
- [ ] Fixed-allocation height (does not grow unbounded)
- [ ] `preservedDraft` semantics: text survives halt/error/recovery
- [ ] Fake cursor when unfocused, real cursor on refocus
- [ ] History navigation with frecency ranking works
- [ ] Slash-autocomplete triggered on `/` prefix
- [ ] Multi-line editing via `Ctrl+E` editor launch

## Open questions

- Should the composer height be configurable or fixed at 3 rows?
- What is the maximum composer buffer size before truncation?
- Should bracketed paste be supported for large pastes?
- Should the composer support drag-and-drop file paths (terminal-dependent)?
