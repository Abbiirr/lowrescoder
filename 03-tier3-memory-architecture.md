# Tier 3 — Memory Architecture

**Goal:** match Claude Code's memory quality so AutoCode survives long sessions and remembers project conventions across restarts.

**Total cost:** ~3 weeks engineering, ~1100 LOC.

**Why this matters:** the current `MemoryStore` puts everything in a single SQLite table. Loading "all memories" into context every turn is expensive and noisy. Claude Code's 3-layer split (index / topic files / daily logs) keeps the always-loaded portion small while letting depth grow arbitrarily.

---

## Tier 3.1 — Three-layer file-system memory

### Files touched

- `src/autocode/session/memory_fs.py` — NEW (~600 LOC)
- `src/autocode/agent/tools.py` — add memory_read_topic, memory_grep_logs, memory_write_topic, memory_index_show
- `src/autocode/session/consolidation.py` — re-target writes from SQLite to topic files (~120 LOC delta)
- `src/autocode/session/memory.py` — keep, but mark deprecated; one-shot migration script
- `src/autocode/agent/loop.py` — load MEMORY.md index on session start (~40 LOC)
- `tests/unit/test_memory_fs.py` — NEW

### Directory layout per project

```
~/.autocode/
└── projects/
    └── <git-root-sha256-prefix>/         ← deterministic from `git rev-parse --show-toplevel`
        ├── MEMORY.md                     ← always loaded; ≤ 200 lines; pointers only
        ├── memory/
        │   ├── architecture.md           ← topic file, loaded on demand
        │   ├── debugging.md
        │   ├── decisions.md
        │   ├── api-patterns.md
        │   └── ...
        └── logs/
            ├── 2026/
            │   ├── 04/
            │   │   ├── 2026-04-29.md     ← append-only daily log
            │   │   └── 2026-04-30.md
            │   └── 05/
            │       └── 2026-05-01.md
```

### `MEMORY.md` format

Hard rules:
- ≤ 200 lines (anything beyond is invisible)
- ~150 chars per pointer line
- Pointers only — never content

```markdown
# Project Memory — autocode
Last updated: 2026-04-30

## Quick facts (5-10 lines max)
- Python 3.11+ backend, Rust frontend (rtui)
- uv for Python deps; cargo for Rust
- Tests: pytest tests/, cargo test in rtui/

## Topics (5-10 pointer lines)
- See [architecture.md](./memory/architecture.md) for module layout
- See [debugging.md](./memory/debugging.md) for known gotchas
- See [decisions.md](./memory/decisions.md) for ADRs
- See [api-patterns.md](./memory/api-patterns.md) for RPC schema

## Recent (5-10 most recent decisions)
- 2026-04-30: Added prompt cache breakpoint injection (see decisions.md#cache)
- 2026-04-29: Migrated TUI Go→Rust complete
- 2026-04-15: Backend v2 ships

## Active work pointers
- Logs: see `logs/2026/04/` for daily session notes
- Open: backend tranche 4 — see decisions.md#backend-tranche-4
```

### Topic file format

YAML frontmatter + Markdown body:

```markdown
---
topic: debugging
type: project
created: 2026-04-15
updated: 2026-04-29
size_lines: 142
---

# Debugging gotchas

## Async gotcha: SQLite row_factory race
On fresh connections, `row_factory` may be unset. Always set explicitly
when inheriting a connection from another scope.

Reproducer:
```python
conn = sqlite3.connect(":memory:")  # row_factory is None
cursor.execute(...)  # returns tuples, not Row objects
```

Fix in `task_store.py`:
```python
if conn.row_factory is None:
    conn.row_factory = sqlite3.Row
```

## ...
```

Topic file caps:
- Soft limit: 1000 lines per file
- Beyond that: split into `<topic>-<sub>.md` (e.g. `debugging-async.md`)

### Daily log format

Append-only. Each session appends a timestamped block:

```markdown
# 2026-04-30

## 09:32 - Session a8f3c1 (qwen3-coder:free, openrouter)
**Goal:** add prompt cache breakpoint injection

**Done:**
- Added `_inject_cache_breakpoint` in OpenRouterProvider
- Added cache token capture
- Wrote 3 unit tests, all passing

**Decisions:**
- TTL set to 1h (extended) for system prompt — typical session > 5min
- Tool defs serialized with sort_keys for determinism

**Open threads:**
- Verify on real Anthropic call (no API key in test env)
- Need to add `/cost` cache breakdown display

**Stats:** files:3 reads:12 writes:5 tools:18 tokens:23k

---

## 14:15 - Session b9d2e3 (qwen3-coder:free, openrouter)
**Goal:** wire stable/dynamic boundary
...
```

