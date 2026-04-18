# Project Memory Rules Loader Contract

Stable TUI v1 Milestone B.1 — the migration-critical surface for loading
project memory files. Claude Code / Codex / OpenCode users can drop their
existing `CLAUDE.md` / `CLAUDE.local.md` / `AGENTS.md` / `.cursorrules` into
an AutoCode project and expect them to load predictably.

## Public API

Module: `autocode.layer2.rules`

| Symbol | Purpose |
|---|---|
| `RulesLoader` | Entry point; has `load()` (legacy) and `load_detailed()` (new). |
| `RulesResult` | Rich result: `text`, `sources`, `skipped_imports`, `circular_detected`. |
| `LoadedSource` | Provenance record for one included file. |
| `Provenance` | `StrEnum` of origin labels (CLAUDE_MD, IMPORT, EXTERNAL_IMPORT, …). |

### Legacy API (backward compatible)

```python
from autocode.layer2.rules import RulesLoader

text = RulesLoader().load("/path/to/project")
```

Existing callers (`agent.factory.load_project_memory_content`) continue to
work unchanged. The return type is `str`; all optional knobs default to
safe values.

### Detailed API

```python
result = RulesLoader().load_detailed(
    project_root,
    include_local=True,              # loads CLAUDE.local.md after CLAUDE.md
    include_imports=True,            # expands @imports
    max_import_depth=5,              # hard cap on @import recursion
    external_import_approver=None,   # Callable[[Path], bool] for files outside project
    strip_html_comments=True,        # removes <!-- ... -->
    max_file_bytes=50_000,           # per-file truncation
    walk_up_to=None,                 # Path to walk up to (broad → specific)
)
```

Returns a `RulesResult` where:

- `result.text` — concatenated rules (same as legacy `load()` output)
- `result.sources` — ordered `list[LoadedSource]` with full provenance
- `result.skipped_imports` — `list[str]` describing external/out-of-depth skips
- `result.circular_detected` — `list[str]` short-chain descriptions

## File discovery order

Per directory in the walk chain (broad → specific), files load in this order
and are concatenated:

1. `CLAUDE.md` — Claude Code's primary project memory file
2. `CLAUDE.local.md` — user-local overrides (loaded after `CLAUDE.md` so
   later entries take precedence in practice)
3. `AGENTS.md` — OpenAI Codex / generic agent instructions
4. `.cursorrules` — Cursor IDE rules
5. `.rules/*.md` — sorted alphabetically

### Directory walk

By default only the supplied `project_root` is scanned. Pass `walk_up_to=<Path>`
to also include every ancestor directory up to (and including) that path.
Ancestors contribute BEFORE the project root so narrower rules override
broader ones.

## @import syntax

A line matching `@<path>` on its own (leading whitespace permitted) is
expanded inline. `<path>` resolves relative to the file containing the
directive.

- **Relative imports** (default) — resolved and expanded inline.
- **External imports** — if the resolved path is OUTSIDE `project_root`,
  the loader will only include it when `external_import_approver(path)`
  returns truthy. Default behavior is to skip and record a
  `skipped_imports` entry.
- **Bounded depth** — `max_import_depth` (default 5) caps the depth of
  `@import` chains. Exceeding the cap records a `skipped_imports` entry
  and leaves a placeholder in the text.
- **Circular-import guard** — a file already loaded is not loaded again; a
  `circular_detected` entry is recorded.

Literal `@<token>` lines that do not resolve to a file are left intact so
user free-form content is not corrupted.

## Truncation

Each individual file is truncated at `max_file_bytes` bytes (default 50 000).
A `\n...(truncated)\n` marker is appended to the included body so reviewers
see that content was dropped.

## HTML block comments

By default `<!-- ... -->` comments are stripped (multiline-aware) so
private scratch notes in `CLAUDE.md` do not leak into the prompt. Pass
`strip_html_comments=False` to preserve them.

## Provenance labels

`LoadedSource.kind` uses the `Provenance` enum:

- `CLAUDE_MD` — `CLAUDE.md` in any walked directory
- `CLAUDE_LOCAL_MD` — `CLAUDE.local.md`
- `AGENTS_MD` — `AGENTS.md`
- `CURSOR_RULES` — `.cursorrules`
- `RULES_DIR` — files under `.rules/`
- `IMPORT` — `@import` target INSIDE `project_root`
- `EXTERNAL_IMPORT` — `@import` target OUTSIDE `project_root`, approved by caller

## Unsupported / out of scope

The following Claude Code features are intentionally NOT in this loader's
contract. They belong to different layers:

- **Skill frontmatter discovery** — handled by `autocode.agent.skills.SkillCatalog` (Milestone B.2).
- **Hook lifecycle** — handled by `autocode.agent.hooks.HookRegistry` (Milestone B.3).
- **Prompt cache boundary** — not implemented; post-v1 optimization.

## Tests

See `autocode/tests/unit/test_rules_imports.py` for the 23-case fixture
matrix exercising every edge above.
