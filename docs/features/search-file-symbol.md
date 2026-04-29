# Search, File Reference, and Symbol Picker

## Purpose

Defines the contract for `@path` file references, line ranges, fuzzy completion, expansion, and symbol-picker interactions. These are composer-attached pickers — NOT focus-mode overlays.

## User-visible TUI surfaces

- `@path` completion: triggered by typing `@` in the composer, shows file path fuzzy matches
- Line range expansion: `@path:10-25` expands to include the specified line range
- Symbol picker: triggered by a dedicated key or command, shows symbols for the current file or project
- Fuzzy filtering: type-to-filter on all picker surfaces
- Composer-attached rendering: picker appears inline with the composer, not as a separate focus mode

## Backend contract

### File reference model

```ts
interface FileReference {
  path: string;
  startLine?: number;
  endLine?: number;
  expandedContent?: string;
}
```

### Symbol model

```ts
interface SymbolEntry {
  name: string;
  kind: "function" | "class" | "variable" | "import" | "method" | "property" | "module";
  filePath: string;
  line: number;
  endLine?: number;
  parentName?: string;
}
```

### File reference behavior

1. User types `@` in composer
2. Frontend shows fuzzy-matching file path list
3. User selects a file; `@path` is inserted into the composer
4. Optional: user adds `:startLine-endLine` for line range
5. On submit, the backend expands the reference into the chat context
6. Expansion includes the file content (or line range) in the message context

### Symbol picker behavior

1. User triggers symbol picker (command or keybinding)
2. Backend provides symbol list for the current file or project
3. Fuzzy filtering narrows the list
4. Selected symbol inserts `@path:line` reference into composer

### Backend tools supporting search

| Tool | Source | Notes |
|---|---|---|
| `find_references` | Layer 1/2 | Find all references to a symbol |
| `find_definition` | Layer 1/2 | Go to definition |
| `get_type_info` | Layer 1/2 | Type information for symbol |
| `list_symbols` | Layer 1/2 | List symbols in file |
| `search_code` | Layer 1/2 | Search code by pattern |
| `semantic_search` | Layer 2 | Semantic code search |
| `glob_files` | Core | File glob matching |
| `grep_content` | Core | Content search |
| LSP-backed tools | Layer 1 | `lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, `lsp_symbols` |

## Event types

- File reference expansion is handled internally; no separate event type
- Symbol data returned from `list_symbols` or LSP tools

## State/reducer behavior

- File picker state: filter string, cursor, filtered file list
- Symbol picker state: filter string, cursor, filtered symbol list
- Both pickers are composer-attached (rendered inline, not focus mode)
- Tab completion on `@` prefix inserts the selected path
- Escape dismisses the picker without insertion

## Persistence behavior

- File index is cached in `CodeIndex` and warmed on session start
- Symbol data is parsed on-demand (Jedi-backed) and cached per-file
- Active working set feeds file picker ranking (recently-edited files ranked higher)

## Commands/keybindings

| Key | Context | Action |
|---|---|---|
| `@` | Composer (start of reference) | Trigger file path completion |
| `Tab` | File picker | Insert selected path |
| `Esc` | File/symbol picker | Dismiss picker |
| `Up/Down` | File/symbol picker | Navigate picker list |

## Failure/recovery behavior

- If file index is not built, `@` completion shows empty list with hint to run `/index`
- If symbol parsing fails (syntax error), the symbol picker skips that file
- Fuzzy matching degrades gracefully: if no matches, shows "no results"

## Tests and fixtures

- `autocode/tests/unit/` — search and symbol tool tests
- `S-L1L2PREVIEW` verification: Layer 1 symbol previews in bootstrap
- Artifact: `autocode/docs/qa/test-results/20260425-171054-s-l1l2preview-verification.md`

## Acceptance criteria

- [ ] File reference model documented (`@path`, line ranges)
- [ ] Symbol picker contract documented
- [ ] Composer-attached pickers (NOT focus mode for these three: file, symbol, search)
- [ ] Fuzzy completion behavior documented
- [ ] Expansion semantics: reference → content in context
- [ ] All search-related backend tools enumerated

## Open questions

- Should `@path` support directory references (listing directory contents)?
- Should symbol picker be scoped to the current file, open files, or the whole project?
- Maximum file size for inline expansion?
- Should the picker support multi-select (insert multiple references)?
