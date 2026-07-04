# AutoCode IDE UI ↔ Harness Coverage Map

Scope: `AutoCode.html` (implementation of `AutoCode.dc.html`, Claude Design project
"IDE with intellisense redesign") checked against `docs/features/inventory.md`
(refreshed 2026-04-30). This is the **GUI/IDE surface** for the AutoCode harness —
a separate frontend concept from the canonical Rust TUI (`autocode/rtui`), not a
replacement for it.

## How this UI differs from the TUI

The Rust TUI is a terminal transcript + composer with pickers and modals. This IDE UI
adds surfaces a terminal cannot carry: a real editor pane with LSP-style IntelliSense,
a side-by-side review/staging rail, card-based thread management across parallel
sessions, and full-page Automations / Skills / Settings views. Both frontends would sit
on the same JSON-RPC backend (`autocode serve --transport tcp`), which is already
single-active-client TCP attach today.

## Surface → harness mapping (backed today)

| UI surface | Harness feature (inventory §) |
|---|---|
| Threads list, search, resume | Sessions: SQLite store, list/resume/fork (§6) |
| Home composer, `/` skills popover | Backend-owned slash command registry (§12) |
| Plan card with step states | `/plan`, `/tasks`, `todo_read`/`todo_write` (§5, §12) |
| Act cards: "Read 3 files", `pnpm vitest run`, "Edited pricing.ts" | Tool families + `tool_call_started/completed` events (§5, §11) |
| Approval card (sandbox/network escalation) | Permission modes, approval decisions, shell enablement (§7) |
| Thinking indicator | Think-token streaming (§2, §3.4) |
| Model picker + reasoning effort | `/model`, `/provider`, cost-aware tier routing (§2, §12) |
| Editor: hover docs, peek definition, go-to, references | `lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, `find_definition`, `get_type_info` (§3.2, §5) |
| Editor: diagnostics + quick fix ("endAt → endsAt") | Auto-verify post-edit diagnostics (§4) |
| Review rail: per-file diff, staging | `/diff`, diff-review payload, git-aware staging (§9) |
| Settings → Permissions cards (Read-only / Balanced / Full) | read-only / suggest / auto / autonomous modes (§7) |
| Settings → "Auto-run unit tests after edits" | Auto-verify flow (§4) |
| Usage meter / Plan & usage | Cost dashboard, `/cost`, token accounting (§8) |
| Automations ("Weekly dependency audit" thread t5) | Partially: `/loop`, `/watch`, `/recipe` (§12) |

## Gaps: UI shows it, harness doesn't have it yet

- **Cloud execution mode** — backend is local stdio/TCP only (§13 remote hardening deferred).
- **Worktree mode as a first-class session property** — closest today is `/fork` + `/tree`.
- **PR creation / "Commit staged & open PR"** — conflicts with current repo policy
  (agents never commit; forbidden git ops §9). Would need an explicit user-gated flow.
- **Editor completions, signature help, inlay hints, ghost text** — LSP surface exposes
  definitions/references/types, but not completion/signatureHelp/inlayHint requests;
  ghost text needs an inline-completion path (L4 streaming or L3).
- **MCP server management (add/reconnect/toggle)** — harness ships a read-only MCP
  *server*; client-side MCP config management is not in the inventory.
- **Scheduled automations with cron-like triggers** — `/watch` and `/loop` are the seeds;
  no scheduler/event-trigger runtime yet.
- **Billing/quota ("62% of weekly compute")** — cost accounting exists; quota/plan
  enforcement does not.

## Gaps: harness has it, UI doesn't show it yet

Candidate next surfaces if this becomes the real frontend: checkpoints/undo/rollback
(§6, §9), subagents & task DAG panel (§5 orchestration tools; TUI already has a side
panel), memory store (§6), `/cost --detail` dashboard (§8), session fork/tree
visualization (§12), transcript export (§12), compaction status (§6), `ask_user`
generic prompts (§5) beyond the approval card.

## Verification of the implementation

- `AutoCode.html` is fully self-contained (no React/runtime dependency, unlike the
  `.dc.html` source which requires the Claude Design runtime); JetBrains Mono via
  Google Fonts degrades gracefully offline.
- Headless smoke test (Deno, DOM-stubbed): **47/47 checks pass** — all 5 views render;
  all 6 IntelliSense states (ghost text, completions incl. keyboard nav, hover, signature,
  peek, inlay hints); approval allow/deny; act-card expansion; review staging + diff
  switching + PR flow; 3 directions × 2 themes; thread search; async send flows (new
  thread + reply); toast lifecycle; balanced markup.