### Implementation: `MemoryFS` class

```python
# src/autocode/session/memory_fs.py

from pathlib import Path
from datetime import datetime, UTC
import hashlib
import re
import yaml

class MemoryFS:
    """File-system-based 3-layer memory store.

    Layer 1: MEMORY.md index — always loaded into context, ≤ 200 lines
    Layer 2: memory/<topic>.md — loaded on demand via memory_read_topic tool
    Layer 3: logs/YYYY/MM/YYYY-MM-DD.md — never auto-loaded; grep-only

    Per Claude Code source leak: agent treats memory as a HINT, not truth.
    Verify before acting.
    """

    INDEX_MAX_LINES = 200
    INDEX_LINE_MAX_CHARS = 150
    TOPIC_FILE_SOFT_LIMIT_LINES = 1000

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.base_dir = self._compute_base_dir(project_root)
        self.index_path = self.base_dir / "MEMORY.md"
        self.topics_dir = self.base_dir / "memory"
        self.logs_dir = self.base_dir / "logs"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.topics_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    @staticmethod
    def _compute_base_dir(project_root: Path) -> Path:
        """Hash the canonical git root for stable per-project identity.

        Same project across worktrees → same memory dir.
        """
        try:
            import subprocess
            r = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=project_root, capture_output=True, text=True, timeout=5,
            )
            canonical = r.stdout.strip() if r.returncode == 0 else str(project_root)
        except Exception:
            canonical = str(project_root)

        h = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return Path.home() / ".autocode" / "projects" / h

    # === LAYER 1: INDEX ===

    def read_index(self) -> str:
        """Read MEMORY.md (Layer 1). Always called at session start."""
        if not self.index_path.exists():
            return self._initial_index()
        return self.index_path.read_text(encoding="utf-8")

    def _initial_index(self) -> str:
        return (
            "# Project Memory\n"
            f"Last updated: {datetime.now(UTC).date().isoformat()}\n\n"
            "## Quick facts\n"
            "- (none yet — will populate as agent learns)\n\n"
            "## Topics\n"
            "- (no topic files yet)\n\n"
            "## Recent\n"
            "- (no recent decisions)\n"
        )

    def update_index_pointer(self, topic_slug: str, summary: str) -> None:
        """Add or update a pointer line in MEMORY.md.

        summary is ≤ 100 chars; combined with the link, total ≤ 150.
        """
        if len(summary) > 100:
            summary = summary[:97] + "..."

        pointer_line = f"- See [{topic_slug}.md](./memory/{topic_slug}.md): {summary}"
        if len(pointer_line) > self.INDEX_LINE_MAX_CHARS:
            pointer_line = pointer_line[:self.INDEX_LINE_MAX_CHARS - 3] + "..."

        index = self.read_index()
        topics_section_re = re.compile(r"(## Topics\n)(.*?)(\n## )", re.DOTALL)
        match = topics_section_re.search(index)
        if not match:
            # No Topics section — append one
            index += f"\n## Topics\n{pointer_line}\n"
        else:
            existing_topics = match.group(2)
            # Replace existing pointer for this topic if any
            same_topic_re = re.compile(
                rf"^- See \[{re.escape(topic_slug)}\.md\].*$", re.MULTILINE
            )
            if same_topic_re.search(existing_topics):
                existing_topics = same_topic_re.sub(pointer_line, existing_topics)
            else:
                existing_topics = existing_topics.rstrip() + "\n" + pointer_line
            index = topics_section_re.sub(
                rf"\1{existing_topics}\3", index
            )

        # Truncate if over 200 lines (FIFO drop oldest "Recent" entries)
        index = self._truncate_index(index)

        self.index_path.write_text(index, encoding="utf-8")

    def _truncate_index(self, content: str) -> str:
        lines = content.splitlines()
        if len(lines) <= self.INDEX_MAX_LINES:
            return content
        # Drop oldest "Recent" lines first
        recent_re = re.compile(r"^## Recent\n((?:- .*\n)*)", re.MULTILINE)
        match = recent_re.search(content)
        if match:
            recent_lines = match.group(1).strip().splitlines()
            if len(recent_lines) > 2:
                # Drop oldest half
                kept = recent_lines[len(recent_lines)//2:]
                content = recent_re.sub(
                    f"## Recent\n" + "\n".join(kept) + "\n", content
                )
        # If still too long, hard truncate
        return "\n".join(content.splitlines()[:self.INDEX_MAX_LINES])

    # === LAYER 2: TOPIC FILES ===

    def read_topic(self, slug: str) -> str | None:
        """Read a topic file (Layer 2). On-demand load."""
        path = self.topics_dir / f"{slug}.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write_topic(self, slug: str, content: str, *, summary: str | None = None) -> None:
        """Write or replace a topic file. Auto-updates index pointer.

        Per Claude Code design: write topic file FIRST, then index.
        That way if write fails partway, index doesn't have a dead pointer.
        """
        slug = self._sanitize_slug(slug)
        path = self.topics_dir / f"{slug}.md"

        # Add/update frontmatter
        body, existing_meta = self._extract_frontmatter(content)
        meta = existing_meta or {}
        meta.setdefault("topic", slug)
        meta.setdefault("type", "project")
        meta.setdefault("created", datetime.now(UTC).date().isoformat())
        meta["updated"] = datetime.now(UTC).date().isoformat()
        meta["size_lines"] = len(body.splitlines())

        full = f"---\n{yaml.safe_dump(meta, sort_keys=True)}---\n\n{body}"

        # Soft size warning
        if meta["size_lines"] > self.TOPIC_FILE_SOFT_LIMIT_LINES:
            # Recommend split — log warning, don't block
            import logging
            logging.warning(
                "Topic file %s.md exceeds %d lines — consider splitting",
                slug, self.TOPIC_FILE_SOFT_LIMIT_LINES,
            )

        path.write_text(full, encoding="utf-8")

        # Update index AFTER successful topic write
        if summary is None:
            summary = self._derive_summary(body)
        self.update_index_pointer(slug, summary)

    def list_topics(self) -> list[str]:
        return sorted(p.stem for p in self.topics_dir.glob("*.md"))

    @staticmethod
    def _sanitize_slug(slug: str) -> str:
        slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "untitled"

    @staticmethod
    def _extract_frontmatter(content: str) -> tuple[str, dict | None]:
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end != -1:
                meta = yaml.safe_load(content[4:end])
                body = content[end+5:]
                return body, meta
        return content, None

    @staticmethod
    def _derive_summary(body: str) -> str:
        """Take first non-heading paragraph as summary."""
        for para in body.split("\n\n"):
            para = para.strip()
            if para and not para.startswith("#"):
                return para.splitlines()[0][:100]
        return "(no summary)"

    # === LAYER 3: DAILY LOGS ===

    def append_log(self, session_id: str, entry: dict) -> None:
        """Append a session entry to today's daily log.

        entry shape:
            {
                "session_id": str,
                "model": str,
                "provider": str,
                "goal": str,
                "done": list[str],
                "decisions": list[str],
                "open_threads": list[str],
                "stats": dict,
            }
        """
        today = datetime.now(UTC).date()
        path = self.logs_dir / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.isoformat()}.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        time_str = datetime.now(UTC).strftime("%H:%M")
        block = self._format_log_block(time_str, entry)

        if path.exists():
            path.write_text(path.read_text() + "\n\n---\n\n" + block, encoding="utf-8")
        else:
            path.write_text(f"# {today.isoformat()}\n\n" + block, encoding="utf-8")

    @staticmethod
    def _format_log_block(time_str: str, entry: dict) -> str:
        lines = [
            f"## {time_str} - Session {entry['session_id'][:8]} "
            f"({entry.get('model', '?')}, {entry.get('provider', '?')})",
            f"**Goal:** {entry.get('goal', '(none)')}",
            "",
            "**Done:**",
        ]
        for d in entry.get("done", []) or ["(nothing yet)"]:
            lines.append(f"- {d}")
        lines.append("")
        if entry.get("decisions"):
            lines.append("**Decisions:**")
            for d in entry["decisions"]:
                lines.append(f"- {d}")
            lines.append("")
        if entry.get("open_threads"):
            lines.append("**Open threads:**")
            for o in entry["open_threads"]:
                lines.append(f"- {o}")
            lines.append("")
        if entry.get("stats"):
            stats_str = " ".join(f"{k}:{v}" for k, v in entry["stats"].items())
            lines.append(f"**Stats:** {stats_str}")
        return "\n".join(lines)

    def grep_logs(
        self,
        pattern: str,
        *,
        days: int = 30,
        max_matches: int = 50,
    ) -> list[dict]:
        """Search recent daily logs for a regex pattern.

        Returns list of {date, line, snippet} matches.
        """
        regex = re.compile(pattern, re.IGNORECASE)
        matches = []
        today = datetime.now(UTC).date()

        for offset in range(days):
            d = today - timedelta(days=offset)
            path = self.logs_dir / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.isoformat()}.md"
            if not path.exists():
                continue
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if regex.search(line):
                    matches.append({
                        "date": d.isoformat(),
                        "line": i,
                        "snippet": line[:200],
                    })
                    if len(matches) >= max_matches:
                        return matches
        return matches
```

