"""Scratch-store tests for large tool-output offload."""

from __future__ import annotations

import json


def test_small_output_inlined_unchanged(tmp_path) -> None:
    from autocode.agent.scratch import ScratchStore

    store = ScratchStore(tmp_path, thread_id="thread-a")

    result = store.offload_if_large("list_files", {"path": "."}, "small", turn_id="turn-001")

    assert result == "small"
    assert not (tmp_path / "thread-a").exists()


def test_large_output_offloaded_with_stub_manifest_and_preview(tmp_path) -> None:
    from autocode.agent.scratch import ScratchStore

    store = ScratchStore(tmp_path, thread_id="thread-a")
    large = "\n".join(f"file-{i}.py" for i in range(1000))

    stub = store.offload_if_large("list_files", {"path": "src"}, large, turn_id="turn-001")

    assert "[Tool output offloaded" in stub
    assert "bytes saved to" in stub
    assert "Summary:" in stub
    assert "First 5 lines" in stub
    assert "file-0.py" in stub
    assert "file-5.py" not in stub
    manifest_path = tmp_path / "thread-a" / "turn-001" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["offloads"][0]["tool_name"] == "list_files"
    assert manifest["offloads"][0]["result_bytes"] == len(large.encode())
    assert manifest["offloads"][0]["summary"].startswith("1000 entries in src")
    scratch_path = manifest["offloads"][0]["path"]
    assert "file-999.py" in open(scratch_path, encoding="utf-8").read()


def test_cleanup_keeps_last_n_turn_dirs(tmp_path) -> None:
    from autocode.agent.scratch import ScratchStore

    store = ScratchStore(tmp_path, thread_id="thread-a")
    large = "x" * 6000
    for idx in range(12):
        store.offload_if_large("large_tool", {}, large, turn_id=f"turn-{idx:03d}")

    store.cleanup_after_n_turns(current_turn_count=12, keep_n=10)

    turns = sorted(path.name for path in (tmp_path / "thread-a").iterdir())
    assert turns == [f"turn-{idx:03d}" for idx in range(2, 12)]


def test_never_and_always_tool_rules(tmp_path) -> None:
    from autocode.agent.scratch import ScratchStore

    store = ScratchStore(tmp_path, thread_id="thread-a")

    never = store.offload_if_large("todo_read", {}, "x" * 50_000, turn_id="turn-001")
    always = store.offload_if_large("git_log", {}, "short output", turn_id="turn-001")

    assert never == "x" * 50_000
    assert "[Tool output offloaded" in always


def test_per_turn_dir_isolation(tmp_path) -> None:
    from autocode.agent.scratch import ScratchStore

    store = ScratchStore(tmp_path, thread_id="thread-a")

    first = store.offload_if_large("web_fetch", {"url": "https://a.test"}, "a", turn_id="turn-001")
    second = store.offload_if_large("web_fetch", {"url": "https://b.test"}, "b", turn_id="turn-002")

    assert "turn-001" in first
    assert "turn-002" in second
    assert (tmp_path / "thread-a" / "turn-001" / "manifest.json").exists()
    assert (tmp_path / "thread-a" / "turn-002" / "manifest.json").exists()


def test_disable_env_inlines_all_outputs(tmp_path, monkeypatch) -> None:
    from autocode.agent.scratch import ScratchStore

    monkeypatch.setenv("AUTOCODE_DISABLE_SCRATCH", "true")
    store = ScratchStore(tmp_path, thread_id="thread-a")

    result = store.offload_if_large("web_fetch", {}, "x" * 50_000, turn_id="turn-001")

    assert result == "x" * 50_000
    assert not (tmp_path / "thread-a").exists()
