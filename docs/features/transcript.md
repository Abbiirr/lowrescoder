# Transcript

## Purpose

Defines the contract for visible message rendering, scroll behavior, search highlighting, and truncation rules in the TUI transcript region. The transcript is the primary content area between the status bar and the composer. All content is driven by typed events — never by parsing free-form text.

## User-visible TUI surfaces

- Scrollable transcript area occupying the full width between status bar and composer
- User messages rendered with distinct styling
- Assistant messages streamed token-by-token via `on_token`
- Thinking blocks rendered in a collapsible section when `/thinking` is enabled
- Tool-call entries with status indicators (spinner → done/failed)
- Search highlighting when transcript search is active
- Truncation markers when messages exceed display budget

## Backend contract

### Data flow

1. Backend emits `on_token` notifications with `text: string`
2. Frontend accumulates tokens into the current assistant message
3. Backend emits `on_done` to finalize the current turn
4. Historical messages are loaded via session storage on resume

### Rendering rules

- Full-screen render contract preserved: transcript fills available space
- No centered overlays for transcript content
- No hidden-while-streaming composer — composer remains visible at all times
- Scroll position auto-follows new content unless user has scrolled up (freeze mode)
- `/freeze` toggles auto-scroll lock

### Message schema (current)

```ts
interface TranscriptMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  toolCalls?: ToolCallEntry[];
}
```

## Event types

- `on_token` → appends text to current assistant message
- `on_thinking` → appends text to thinking section
- `on_tool_call` → adds/updates tool-call entry with status
- `on_done` → finalizes current turn, updates cost counters
- `on_error` → displays error inline in transcript

## State/reducer behavior

- Frontend maintains a `messages: Vec<TranscriptMessage>` in `AppState`
- New `on_token` text appends to the last assistant message's content
- `on_done` pushes the accumulated assistant message to persistent history
- Tool calls are tracked with status transitions: `pending` → `running` → `done`/`failed`/`cancelled`
- Scroll offset is frontend-local state, not backend-owned

## Persistence behavior

- Messages persisted as rows in SQLite session store
- On `session.resume`, messages are loaded from storage and rendered
- Adaptive truncation preserves high-signal content under display budget
- Episode retention creates deterministic summary rows before pruning

## Commands/keybindings

| Command | Keybinding | Action |
|---|---|---|
| `/freeze` (`/scroll-lock`) | — | Toggle auto-scroll |
| `/clear` (`/cls`) | — | Clear visible transcript |
| `/compact` | — | Compact session history |
| `/copy` (`/cp`) | — | Copy response text |
| `Up` (idle stage) | Scroll up | Navigate transcript history |
| `Down` (idle stage) | Scroll down | Navigate transcript history |
| `Ctrl+E` | — | Open editor for multiline input |
| `Ctrl+L` | — | Toggle detail surface |

## Failure/recovery behavior

- If streaming is interrupted, partial message is preserved in transcript
- If backend crashes mid-stream, frontend shows recovery banner (see `recovery.md`)
- If session storage is unavailable, transcript operates from in-memory state only

## Tests and fixtures

- Track 1 runtime invariants: `autocode/tests/tui-comparison/` — composer visible, no crash
- Track 4 PTY scenes: `ready`, `active` — transcript rendering validation
- Unit tests: `autocode/tests/unit/test_backend_chat.py` — streaming behavior
- PTY smoke: `autocode/tests/pty/` — real gateway streaming

## Acceptance criteria

- [ ] Transcript fills full screen between status bar and composer
- [ ] Streaming tokens append without flicker
- [ ] Scroll behavior respects freeze mode
- [ ] No centered overlay for transcript content
- [ ] Composer remains visible during streaming
- [ ] Search highlighting supported (planned)
- [ ] Truncation rules documented

## Open questions

- Exact truncation strategy: line count, character count, or token count budget?
- Should transcript search be incremental (type-to-search) or modal?
- How should very long tool outputs be collapsed — expandable sections or hard truncation?
- Should the transcript support inline image/rendering for non-text content?