### New tools exposed to the agent

```python
# Add to src/autocode/agent/tools.py inside create_default_registry

def _make_memory_tools(memory_fs: MemoryFS) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="memory_read_topic",
            description=(
                "Read the contents of a memory topic file. Use this to "
                "look up context that was previously saved. The MEMORY.md "
                "index is auto-loaded; use this tool to read deeper. "
                "Topic slugs are listed in the 'Topics' section of MEMORY.md."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Topic slug, e.g. 'debugging'"}
                },
                "required": ["slug"],
            },
            handler=lambda **kw: (
                memory_fs.read_topic(kw["slug"]) or
                f"Topic '{kw['slug']}' not found. Available: " + ", ".join(memory_fs.list_topics())
            ),
            requires_approval=False,
            safe=True,
        ),

        ToolDefinition(
            name="memory_write_topic",
            description=(
                "Write or replace a memory topic file. Use this to "
                "record durable, project-specific knowledge that should "
                "survive across sessions: architecture decisions, debugging "
                "gotchas, API patterns. Auto-updates MEMORY.md index. "
                "DO NOT use for ephemeral session state."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "content": {"type": "string"},
                    "summary": {"type": "string", "description": "≤100 chars; shown in index"},
                },
                "required": ["slug", "content"],
            },
            handler=lambda **kw: (
                memory_fs.write_topic(kw["slug"], kw["content"], summary=kw.get("summary"))
                or f"Wrote topic '{kw['slug']}'"
            ),
            requires_approval=False,
            safe=True,
        ),

        ToolDefinition(
            name="memory_grep_logs",
            description=(
                "Search recent daily session logs for a regex pattern. "
                "Use this to recall what was done in past sessions. "
                "Logs are append-only and contain timestamps, decisions, "
                "open threads, and stats per session."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "days": {"type": "integer", "default": 30},
                },
                "required": ["pattern"],
            },
            handler=lambda **kw: json.dumps(
                memory_fs.grep_logs(kw["pattern"], days=kw.get("days", 30)),
                indent=2,
            ),
            requires_approval=False,
            safe=True,
        ),

        ToolDefinition(
            name="memory_index_show",
            description="Show the current MEMORY.md index. Useful to remind yourself what topic files exist.",
            parameters={"type": "object", "properties": {}},
            handler=lambda **kw: memory_fs.read_index(),
            requires_approval=False,
            safe=True,
        ),
    ]
```

