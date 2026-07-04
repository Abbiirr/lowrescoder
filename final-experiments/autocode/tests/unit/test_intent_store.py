from __future__ import annotations

from pathlib import Path

from autocode.session.intent_store import IntentStore


def test_capture_creates_persistent_sqlite_row(tmp_path: Path) -> None:
    store = IntentStore(tmp_path / "sessions.db")

    intent = store.capture(
        "session-1",
        "Refactor the backend transport layer without breaking attach mode.",
        extractor=lambda message: {
            "original_goal": message,
            "success_criteria": ["transport tests pass", "attach mode preserved"],
            "constraints": ["no git commits", "do not touch TUI visuals"],
            "progress_so_far": ["read current transport files"],
        },
    )

    loaded = store.get("session-1")
    assert loaded is not None
    assert loaded == intent
    assert loaded.session_id == "session-1"
    assert (
        loaded.original_goal
        == "Refactor the backend transport layer without breaking attach mode."
    )
    assert loaded.success_criteria == ["transport tests pass", "attach mode preserved"]
    assert loaded.constraints == ["no git commits", "do not touch TUI visuals"]
    assert loaded.progress_so_far == ["read current transport files"]
    assert loaded.captured_at


def test_intent_persists_across_simulated_session_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "sessions.db"
    first = IntentStore(db_path)
    first.capture(
        "session-2",
        "Migrate memory storage.",
        extractor=lambda _message: {
            "success_criteria": ["MemoryFS loads on restart"],
            "constraints": ["preserve legacy rollback"],
        },
    )
    first.close()

    second = IntentStore(db_path)
    loaded = second.get("session-2")

    assert loaded is not None
    assert loaded.original_goal == "Migrate memory storage."
    assert loaded.success_criteria == ["MemoryFS loads on restart"]
    assert loaded.constraints == ["preserve legacy rollback"]


def test_progress_so_far_appends_and_never_overwrites(tmp_path: Path) -> None:
    store = IntentStore(tmp_path / "sessions.db")
    intent = store.capture(
        "session-3",
        "Implement Ralph recovery.",
        extractor=lambda _message: {
            "success_criteria": ["recovery message injected"],
            "progress_so_far": ["captured initial intent"],
        },
    )

    intent.progress_so_far = ["first recovery attempt", "second recovery attempt"]
    store.update(intent)
    store.append_progress("session-3", "third recovery attempt")

    loaded = store.get("session-3")
    assert loaded is not None
    assert loaded.progress_so_far == [
        "captured initial intent",
        "first recovery attempt",
        "second recovery attempt",
        "third recovery attempt",
    ]
