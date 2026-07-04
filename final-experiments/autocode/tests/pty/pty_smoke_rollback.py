#!/usr/bin/env python3
"""Smoke coverage for rollback command flows backed by real session storage.

Run: python3 autocode/tests/pty/pty_smoke_rollback.py

This smoke uses the same slash-command handler that the Python backend exposes
to frontends, with a real SQLite session DB and real local file snapshots.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_AUTOCODE_ROOT / "src"))

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    if os.environ.get("AUTOCODE_ROLLBACK_SMOKE_UV") != "1":
        os.environ["AUTOCODE_ROLLBACK_SMOKE_UV"] = "1"
        os.execvp("uv", ["uv", "run", "python3", str(Path(__file__).resolve())])
    raise

from autocode.app.commands import _handle_rollback  # noqa: E402
from autocode.session.checkpoint_store import CheckpointStore  # noqa: E402
from autocode.session.file_snapshot import snapshot_files  # noqa: E402
from autocode.session.store import SessionStore  # noqa: E402
from autocode.session.task_store import TaskStore  # noqa: E402

ARTIFACT_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"


class FakeApp(SimpleNamespace):
    """Minimal app surface required by the slash-command handler."""

    def add_system_message(self, message: str) -> None:
        self.messages.append(message)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _assert_last_message(app: FakeApp, needle: str) -> None:
    if not app.messages:
        raise AssertionError(f"expected message containing {needle!r}, got none")
    if needle not in app.messages[-1]:
        raise AssertionError(
            f"expected message containing {needle!r}, got:\n{app.messages[-1]}"
        )


async def _run_smoke(tmp: Path) -> list[str]:
    original_home = os.environ.get("HOME")
    home = tmp / "home"
    project_root = tmp / "project"
    home.mkdir()
    project_root.mkdir()
    os.environ["HOME"] = str(home)

    session_store = SessionStore(tmp / "sessions.sqlite")
    session_id = session_store.create_session(
        title="rollback smoke",
        model="test-model",
        provider="test-provider",
        project_dir=str(project_root),
    )
    app = FakeApp(
        session_store=session_store,
        session_id=session_id,
        project_root=project_root,
        messages=[],
    )

    try:
        target = project_root / "sample.txt"
        target.write_text("before\n", encoding="utf-8")

        tool_call_id = "tool-smoke-001"
        snap_dir = home / ".autocode" / "snapshots" / session_id / tool_call_id
        copied = snapshot_files(project_root, snap_dir, ["sample.txt"])
        if copied != ["sample.txt"]:
            raise AssertionError(f"snapshot did not copy sample.txt: {copied!r}")

        target.write_text("after\n", encoding="utf-8")

        conn = session_store.get_connection()
        task_store = TaskStore(conn, session_id)
        checkpoint_store = CheckpointStore(conn, session_id)
        checkpoint_id = checkpoint_store.save_per_tool_checkpoint(
            task_store,
            tool_call_id=tool_call_id,
            tool_name="write_file",
            tool_call_idx=1,
            kind="pre_tool",
            files_touched=["sample.txt"],
            label="pre write_file sample.txt",
            session_store=session_store,
        )

        await _handle_rollback(app, "")
        _assert_last_message(app, "Per-tool checkpoints")
        _assert_last_message(app, checkpoint_id)

        await _handle_rollback(app, checkpoint_id)
        _assert_last_message(app, "Rollback preview")
        _assert_last_message(app, f"/rollback restore {checkpoint_id}")
        if target.read_text(encoding="utf-8") != "after\n":
            raise AssertionError("/rollback <id> restored without explicit confirmation")

        await _handle_rollback(app, "--last")
        _assert_last_message(app, "Rollback preview")
        _assert_last_message(app, f"/rollback restore {checkpoint_id}")
        if target.read_text(encoding="utf-8") != "after\n":
            raise AssertionError("/rollback --last restored without explicit confirmation")

        await _handle_rollback(app, f"restore {checkpoint_id}")
        _assert_last_message(app, "Rolled back to checkpoint")
        if target.read_text(encoding="utf-8") != "before\n":
            raise AssertionError("/rollback restore <id> did not restore file snapshot")

        return [
            f"checkpoint_id={checkpoint_id}",
            "/rollback listed per-tool checkpoints",
            "/rollback <id> previewed without restore",
            "/rollback --last previewed without restore",
            "/rollback restore <id> restored the file snapshot",
        ]
    finally:
        session_store.close()
        if original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = original_home


async def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / f"{_timestamp()}-pty-smoke-rollback.md"
    try:
        with tempfile.TemporaryDirectory(prefix="autocode-rollback-smoke-") as raw:
            evidence = await _run_smoke(Path(raw))
    except Exception as exc:
        artifact.write_text(
            "# Rollback PTY Smoke\n\n"
            "Status: FAIL\n\n"
            f"Error: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        print(f"[FAIL] rollback smoke: {type(exc).__name__}: {exc}")
        print(f"Artifact: {artifact}")
        return 1

    artifact.write_text(
        "# Rollback PTY Smoke\n\n"
        "Status: PASS\n\n"
        "Scope: real slash-command handler, real SQLite session DB, "
        "real per-tool checkpoint row, real local file snapshot restore.\n\n"
        "Evidence:\n"
        + "\n".join(f"- {line}" for line in evidence)
        + "\n",
        encoding="utf-8",
    )
    print("[PASS] rollback smoke")
    print(f"Artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