### Auto-load index at session start

In `agent/loop.py` or `backend/server.py`, when the agent loop is initialized, prepend `MEMORY.md` content to the system prompt's stable prefix:

```python
# In server._ensure_agent_loop after RulesLoader

memory_fs = MemoryFS(self.project_root)
memory_index = memory_fs.read_index()

# Append to memory_content (which gets injected as system context)
if memory_index:
    memory_content = (
        memory_index + "\n\n" + memory_content
        if memory_content
        else memory_index
    )
```

### Migration from current SQLite `MemoryStore`

One-shot script `scripts/migrate_memory_to_fs.py`:

1. Read all rows from `memories` table
2. Group by category: `tool_pattern` → `patterns.md`, `user_preference` → `preferences.md`, `project_fact` → `facts.md`, `error_resolution` → `debugging.md`
3. Write each group to a topic file
4. Build index pointers
5. Mark old SQLite table for deletion (rename to `memories_archive_<date>`)

### Acceptance tests

```python
def test_index_truncated_to_200_lines():
    fs = MemoryFS(tmp_path)
    long_content = "\n".join(f"line {i}" for i in range(500))
    fs.index_path.write_text(long_content)
    fs.update_index_pointer("test", "some summary")
    final = fs.index_path.read_text()
    assert len(final.splitlines()) <= 200


def test_topic_write_creates_index_pointer():
    fs = MemoryFS(tmp_path)
    fs.write_topic("debugging", "# Debug\n\nKnown issues...", summary="Async gotcha")
    index = fs.read_index()
    assert "[debugging.md]" in index
    assert "Async gotcha" in index


def test_grep_logs_finds_recent_match():
    fs = MemoryFS(tmp_path)
    fs.append_log("abc123", {
        "session_id": "abc123",
        "goal": "Fix Redis port conflict",
        "done": ["Updated docker-compose.yml"],
    })
    matches = fs.grep_logs("Redis")
    assert len(matches) == 1
    assert "Redis" in matches[0]["snippet"]


def test_canonical_git_root_hash_stable_across_worktrees():
    repo1 = make_git_repo(tmp_path / "main")
    repo2 = make_git_worktree(repo1, tmp_path / "wt1")
    fs1 = MemoryFS(repo1)
    fs2 = MemoryFS(repo2)
    assert fs1.base_dir == fs2.base_dir
```

