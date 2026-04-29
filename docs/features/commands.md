# Commands

## Purpose

Defines the command registry contract, slash-command catalog, palette behavior, and keybinding enumeration. The core rule: **slash picker, Ctrl+K command palette, Ctrl+Shift+P focus mode, keybindings, and custom commands ALL share one unified command registry.** There is one source of truth for all discoverable commands.

## User-visible TUI surfaces

- Slash-autocomplete dropdown: triggered by typing `/` in the composer
- Command palette: triggered by `Ctrl+K`, showing all commands with type-to-filter
- Slash command execution: `/command [args]` submitted as a `command` RPC request
- `/help` overlay showing command catalog

## Backend contract

### Typed model

```ts
interface CommandDefinition {
  id: string;
  slashName?: string;
  title: string;
  description: string;
  keybinding?: string;
  category:
    | "session"
    | "model"
    | "queue"
    | "diff"
    | "recovery"
    | "settings"
    | "search"
    | "permissions"
    | "tools";
  enabledWhen: string;
  argsSchema?: unknown;
  runMode: "immediate" | "composer_insert" | "focus_mode" | "drawer";
}
```

### Same-registry rule

Slash picker, `Ctrl+K` command palette, `Ctrl+Shift+P` focus mode, keybindings, and custom commands **must all use the same command registry.** A command registered once is discoverable through all these surfaces.

### RPC methods

| Method | Direction | Params | Result |
|---|---|---|---|
| `command` | Frontend → Backend | `cmd: string` | `ok: bool, compacted: bool, messages_compacted: int, summary_tokens: int` |
| `command.list` | Frontend → Backend | _(none)_ | `commands: CommandListEntry[]` |

```ts
interface CommandListEntry {
  name: string;
  aliases: string[];
  description: string;
}
```

## Current slash-command catalog

| Command | Aliases | Category | Description |
|---|---|---|---|
| `/exit` | `/quit`, `/q` | session | Quit the application |
| `/new` | — | session | Start a new session |
| `/sessions` | `/s` | session | List sessions |
| `/resume` | — | session | Resume a session by ID |
| `/help` | `/h`, `/?` | session | Show available commands |
| `/model` | `/m` | model | Show or switch the LLM model |
| `/provider` | — | model | Show, list, or switch the LLM provider |
| `/mode` | `/permissions` | permissions | Show or switch approval mode |
| `/tui` | `/screen` | settings | Show or save the default TUI launch mode |
| `/compact` | — | session | Compact session history |
| `/init` | — | settings | Create project memory file |
| `/shell` | — | settings | Enable or disable shell execution |
| `/copy` | `/cp` | session | Copy last response |
| `/freeze` | `/scroll-lock` | session | Toggle auto-scroll |
| `/thinking` | `/think` | settings | Toggle thinking token visibility |
| `/clear` | `/cls` | session | Clear the terminal screen |
| `/loop` | — | tools | Recurring jobs |
| `/index` | — | tools | Build or rebuild the code search index |
| `/tasks` | `/t` | tools | Show task board |
| `/plan` | — | tools | Plan mode control |
| `/research` | `/comprehend` | tools | Research mode control |
| `/build` | — | tools | Build mode (verification required) |
| `/review` | — | tools | Review mode (read-only) |
| `/memory` | `/mem` | tools | Show learned patterns |
| `/checkpoint` | `/ckpt` | recovery | List or save checkpoints |
| `/undo` | — | recovery | Restore the most recent checkpoint |
| `/diff` | — | diff | Show git diff of session changes |
| `/cost` | `/tokens`, `/usage` | session | Show token usage and estimated cost |
| `/export` | — | session | Export conversation to markdown |

## Current keybindings

| Key | Context | Action |
|---|---|---|
| `Ctrl+C` (double) | Global | Exit application |
| `Ctrl+C` (single) | Active streaming | Cancel current turn |
| `Ctrl+K` | Global | Open command palette |
| `Ctrl+T` | Global | Toggle thinking visibility |
| `Ctrl+Q` | Global | Toggle queue drawer |
| `Ctrl+L` | Global | Toggle detail surface |
| `Ctrl+E` | Composer | Open external editor |
| `Ctrl+U` | Composer | Clear current input line |
| `Enter` | Composer | Submit (single-line) or newline (multi-line) |
| `Alt+Enter` | Composer | Queue current draft |
| `Esc` | Palette/picker/recovery | Dismiss overlay/picker |
| `/` | Composer (start of input) | Trigger slash autocomplete |
| `Up/Down` | Idle stage | Scroll transcript or navigate history |
| `j/k` | Palette/picker | Navigate list |

## Event types

- `command.list` response carries the catalog
- `command` response carries execution result

## State/reducer behavior

- Frontend fetches command catalog on session start via `command.list`
- Palette state: filter string, cursor position, filtered results
- Slash-autocomplete state: triggered when input starts with `/`, shows matching commands
- Palette dismissed on `Esc` or command execution
- Command execution sends `command` RPC with the full `/command args` string

## Persistence behavior

- Command registry is backend-owned; no frontend persistence needed
- Palette filter state is frontend-local only

## Commands/keybindings

Covered in the catalog tables above. All commands use the same registry.

## Failure/recovery behavior

- If `command.list` fails, frontend falls back to a hardcoded minimal command set
- If `command` execution fails, `on_error` is emitted with the failure message
- Unknown commands: backend returns error; frontend shows error in transcript

## Tests and fixtures

- `autocode/tests/unit/test_backend_server.py` — command dispatch tests
- `autocode/src/autocode/app/commands.py` — `CommandRouter` unit tests
- PTY smoke: slash command surface coverage
- Track 4: `palette` scene — command palette rendering

## Acceptance criteria

- [ ] `CommandDefinition` typed model embedded
- [ ] Same-registry rule explicitly documented
- [ ] All 29 current slash commands enumerated with aliases
- [ ] All current keybindings enumerated
- [ ] `command.list` and `command` RPC methods documented
- [ ] Palette and slash-autocomplete share the same registry

## Open questions

- Should custom user commands be supported (user-defined aliases or scripts)?
- Should `Ctrl+Shift+P` have a different filtered view from `Ctrl+K` (e.g., only non-slash commands)?
- Should commands support tab-completion for arguments?
- How should the palette handle commands with required arguments?
