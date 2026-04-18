# Skills Contract

Stable TUI v1 Milestone B.2 — Claude-Code-compatible skills discovery with
progressive disclosure.

## Goal

Let existing Claude Code / Codex / Pi skill directories work unchanged.
Project-level `.claude/skills/` skills are discovered alongside user-level
`~/.claude/skills/` skills. Only the frontmatter is loaded up front; full
bodies load lazily on demand.

## Public API

Module: `autocode.agent.skills`

| Symbol | Purpose |
|---|---|
| `SkillCatalog(project_root, user_skills_dir)` | Main entry point. |
| `SkillCatalogEntry` | Dataclass — one catalog row (frontmatter only). |
| `SkillSource` | Enum — `PROJECT` or `USER`. |
| `skill_catalog_section(entries)` | Build the system-prompt section. |
| `default_catalog(project_root)` | Factory using `~/.claude/skills/` as user dir. |

### Scan + progressive disclosure

```python
from autocode.agent.skills import default_catalog, skill_catalog_section

catalog = default_catalog("/path/to/project")
entries = catalog.scan()                       # cheap — frontmatter only
section = skill_catalog_section(entries)       # system-prompt text
body = catalog.load_body("plan-first")         # lazy — reads file now
if catalog.reload_if_changed("plan-first"):
    body = catalog.load_body("plan-first")     # live-reload support
```

### Discovery order

1. `<project_root>/.claude/skills/<name>/SKILL.md` — project scope
2. `<user_skills_dir>/<name>/SKILL.md` — user scope (default: `~/.claude/skills/`)

On name collision, project scope wins; user-scope entry is hidden.

## SKILL.md file format

```markdown
---
name: plan-first
description: Read-only planning phase — produce a numbered plan.
allowed-tools: [Read, Grep, Glob]
disable-model-invocation: false
---

# Plan First

## Purpose
...
```

Frontmatter is a simple YAML-subset block between `---` fences at the top of
the file. Supported fields:

| Field | Required | Type | Meaning |
|---|---|---|---|
| `name` | yes | str | Skill identifier; collisions resolved project-over-user. |
| `description` | no | str | Shown in the model-visible catalog section. |
| `allowed-tools` | no | list | Tools the skill may invoke (flow-style `[A, B]`). |
| `disable-model-invocation` | no | bool | If true, hidden from model catalog. |

### Unsupported today (can be added post-v1)

- Nested / multi-line YAML structures
- Linked-file `resources:` manifest
- `context: fork` subagent execution control
- Skill-scoped hooks

These are accepted in the file (ignored by the parser) so users can keep the
full Claude Code spec in place without errors.

## System prompt section

`skill_catalog_section(entries)` builds the model-visible block:

```text
Available skills:
- plan-first — Read-only planning phase — produce a numbered plan.
- build-verified — Edits + mandatory verification.
- review-and-close — Diff review, risk summary, go/no-go.
```

Entries with `disable-model-invocation: true` are excluded. Empty input
returns an empty string, which callers can drop in without a conditional.

## Progressive disclosure guarantee

`scan()` does NOT read skill bodies. It reads frontmatter (short) and stats
each file for mtime tracking. This is verified by an internal test that
confirms `SkillCatalog._cached_body_count() == 0` immediately after a
scan that discovered a skill with a 1 MB body.

## Live reload

`reload_if_changed(name)` stat-checks the skill file. If its mtime advanced,
the cached body is invalidated and the internal entry updated. Next
`load_body()` call reads from disk.

Callers integrating with a long-running process (e.g., the interactive TUI
loop) should call `reload_if_changed(name)` before each invocation where
reflecting in-session edits matters.

## Factory wiring

`autocode.agent.factory.load_project_memory_content(project_root)` appends
`skill_catalog_section(catalog.scan())` after the rules/memory text. The
integration is best-effort — any failure (missing dir, parse error) degrades
to no catalog section rather than blocking session startup.

## Tests

See `autocode/tests/unit/test_skills.py` for 20 cases covering discovery,
project-over-user precedence, frontmatter parsing, progressive disclosure,
mtime-based reload, and the system-prompt section.
