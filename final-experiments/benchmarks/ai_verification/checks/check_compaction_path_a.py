"""Deterministic proof that compaction Path A (Session Notes) works.

This script is designed to be invoked as a grading check command from
compaction-path-a.yaml.  It exercises the full Path A code path without
requiring a live LLM:

1. Create a SessionStore with enough messages to exceed compaction threshold.
2. Create a SessionNotes instance and seed it with deterministic content.
3. Construct a ContextEngine wired to the notes.
4. Call auto_compact().
5. Assert that Path A was chosen (compaction_event with path="A").
6. Assert that the compacted summary contains the seeded notes content.

Exit 0 = PASS, exit 1 = FAIL with diagnostics on stderr.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _setup_path() -> None:
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    src = _PROJECT_ROOT / "autocode" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def verify_path_a_compaction() -> list[str]:
    """Run the deterministic Path A proof and return a list of error strings.

    Returns an empty list on success.  Callers can inspect the list or
    convert to exit-code as needed.
    """
    _setup_path()

    from autocode.agent.context import ContextEngine
    from autocode.session.session_notes import SessionNotes
    from autocode.session.store import SessionStore

    errors: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        store = SessionStore(tmp_path / "sessions.db")
        session_id = store.create_session(
            title="compaction-path-a-check",
            model="test",
            provider="test",
            project_dir=str(tmp_path),
        )

        for idx in range(8):
            store.add_message(
                session_id,
                "user",
                f"message {idx} " + ("x" * 500),
                200,
            )

        notes = SessionNotes(session_id=session_id, base_dir=tmp_path)
        notes.update_from_text(
            "Decision: use Path A for compaction. Key fact: deterministic proof.",
            total_tokens=12_000,
        )

        events: list[dict[str, object]] = []
        engine = ContextEngine(
            provider=None,
            session_store=store,
            context_length=2000,
            compaction_threshold=0.1,
            session_notes=notes,
            telemetry_emit=lambda kind, payload: events.append({"kind": kind, **payload}),
        )

        import asyncio

        summary = asyncio.run(engine.auto_compact(session_id))

        compaction_events = [
            e for e in events
            if e.get("kind") == "compaction_event"
        ]

        if not compaction_events:
            errors.append("FAIL: no compaction_event emitted")
        else:
            path_val = compaction_events[0].get("path")
            if path_val != "A":
                errors.append(f"FAIL: expected path='A', got path={path_val!r}")

        if "deterministic proof" not in summary:
            errors.append(
                f"FAIL: summary does not contain seeded notes content. "
                f"summary={summary!r}"
            )

        remaining = store.get_messages(session_id)
        if not remaining:
            errors.append("FAIL: no messages remain after compaction")
        elif remaining[0].content != summary:
            errors.append(
                f"FAIL: first message is not the summary. "
                f"got: {remaining[0].content!r}"
            )

        store.close()

    return errors


def run_check() -> None:
    errors = verify_path_a_compaction()
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    print("PASS: Path A compaction deterministic proof succeeded")
    sys.exit(0)


if __name__ == "__main__":
    run_check()
