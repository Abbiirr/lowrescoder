# Memory Migration V1

P3 introduces file-system durable memory under `~/.autocode/projects/<git-root-sha256-prefix>/`.

## What Migrates

Legacy SQLite rows from the `memories` table are grouped into MemoryFS topics:

- `tool_pattern` -> `memory/patterns.md`
- `user_preference` -> `memory/preferences.md`
- `project_fact` -> `memory/facts.md`
- `error_resolution` -> `memory/debugging.md`
- unknown categories -> `memory/miscellany.md`

The old SQLite table is renamed to `memories_archive_<date>`. It is not dropped.

## Command

```bash
uv run python scripts/migrate_memory_to_fs.py ~/.autocode/sessions.db --project-root /path/to/project
```

The helper is idempotent: if `memories` has already been renamed, rerunning reports zero migrated rows.

## Rollback

Set:

```bash
AUTOCODE_USE_LEGACY_MEMORY=true
```

Backend and headless runners then use the legacy SQLite `MemoryStore` path instead of `MemoryFS`.

## Validation

Focused tests:

```bash
uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py -q
```
