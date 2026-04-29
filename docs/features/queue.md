# Queue

## Purpose

Defines the contract for the follow-up queue system. The queue allows users to stack drafts while the agent is actively processing, enabling a "work ahead" pattern. The queue is a bottom drawer (not an overlay), collapsed to one row when inactive.

## User-visible TUI surfaces

- Collapsed queue strip: one row above the composer showing queued item count
- Expanded queue: bottom drawer pushing the composer up, showing all queued items
- Each queue item shows: position, text preview, state badge (draft/queued/blocked)
- Editable items in the queue until they are submitted
- Submitted items become read-only transcript entries

## Backend contract

### Typed model

```ts
type QueueItemState =
  | "draft"
  | "queued"
  | "next"
  | "blocked"
  | "prioritized"
  | "submitted"
  | "cancelled";

interface QueueItem {
  id: string;
  sessionId: string;
  text: string;
  state: QueueItemState;
  blockedReason?: string;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
  editableUntilSubmitted: boolean;
}
```

### Queue behavior

- `Alt+Enter` queues the current composer draft
- Queued drafts remain editable until submitted
- Submitted queue items become transcript entries and are read-only
- **Collapsed queue = 1 row** showing count
- **Expanded queue = bottom drawer, NOT an overlay** (no centered modal, no dimmed backdrop)

### State transitions

```
draft → queued → next → submitted (becomes transcript entry)
                 ↗
queued → prioritized → next → submitted
queued → blocked → queued (when blocker resolves)
draft/queued → cancelled
```

## Event types

- `QueueEvent` (planned): emitted on queue state changes
  - `queue_item_added`: new item queued
  - `queue_item_updated`: item text or state changed
  - `queue_item_submitted`: item submitted as chat turn
  - `queue_item_cancelled`: item removed from queue

## State/reducer behavior

- Frontend maintains a `Vec<QueueItem>` in local state
- On `Alt+Enter`: current composer text becomes a new `QueueItem` with state `queued`; composer clears
- When current turn completes (`on_done`): next queued item (state `next`) is auto-submitted
- Queue drawer expansion is frontend-local toggle
- Item editing: clicking/selecting a queued item loads its text into an inline editor

## Persistence behavior

- Queue state is frontend-local during a session (not persisted to SQLite)
- On session resume: queue is empty (queue does not survive session switches)
- On recovery: queue items in `queued` state are preserved; `draft` items may be lost

## Commands/keybindings

| Key/Command | Action |
|---|---|
| `Alt+Enter` | Queue current composer draft |
| `/freeze` | Toggle queue drawer expansion (shared with scroll-lock) |
| Queue item click/select | Edit queued item text |
| Queue item submit | Force-submit selected item |

## Failure/recovery behavior

- If the backend fails mid-submission, the queue item transitions to `blocked` with an error reason
- Blocked items can be retried or cancelled
- If the frontend crashes, queued items are lost (not persisted); `preservedDraft` only preserves the active composer text

## Tests and fixtures

- Track 4: `ready` scene validates collapsed queue strip absence (empty queue = no strip)
- PTY smoke: queue behavior when agent is active
- Reducer tests for queue state transitions

## Acceptance criteria

- [ ] `QueueItem` and `QueueItemState` typed models embedded
- [ ] Collapsed queue = 1 row above composer
- [ ] Expanded queue = bottom drawer (NOT overlay, NOT centered modal)
- [ ] `Alt+Enter` queues current draft
- [ ] Queued items editable until submitted
- [ ] Submitted items become read-only transcript entries
- [ ] No dimmed backdrop when queue is expanded

## Open questions

- Should the queue support drag-to-reorder items?
- Maximum queue depth before rejection?
- Should blocked items auto-retry, or require manual intervention?
- Visual design of the collapsed strip — just count or preview of next item?
