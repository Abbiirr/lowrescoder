from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest

from autocode.agent.tools import create_default_registry
from autocode.backend.services import build_memory_list_payload
from autocode.session.memory_fs import MemoryFS
from autocode.session.memory_migration import migrate_sqlite_memories


def test_index_truncates_to_200_lines_and_150_char_pointer_lines(tmp_path: Path) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")
    oversized = "\n".join(f"- Recent {idx}: {'x' * 240}" for idx in range(500))

    truncated = memory._truncate_index(oversized)

    lines = truncated.splitlines()
    assert len(lines) <= 200
    assert all(len(line) <= 150 for line in lines)


def test_topic_write_adds_required_frontmatter_and_index_pointer(tmp_path: Path) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")

    result = memory.write_topic(
        "Release Notes",
        "Backend migration status is green.",
        summary="Release state",
    )

    assert result.warning is None
    topic = memory.read_topic("release-notes")
    assert "topic: release-notes" in topic
    assert "type: topic" in topic
    assert "created:" in topic
    assert "updated:" in topic
    assert "size_lines:" in topic
    assert "Backend migration status is green." in topic
    assert "memory/release-notes.md" in memory.read_index()
    assert "Backend migration status" not in memory.read_index()


def test_topic_soft_cap_warns_and_recommends_split(tmp_path: Path) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")
    body = "\n".join(f"line {idx}" for idx in range(1005))

    result = memory.write_topic("Large Topic", body)

    assert result.warning is not None
    assert "1000-line soft cap" in result.warning
    assert "large-topic-" in result.warning


def test_daily_log_appends_and_grep_finds_recent_match(tmp_path: Path) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")

    memory.append_log(
        "sess-1",
        {
            "model": "m",
            "provider": "p",
            "goal": "ship memory",
            "done": ["MemoryFS implemented"],
            "decisions": ["use files"],
            "open_threads": [],
            "stats": {"tokens": 10},
        },
    )
    memory.append_log("sess-2", {"goal": "second block", "decisions": ["grep token"]})

    log_files = list((tmp_path / "state" / "logs").glob("*/*/*.md"))
    assert len(log_files) == 1
    assert log_files[0].read_text(encoding="utf-8").count("session_id:") == 2
    matches = memory.grep_logs("grep token", days=30)
    assert matches and matches[0].session_id == "sess-2"


def test_git_root_hash_is_stable_across_worktrees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    linked = tmp_path / "repo-linked"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "a@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=repo, check=True)
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "worktree", "add", str(linked)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    assert MemoryFS(project_root=repo)._project_hash == MemoryFS(project_root=linked)._project_hash


def test_default_registry_exposes_memory_tools(tmp_path: Path) -> None:
    registry = create_default_registry(project_root=str(tmp_path))

    for name in (
        "memory_read_topic",
        "memory_write_topic",
        "memory_grep_logs",
        "memory_index_show",
    ):
        assert registry.get(name) is not None

    write_result = registry.get("memory_write_topic").handler(
        slug="facts",
        content="Known fact",
        summary="Fact pointer",
    )
    assert "memory/facts.md" in write_result
    assert "Known fact" in registry.get("memory_read_topic").handler(slug="facts")
    assert "Fact pointer" in registry.get("memory_index_show").handler()


def test_memory_list_legacy_payload_reads_memory_fs_topics(tmp_path: Path) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")
    memory.write_topic("facts", "Fact body", summary="Fact summary")

    payload = build_memory_list_payload(memory)

    assert payload["memories"] == [
        {
            "id": "facts",
            "category": "topic",
            "content": "Fact summary",
            "relevance": 1.0,
        }
    ]


def test_migration_groups_sqlite_memories_and_archives_table(tmp_path: Path) -> None:
    db = tmp_path / "sessions.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE memories ("
        "id TEXT, session_id TEXT, project_id TEXT, category TEXT, content TEXT, "
        "relevance REAL, created_at TEXT, updated_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO memories VALUES (?, 's', 'p', ?, ?, 1.0, '2026-01-01', '2026-01-01')",
        [
            ("1", "tool_pattern", "Use rg for search"),
            ("2", "user_preference", "Prefer concise updates"),
            ("3", "project_fact", "Backend is Python"),
            ("4", "error_resolution", "Timeout fixed by retry"),
        ],
    )
    conn.commit()
    conn.close()
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")

    result = migrate_sqlite_memories(db, memory, archive_date="20260501")
    second = migrate_sqlite_memories(db, memory, archive_date="20260501")

    assert result.migrated_count == 4
    assert second.migrated_count == 0
    assert "Use rg for search" in memory.read_topic("patterns")
    assert "Prefer concise updates" in memory.read_topic("preferences")
    assert "Backend is Python" in memory.read_topic("facts")
    assert "Timeout fixed by retry" in memory.read_topic("debugging")
    conn = sqlite3.connect(db)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "memories_archive_20260501" in tables
    assert "memories" not in tables
    conn.close()


def test_index_stays_under_200_lines_after_50_simulated_sessions(
    tmp_path: Path,
) -> None:
    memory = MemoryFS(project_root=tmp_path, base_dir=tmp_path / "state")

    for idx in range(50):
        memory.write_topic(
            f"topic-{idx}",
            f"Content for topic {idx} with some detail.",
            summary=f"Topic {idx} summary",
        )

    index_text = memory.read_index()
    assert len(index_text.splitlines()) <= 200, (
        f"Index has {len(index_text.splitlines())} lines after 50 sessions"
    )


@pytest.mark.asyncio
async def test_path_a_chosen_in_majority_of_compaction_events(
    tmp_path: Path,
) -> None:
    from autocode.agent.context import ContextEngine
    from autocode.session.session_notes import ACTIVATION_TOKENS, SessionNotes
    from autocode.session.store import SessionStore

    path_a_count = 0
    path_b_count = 0
    total_runs = 10

    for _ in range(total_runs):
        store = SessionStore(tmp_path / f"sessions_{_}.db")
        session_id = store.create_session(
            "compaction-test", "m", "p", str(tmp_path)
        )
        for idx in range(8):
            store.add_message(
                session_id, "user", f"msg {idx} " + ("x" * 500), 200
            )

        notes = SessionNotes(
            session_id=session_id, base_dir=tmp_path / f"notes_{_}"
        )
        notes.update_from_text(
            "Path A deterministic summary content.",
            total_tokens=ACTIVATION_TOKENS,
        )

        events: list[dict[str, object]] = []
        engine = ContextEngine(
            provider=None,
            session_store=store,
            context_length=2000,
            compaction_threshold=0.1,
            session_notes=notes,
            telemetry_emit=lambda kind, payload: events.append(
                {"kind": kind, **payload}
            ),
        )

        await engine.auto_compact(session_id)

        compaction_events = [
            e for e in events if e.get("kind") == "compaction_event"
        ]
        if compaction_events and compaction_events[0].get("path") == "A":
            path_a_count += 1
        else:
            path_b_count += 1

        store.close()

    ratio = path_a_count / total_runs
    assert ratio >= 0.8, (
        f"Path A chosen in {path_a_count}/{total_runs} = {ratio:.0%}, expected >= 80%"
    )
