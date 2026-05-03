# Cross-Cutting Concerns

Things that span multiple tiers and need to be planned before any tier is started.

---

## Testing strategy

### Unit tests — keep current style

Each tier change adds unit tests in the appropriate `tests/unit/` location. Names follow existing convention: `test_<module>.py`. Test count assertions in `tests/test_sprint_verify.py` will need bumping each time tools or commands are added — same mechanical pattern done many times before.

**Per-tier test additions:**

| Tier | New test files | Tests added |
|---|---|---|
| 1.1 | `tests/integration/test_prompt_cache.py` | ~6 (cache hit, miss, write premium, TTL expiry, 4-breakpoint limit, OpenRouter sticky) |
| 1.2 | `tests/unit/test_prompt_cache_boundary.py` | ~5 (boundary marker present, no leakage, deterministic tool serialization, RulesLoader in stable, todos in dynamic) |
| 1.3 | `tests/unit/test_token_tracker_cache.py` | ~4 (record_cache aggregation, per-provider breakdown, billable_input_cost_factor, persistence round-trip) |
| 2.1 | `tests/integration/test_app_server_protocol.py` | ~12 (initialize handshake, thread CRUD, turn lifecycle, item streaming, fork ephemeral, legacy aliases) |
| 2.2 | `tests/integration/test_transports.py` | ~6 (stdio, unix socket, websocket, auth token, overload -32001, sticky routing) |
| 2.3 | `tests/integration/test_turn_steer.py` | ~3 (steer mid-turn, multiple steers batched, steer after completion fails) |
| 3.1 | `tests/unit/test_memory_fs.py` | ~10 (index 200-line cap, pointer line 150-char cap, topic frontmatter, daily log append, grep_logs, git root hashing, worktree consistency, slug sanitization, deprecated migration path) |
| 3.2 | `tests/unit/test_session_notes.py` | ~5 (activation threshold, update interval, tool call gate, Path A vs B selection, subagent budget) |
| 3.3 | `tests/integration/test_verify_before_use.py` | ~2 (model re-reads file before relying on memory; updates topic file when memory contradicts reality) — these are LLM-eval tests, expect flakiness |
| 4.1 | `tests/integration/test_kairos.py` | ~6 (tick injection, sleep tool delay, blocking budget enforcement, anti-narration detection, terminal focus pause, batched ticks) |
| 4.2 | `tests/integration/test_ephemeral_fork.py` | ~3 (fork inherits history, ephemeral has null path, fork doesn't pollute parent) |
| 4.3 | `tests/integration/test_sticky_env.py` | ~4 (cwd persists, env vars persist, background process cleanup, shell crash recovery) |
| 4.4 | `tests/integration/test_headless_json.py` | ~5 (one JSON per line, schema validation, reasoning_tokens reported, exit codes, schema generation) |

### Integration test fixtures — recorded LLM responses

For Tier 1.1 (cache verification) and any LLM-touching test, use VCR-style cassette fixtures. Already in use elsewhere in repo. Add fixtures under `tests/fixtures/cassettes/`.

For Tier 1.1 specifically: record one cassette that has `cache_creation_input_tokens > 0` and one with `cache_read_input_tokens > 0`. Replay against the provider to verify metric capture.

### TUI rendering tests — programmatic state

Already proven pattern: render TUI state in a Rust test, snapshot the buffer output, compare. Used for view tests across the rtui codebase. Apply same pattern for:

- New `Picker(Approval)` or palette items added by Tier 2.1
- Status bar cache hit indicator added by Tier 1.3
- Side pane for ephemeral fork (Tier 4.2)

### Acceptance test budget

Set CI budget cap: `pytest tests/` should complete in < 5 min. Currently ~3 min for 1955 tests. Each tier adds tests but also some can move from sleep-based to mock-based.

---

## Telemetry and observability

### What to log per tier

| Tier | Metric | Why |
|---|---|---|
| 1.1 | cache_hit_ratio (read_tokens / prompt_tokens) | Verify cache is firing; alert if drops below 0.5 after warmup |
| 1.1 | cache_write_premium_paid (write_tokens × 0.25 × input_price) | Track the cost of cache misses |
| 1.3 | cost_savings_per_session (would-be cost - actual cost) | Justify the work to user / management |
| 2.1 | turn_completion_latency_p50/p95 | Detect regressions from Item refactor |
| 2.1 | item_kind_distribution | Understand what items are most common |
| 2.2 | transport_connection_count by transport type | See which transports are actually used |
| 2.2 | overload_rejection_count | Tune queue depth |
| 3.1 | memory_index_line_count | Should stay ≤ 200 |
| 3.1 | topic_file_count | Growth rate signal |
| 3.1 | grep_logs_query_count | Track usage of layer 3 |
| 3.2 | compaction_path_a_ratio | Goal: > 80% after activation threshold |
| 3.2 | session_notes_subagent_cost | Should be small relative to main turn cost |
| 4.1 | tick_count, sleep_call_ratio, anti_narration_violations | Safety telemetry for KAIROS |
| 4.1 | kairos_action_blast_radius (files changed during proactive runs) | Alert if KAIROS is going wild |

### Logging destination

- Per-session logs: append to `~/.autocode/sessions/<id>/events.jsonl`
- Daily aggregates: `~/.autocode/telemetry/<YYYY-MM-DD>.jsonl`
- `/cost` slash command pulls from session log
- `autocode telemetry summary --last 7d` reads aggregates (new CLI subcommand)

### Privacy

Telemetry is local only — never sent off-machine. Document this in README. Provide `autocode telemetry purge` to clear all of it.

---

## Migration safety

### Tier 1.x — fully backward-compatible

No data format changes. New fields added to `TokenUsage` default to 0. No migration needed.

### Tier 2.1 — major migration

Adds `items`, `turns` tables; alters `sessions` table with 5 new columns. Migration script:

```python
# scripts/migrate_to_app_server_v2.py

import sqlite3
from pathlib import Path

def migrate(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Idempotent: check if already migrated
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
    if cur.fetchone():
        print("Already migrated.")
        return

    # 1. Add new columns to sessions (idempotent via ALTER TABLE IF NOT EXISTS hack)
    for col, ddl in [
        ("ephemeral", "INTEGER DEFAULT 0"),
        ("archived", "INTEGER DEFAULT 0"),
        ("permission_profile", "TEXT DEFAULT 'default'"),
        ("git_info_json", "TEXT"),
        ("turn_count", "INTEGER DEFAULT 0"),
    ]:
        try:
            cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} {ddl}")
        except sqlite3.OperationalError:
            pass  # column exists

    # 2. Create new tables
    cur.executescript("""
        CREATE TABLE items (
            id TEXT PRIMARY KEY,
            turn_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX idx_items_turn ON items(turn_id);
        CREATE INDEX idx_items_thread ON items(thread_id);

        CREATE TABLE turns (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            interrupted INTEGER DEFAULT 0,
            interruption_reason TEXT
        );
        CREATE INDEX idx_turns_thread ON turns(thread_id);
    """)

    # 3. Best-effort: convert existing messages → items grouped by user-message boundary
    cur.execute("SELECT id FROM sessions")
    for (session_id,) in cur.fetchall():
        _convert_messages_to_items_and_turns(conn, session_id)

    conn.commit()
    print(f"Migrated {db_path}")
```

This runs once on first launch of v0.4.0. Idempotent — safe to re-run. Backup the SQLite file before migration: `~/.autocode/sessions.db.backup-<date>`.

### Tier 3.1 — file system migration

Existing memories in `MemoryStore` SQLite table get exported to topic files:

```python
# scripts/migrate_memory_to_fs.py

CATEGORY_TO_TOPIC = {
    "tool_pattern": "tool-patterns",
    "user_preference": "preferences",
    "project_fact": "facts",
    "error_resolution": "debugging",
}

def migrate(memory_store: MemoryStore, memory_fs: MemoryFS) -> None:
    by_topic: dict[str, list[str]] = {}
    for mem in memory_store.list_all():
        topic = CATEGORY_TO_TOPIC.get(mem["category"], "miscellany")
        by_topic.setdefault(topic, []).append(
            f"## {mem['created_at']}\n\n{mem['content']}"
        )

    for topic, entries in by_topic.items():
        content = f"# {topic.title()}\n\n" + "\n\n---\n\n".join(entries)
        memory_fs.write_topic(
            topic, content,
            summary=f"Migrated {len(entries)} entries from SQLite memory",
        )

    # Rename old table for safety, don't drop
    memory_store.archive_table()
```

User can roll back by reverting to v0.3.x and using `memories_archive_<date>` table.

### Tier 4.x — feature-flag rollout

Each Tier 4 feature defaults to off. Promote individually after monitoring:
- `AUTOCODE_FEATURE_KAIROS=true`
- `AUTOCODE_FEATURE_EPHEMERAL_FORK=true`
- `AUTOCODE_FEATURE_STICKY_ENV=true`
- `AUTOCODE_FEATURE_HEADLESS_JSON=true`

Gates checked at startup; flag flip requires restart. No mid-session toggling to avoid state inconsistencies.

---

## Rollback safety

### Per-tier rollback paths

| Tier | Rollback action |
|---|---|
| 1.1 | Disable cache injection: set `AUTOCODE_DISABLE_PROMPT_CACHE=true`. Provider falls back to non-cached. No data corruption risk. |
| 1.2 | Boundary marker is just a comment string; if something fails parsing, fall back to caching the entire system message (less optimal but still works). |
| 1.3 | Token tracker just shows zeros for new fields if not populated. |
| 2.1 | Major rollback: `autocode --legacy-rpc-v1` flag re-enables old method aliases without deprecation warnings. Items table is additive — old code ignores it. |
| 2.2 | Each transport optional. Stdio always works. If WebSocket has issues, fall back to stdio. |
| 2.3 | Steer is purely additive. Feature flag `AUTOCODE_DISABLE_TURN_STEER=true`. |
| 3.1 | Old SQLite memories_archive table preserved. Set `AUTOCODE_USE_LEGACY_MEMORY=true` to read from it instead. |
| 3.2 | Session Notes is additive; if subagent fails, compaction falls back to Path B (existing behavior). |
| 3.3 | Just system prompt text. Remove the section if it causes issues. |
| 4.x | Feature flags default off. Disable by setting flag to false. |

### Disaster recovery

`autocode session export <session_id>` writes a complete session to `<id>.jsonl`. `autocode session import <file>` reads it back. Use this to:
- Snapshot before risky migrations
- Move sessions between machines
- Debug specific sessions in isolation

---

## Performance budgets

| Operation | Budget | Why |
|---|---|---|
| `initialize` round trip | < 100 ms | Affects perceived startup latency |
| `thread/start` round trip | < 200 ms | New conversation feel |
| `turn/start` → first `item/started` | < 300 ms | "Did I press enter?" threshold |
| `item/agentMessage/delta` per chunk | < 50 ms intervals | Smooth streaming feel |
| Memory index load (Layer 1) | < 50 ms | Happens on every session start |
| Topic file load (Layer 2) | < 200 ms per file | Tool call cost |
| `grep_logs` over 30 days | < 500 ms | Tool call cost |
| Session Notes update (subagent) | < 30 sec | Background; user shouldn't notice |
| Compaction Path A | < 1 sec | Just a file read |
| Compaction Path B (LLM call) | < 30 sec | One API round trip |

If any budget is busted: alert in dev mode, log warning in prod, file an issue.

---

## Sequencing risks

### Risk: Tier 1.1 ships without 1.2

Cache breakpoint injection without the stable/dynamic boundary marker means the cache busts on every turn (because current date / git status / cwd change). User sees no cost reduction, concludes Tier 1 was a waste of time.

**Mitigation:** Ship 1.1 + 1.2 atomically as a single PR. Don't merge 1.1 alone.

### Risk: Tier 2.1 ships without legacy aliases working

Existing TUI breaks because old method names disappear.

**Mitigation:** PR for 2.1 includes alias mapping AND tests that exercise old method names AND emits deprecation warnings.

### Risk: Tier 3.1 migrates SQLite memories to files but agent still references old SQLite

Agent calls `memory_list` (legacy tool), gets stale data.

**Mitigation:** Either re-implement `memory_list` to read from MemoryFS, or remove it entirely with a deprecation cycle.

### Risk: Tier 4.1 KAIROS goes rogue while user is asleep

Agent makes destructive changes during overnight ticks.

**Mitigation:**
1. Default off (already planned)
2. Add `--dry-run` mode for first 2 weeks of opt-in
3. Hard cap: KAIROS can never call tools with `requires_approval=True` unless user is interactively present
4. Persist a "blast radius log" — every file touched by KAIROS, queryable via `autocode kairos audit`

### Risk: Schema generation (4.4) lags Item/Turn/Thread (2.1)

External clients written against schema break when 2.1 evolves.

**Mitigation:** Treat the JSON schema as a public API contract. Bump `protocol_version` field on every breaking change. Schema generation is part of CI; failing tests block merges.

---

## Documentation deliverables

Each tier needs:

1. **CHANGELOG.md entry** — user-visible changes
2. **`docs/reference/` page** — for tier 2.1 specifically: `rpc-schema-v2.md` matching Codex's app-server README format
3. **Migration guide** — for tiers 2.1 and 3.1
4. **Configuration docs** — for tier 4.x feature flags
5. **Telemetry guide** — what's logged where, how to read it

Don't skip docs. Future-you will be the person debugging this in 6 months.

---

## Cost vs benefit summary table

| Tier | Eng cost | User-visible benefit | Strategic benefit |
|---|---|---|---|
| 1.1 | 1 day | 40-80% LLM cost reduction | None (foundation) |
| 1.2 | 2 days | (none direct, makes 1.1 work) | Better prompt engineering hygiene |
| 1.3 | 1 day | `/cost` shows real numbers | Justifies further investment |
| 2.1 | 2 weeks | (none direct) | Multi-surface harness — biggest unlock |
| 2.2 | 2 days | "I can connect from another window" | Remote/IDE/web clients possible |
| 2.3 | 1 day | "I can steer the model mid-turn" | UX parity with Codex |
| 3.1 | 2 weeks | Better long-session quality | Match Claude Code memory |
| 3.2 | 1 week | Faster compaction, lower cost | Match Claude Code Path A |
| 3.3 | half day | Fewer hallucinations | Memory hygiene |
| 4.1 | 1 week | "Claude works while I'm away" | Match KAIROS |
| 4.2 | 1 day | "Quick second opinion" | Codex parity |
| 4.3 | 3 days | Persistent shell across calls | Codex parity |
| 4.4 | 2 days | CI/Slack/web automation | Codex parity for non-TUI |

**Best-bang-for-buck order:** 1.1 → 1.2 → 1.3 → 3.3 → 2.1 → 2.3 → 2.2 → 3.1 → 3.2 → 4.4 → 4.2 → 4.3 → 4.1

This is slightly different from the suggested execution order (00-INDEX.md) because 3.3 is so cheap and 2.3 is small enough to slot in early.

---

## Things I'd do differently if starting from scratch

These are caveats that might inform sequencing decisions:

1. **Memory before App Server.** Tier 3 doesn't depend on Tier 2 and the 3-layer memory delivers immediately visible quality. If user-perceived value matters more than client-surface diversity, swap order.

2. **Prompt cache could be a 2-day spike, not a week.** Most of the work in Tier 1 is the boundary refactor (1.2). If you want to test cache impact first without committing to the refactor, ship a minimal version of 1.1 that only caches the `STABLE_INSTRUCTIONS` constant — measure, then decide whether 1.2's cost is worth it.

3. **Item/Turn/Thread is a big bet.** If no second client is on the horizon, you're paying ~2 weeks of refactor for purely speculative future value. Defer if no concrete client surface is planned within 6 months.

4. **KAIROS won't ship cleanly without a strong observability story first.** Don't even start Tier 4.1 until telemetry from Tier 1.3 has been running long enough that anomaly detection works.
