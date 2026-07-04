"""Tests for the schema migration subsystem."""

from __future__ import annotations

import sqlite3

import pytest

from autocode.session.migrations import (
    get_schema_version,
    run_migrations,
)
from autocode.session.models import ensure_tables


@pytest.fixture()
def conn():
    """In-memory SQLite connection with base DDL applied."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


def test_schema_version_table_exists(conn: sqlite3.Connection) -> None:
    """ensure_tables creates the schema_version table."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'",
    )
    assert cursor.fetchone() is not None


def test_initial_version_is_zero() -> None:
    """Fresh database with only base DDL (no ensure_tables) starts at version 0."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    # Only apply the base DDL without migrations
    from autocode.session.models import DDL
    db.executescript(DDL)
    assert get_schema_version(db) == 0


def test_run_migrations_advances_version(conn: sqlite3.Connection) -> None:
    """run_migrations applies all pending migrations and returns final version."""
    final = run_migrations(conn)
    assert final > 0
    assert get_schema_version(conn) == final


def test_run_migrations_is_idempotent(conn: sqlite3.Connection) -> None:
    """Running migrations twice yields the same version, no errors."""
    v1 = run_migrations(conn)
    v2 = run_migrations(conn)
    assert v1 == v2


def test_migrations_apply_in_order(conn: sqlite3.Connection) -> None:
    """Each migration's version is recorded in ascending order."""
    run_migrations(conn)
    cursor = conn.execute(
        "SELECT version FROM schema_version ORDER BY version ASC",
    )
    versions = [row[0] for row in cursor.fetchall()]
    assert versions == sorted(versions)
    assert len(versions) > 0


def test_partial_migration_resumes() -> None:
    """If only some migrations ran, run_migrations picks up where it left off."""
    from autocode.session.migrations import MIGRATIONS
    from autocode.session.models import DDL

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    # Apply only base DDL (creates schema_version table but no migrations)
    db.executescript(DDL)

    if len(MIGRATIONS) >= 1:
        version, _desc, func = MIGRATIONS[0]
        func(db)
        db.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
        db.commit()
        assert get_schema_version(db) == version

        # Now run_migrations should skip version 1 and apply the rest
        final = run_migrations(db)
        assert final >= version


def test_get_schema_version_no_table() -> None:
    """get_schema_version returns 0 if schema_version table doesn't exist."""
    db = sqlite3.connect(":memory:")
    assert get_schema_version(db) == 0


def test_migration_creates_expected_tables(conn: sqlite3.Connection) -> None:
    """After all migrations, expected tables exist."""
    run_migrations(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
    )
    tables = {row[0] for row in cursor.fetchall()}
    # v1 should create orchestrator_events
    assert "orchestrator_events" in tables