---

## Tier 3.2 — Session Notes living document

### Files touched

- `src/autocode/session/session_notes.py` — NEW (~250 LOC)
- `src/autocode/agent/context.py` — compaction Path A integration (~80 LOC delta)
- `src/autocode/agent/loop.py` — invoke notes update at thresholds (~50 LOC)

### What this is

A Markdown template that the agent updates incrementally during a session. When compaction triggers, the notes serve as the summary instead of a fresh API call (Claude Code's "Path A" vs "Path B").

### Trigger thresholds (verified from research)

- **Activation:** session reaches 10,000 tokens consumed
- **Update interval:** every additional 5,000 tokens
- **Gate:** at least 3 tool calls between updates (don't bother if no work happened)

### Template

```markdown
# Session Notes — <session_id>

**Started:** 2026-04-30T09:32:00Z
**Last updated:** 2026-04-30T11:18:00Z
**Tokens used:** 23,450

## Active goal
Fix the OAuth callback bug where state cookie is lost on redirect.

## Decisions made this session
- Use `SameSite=Lax` instead of `None` (CSRF tradeoff acceptable)
- State cookie TTL reduced from 1h to 10min (tighter security window)

## Files touched
- `src/auth/callback.py` (read, edited)
- `src/auth/state.py` (read, edited)
- `tests/auth/test_callback.py` (created)

## Open threads
- Need to update prod CSP header before deploy
- Frontend needs corresponding cookie attribute change

## Next step
Add integration test that exercises the full callback flow with a real cookie.

---

## Append-only log (most recent first)

### 11:18 (turn 7) — Wrote test_callback.py
Tool calls: write_file (1), run_command (1)

### 10:55 (turn 5) — Edited state.py
Tool calls: read_file (1), edit_file (1)

...
```

### Implementation

```python
# src/autocode/session/session_notes.py

class SessionNotes:
    ACTIVATION_TOKENS = 10_000
    UPDATE_INTERVAL_TOKENS = 5_000
    MIN_TOOL_CALLS = 3

    def __init__(self, session_id: str, base_dir: Path):
        self.session_id = session_id
        self.path = base_dir / "sessions" / f"{session_id}-notes.md"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._tokens_at_last_update = 0
        self._tool_calls_since_update = 0

    def should_update(self, total_tokens: int) -> bool:
        if total_tokens < self.ACTIVATION_TOKENS:
            return False
        if total_tokens - self._tokens_at_last_update < self.UPDATE_INTERVAL_TOKENS:
            return False
        if self._tool_calls_since_update < self.MIN_TOOL_CALLS:
            return False
        return True

    async def update(self, *, agent_loop, total_tokens: int) -> None:
        """Have a subagent update the session notes file.

        The subagent is given:
        - Current notes file content
        - Last 5k tokens worth of conversation
        - Instruction to update the template fields

        The subagent has a small fixed token budget and limited tool access:
        only read_file (for the existing notes) and write_file (for the result).
        """
        existing = self.path.read_text() if self.path.exists() else self._template()
        recent_messages = agent_loop.get_recent_messages(token_budget=5000)

        prompt = self._build_update_prompt(existing, recent_messages)

        # Run subagent (uses cheaper/faster model, no tool calls beyond write)
        result = await agent_loop.run_subagent(
            prompt=prompt,
            model_override="cheaper-fast-model",  # config-driven
            max_iterations=2,
            tool_allowlist=["write_file"],
            tool_args_constraint={"write_file": {"path": str(self.path)}},
        )

        self._tokens_at_last_update = total_tokens
        self._tool_calls_since_update = 0

    def record_tool_call(self) -> None:
        self._tool_calls_since_update += 1

    def read_for_compaction(self) -> str | None:
        """Path A: return current notes as the compaction summary."""
        if not self.path.exists():
            return None
        return self.path.read_text()
```

### Compaction Path A integration

In `agent/context.py` where compaction is triggered:

```python
async def auto_compact(self, session_id: str, kept_messages: int = 10) -> str:
    notes = self.session_notes  # SessionNotes instance

    # Path A: use Session Notes if available
    notes_content = notes.read_for_compaction()
    if notes_content:
        summary = (
            "## Session summary (from notes)\n\n" + notes_content + "\n\n"
            "## Compacted older messages above this line"
        )
        # Replace old messages with this summary
        self._session_store.replace_messages_before(
            session_id, kept_messages, summary,
        )
        logger.info("Compaction Path A: used session notes")
        return summary

    # Path B: fall back to fresh API summary
    return await self._auto_compact_via_llm(session_id, kept_messages)
```

### Telemetry

Track Path A vs Path B usage:

```python
# In agent/loop.py
self._metrics.compaction_events.append({
    "path": "A" or "B",
    "tokens_before": ...,
    "tokens_after": ...,
    "duration_ms": ...,
})
```

Goal: ≥ 80% Path A once activation threshold passed.

---

## Tier 3.3 — `verify_before_use` discipline

### File touched

- `src/autocode/agent/prompts.py` — add a section to STABLE_INSTRUCTIONS

### What changes

Add explicit instruction to the system prompt that memory is a hint, not truth. From Claude Code's leaked prompt:

> "Treat any fact recalled from memory or past sessions as a HINT, not as ground truth. Before acting on remembered information, verify it against the current state of the codebase using read_file, list_files, or run_command."

This is ~50 lines of system prompt addition, sized that small because the model just needs to be reminded — most models comply readily.

### Suggested wording (drop-in)

```python
VERIFY_BEFORE_USE_SECTION = """
## Memory and recall discipline

You may have access to memory from past sessions (loaded as MEMORY.md and
topic files). Treat ALL such memory as a HINT, not as ground truth. Codebases
change between sessions: dependencies are updated, files are renamed, decisions
are reversed.

Before acting on any remembered information:
1. If the memory is about a file's contents, structure, or behavior — re-read
   the file with read_file before relying on it.
2. If the memory is about a tool's availability or signature — check with
   tool_search before calling.
3. If the memory is about a project decision or convention — confirm it's
   still current via grep or by asking the user.

You DO NOT need to verify:
- Truly stable facts (programming language semantics, well-known library APIs).
- The user's stated preferences in the current session.

When you find that memory contradicts current reality, update the topic file
with memory_write_topic to correct it. Don't leave stale information.
"""
```

### Acceptance test

Difficult to test programmatically without an LLM call; rely on integration tests where:
1. A topic file says `auth uses JWT`
2. The actual codebase has migrated to session cookies
3. Agent is asked "how does auth work"
4. Verify model called `read_file` on `auth.py` before answering

---

## What's NOT in Tier 3 (deferred)

- **Auto Memory** (Anthropic's: "Claude saves notes for itself") — requires LLM call after each turn to decide what to save. Defer until baseline 3-layer is stable.
- **Auto Dream advanced features** (timestamp normalization, contradiction resolution) — your `consolidation.py` has the structure; flesh out incrementally.
- **Multi-agent broker pattern** (one agent owns memory, others request via it) — not needed until concurrent agents.
- **Vector-based semantic retrieval** — research shows filesystem-based retrieval beats vector RAG below 100+ documents. Skip until corpus is large.
