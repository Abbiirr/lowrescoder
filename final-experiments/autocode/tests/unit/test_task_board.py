"""Tests for task board semantics — claim/release/escalate/artifacts/history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from autocode.session.models import TaskArtifactRow, TaskStatusHistoryRow, ensure_tables
from autocode.session.task_store import TaskStore


@pytest.fixture()
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ensure_tables(db)
    return db


@pytest.fixture()
def store(conn: sqlite3.Connection) -> TaskStore:
    return TaskStore(conn, session_id="test-session")


# ── Claim ──


class TestTaskClaim:
    def test_claim_pending_task(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        assert store.claim_task(tid, "worker-1")

    def test_claim_sets_owner_and_lease(self, store: TaskStore, conn: sqlite3.Connection) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1", lease_seconds=300)

        cursor = conn.execute(
            "SELECT owner_agent, claimed_at, lease_expires_at, status FROM tasks WHERE id = ?",
            (tid,),
        )
        row = cursor.fetchone()
        assert row["owner_agent"] == "worker-1"
        assert row["claimed_at"] is not None
        assert row["lease_expires_at"] is not None
        assert row["status"] == "in_progress"

    def test_claim_already_claimed_fails(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        assert not store.claim_task(tid, "worker-2")

    def test_claim_completed_task_fails(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.complete_task(tid, "worker-1")
        assert not store.claim_task(tid, "worker-2")

    def test_claim_blocked_task_fails(self, store: TaskStore) -> None:
        t1 = store.create_task("First")
        t2 = store.create_task("Second")
        store.add_dependency(t2, t1)
        # t2 is blocked by t1
        assert not store.claim_task(t2, "worker-1")


# ── Release ──


class TestTaskRelease:
    def test_release_claimed_task(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.release_task(tid, "worker-1")
        task = store.get_task(tid)
        assert task.status == "pending"
        assert task.owner_agent == ""

    def test_release_by_wrong_agent_fails(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        with pytest.raises(ValueError, match="not owned"):
            store.release_task(tid, "worker-2")


# ── Complete / Fail ──


class TestTaskComplete:
    def test_complete_claimed_task(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.complete_task(tid, "worker-1")
        assert store.get_task(tid).status == "completed"

    def test_complete_records_history(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.complete_task(tid, "worker-1", reason="All tests pass")
        history = store.get_status_history(tid)
        # Should have: pending→in_progress (claim), in_progress→completed
        statuses = [(h.old_status, h.new_status) for h in history]
        assert ("pending", "in_progress") in statuses
        assert ("in_progress", "completed") in statuses


class TestTaskFail:
    def test_fail_task_records_history(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.fail_task(tid, "worker-1", reason="Tests failed")
        task = store.get_task(tid)
        assert task.status == "failed"
        history = store.get_status_history(tid)
        assert any(h.new_status == "failed" for h in history)


# ── Escalate ──


class TestTaskEscalate:
    def test_escalate_releases_and_marks(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.escalate_task(tid, "worker-1", reason="Too complex")
        task = store.get_task(tid)
        assert task.status == "escalated"
        assert task.owner_agent == ""


# ── Artifacts ──


class TestTaskArtifacts:
    def test_add_artifact(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        aid = store.add_artifact(tid, "file", path="/tmp/fix.py", content_hash="abc123")
        assert aid > 0

    def test_get_artifacts(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.add_artifact(tid, "file", path="/tmp/a.py")
        store.add_artifact(tid, "log", path="/tmp/test.log")
        arts = store.get_artifacts(tid)
        assert len(arts) == 2
        assert arts[0].artifact_type == "file"

    def test_multiple_artifacts_per_task(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        for i in range(5):
            store.add_artifact(tid, "patch", path=f"/tmp/patch-{i}.diff")
        assert len(store.get_artifacts(tid)) == 5


# ── Status History ──


class TestTaskStatusHistory:
    def test_history_recorded_on_claim(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        history = store.get_status_history(tid)
        assert len(history) >= 1
        assert history[0].old_status == "pending"
        assert history[0].new_status == "in_progress"
        assert history[0].changed_by == "worker-1"

    def test_get_full_history(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1")
        store.release_task(tid, "worker-1")
        store.claim_task(tid, "worker-2")
        store.complete_task(tid, "worker-2")
        history = store.get_status_history(tid)
        assert len(history) == 4  # pending→ip, ip→pending, pending→ip, ip→completed


# ── Lease Expiry ──


class TestLeaseExpiry:
    def test_release_expired_claims(self, store: TaskStore, conn: sqlite3.Connection) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1", lease_seconds=1)

        # Set lease to past
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute(
            "UPDATE tasks SET lease_expires_at = ? WHERE id = ?", (past, tid),
        )
        conn.commit()

        released = store.release_expired_claims()
        assert released == 1
        task = store.get_task(tid)
        assert task.status == "pending"
        assert task.owner_agent == ""

    def test_unexpired_claims_not_released(self, store: TaskStore) -> None:
        tid = store.create_task("Fix bug")
        store.claim_task(tid, "worker-1", lease_seconds=3600)
        assert store.release_expired_claims() == 0


# ── Claimable Tasks ──


class TestGetClaimable:
    def test_claimable_excludes_claimed(self, store: TaskStore) -> None:
        t1 = store.create_task("Task 1")
        t2 = store.create_task("Task 2")
        store.claim_task(t1, "worker-1")
        claimable = store.get_claimable_tasks()
        ids = [t.id for t in claimable]
        assert t1 not in ids
        assert t2 in ids

    def test_claimable_excludes_completed(self, store: TaskStore) -> None:
        t1 = store.create_task("Task 1")
        store.claim_task(t1, "worker-1")
        store.complete_task(t1, "worker-1")
        claimable = store.get_claimable_tasks()
        assert all(t.id != t1 for t in claimable)


# ── Restart / Recovery ──


class TestRestartRecovery:
    def test_claims_survive_reconnect(self) -> None:
        import os, tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn1 = sqlite3.connect(db_path)
            conn1.row_factory = sqlite3.Row
            ensure_tables(conn1)
            s1 = TaskStore(conn1, "s1")
            tid = s1.create_task("Fix bug")
            s1.claim_task(tid, "worker-1")
            conn1.close()

            conn2 = sqlite3.connect(db_path)
            conn2.row_factory = sqlite3.Row
            ensure_tables(conn2)
            s2 = TaskStore(conn2, "s1")
            task = s2.get_task(tid)
            assert task.owner_agent == "worker-1"
            assert task.status == "in_progress"
            conn2.close()
        finally:
            os.unlink(db_path)
