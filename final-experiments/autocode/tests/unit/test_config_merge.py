"""Tests for safe config merge — never overwrite user config."""

from __future__ import annotations

import json
from pathlib import Path

from autocode.external.config_merge import (
    generate_claude_code_config,
    generate_codex_config,
    generate_opencode_config,
    merge_json_config,
    remove_managed_section,
)


def test_merge_new_file(tmp_path: Path) -> None:
    """Merge into non-existent file creates it."""
    config = tmp_path / "settings.json"
    merge_json_config(config, {"tools": ["search_code"]})

    assert config.exists()
    data = json.loads(config.read_text())
    assert "__managed_by_autocode" in data
    assert data["__managed_by_autocode"]["tools"] == ["search_code"]


def test_merge_preserves_user_config(tmp_path: Path) -> None:
    """Merge never overwrites existing user sections."""
    config = tmp_path / "settings.json"
    config.write_text(json.dumps({"user_setting": "keep_this", "theme": "dark"}))

    merge_json_config(config, {"mcp": "autocode"})

    data = json.loads(config.read_text())
    assert data["user_setting"] == "keep_this"
    assert data["theme"] == "dark"
    assert data["__managed_by_autocode"]["mcp"] == "autocode"


def test_merge_creates_backup(tmp_path: Path) -> None:
    """Merge creates backup of existing config."""
    config = tmp_path / "settings.json"
    config.write_text(json.dumps({"original": True}))
    backup_dir = tmp_path / "backups"

    merge_json_config(config, {"new": True}, backup_dir=backup_dir)

    backups = list(backup_dir.glob("*.bak"))
    assert len(backups) == 1


def test_remove_managed_section(tmp_path: Path) -> None:
    """Remove only AutoCode-managed sections."""
    config = tmp_path / "settings.json"
    data = {
        "user_setting": "keep",
        "__managed_by_autocode": {"mcp": "remove_this"},
    }
    config.write_text(json.dumps(data))

    removed = remove_managed_section(config)
    assert removed

    result = json.loads(config.read_text())
    assert "user_setting" in result
    assert "__managed_by_autocode" not in result


def test_remove_nothing_to_remove(tmp_path: Path) -> None:
    """Remove returns False when no managed section exists."""
    config = tmp_path / "clean.json"
    config.write_text(json.dumps({"user": "only"}))

    removed = remove_managed_section(config)
    assert not removed


def test_generate_claude_code_config(tmp_path: Path) -> None:
    """Claude Code config has MCP server entry."""
    config = generate_claude_code_config(tmp_path)
    assert "mcpServers" in config
    assert "autocode" in config["mcpServers"]
    assert config["mcpServers"]["autocode"]["command"] == "uv"


def test_generate_opencode_config(tmp_path: Path) -> None:
    """OpenCode config has MCP entry."""
    config = generate_opencode_config(tmp_path)
    assert "mcp" in config
    assert "autocode" in config["mcp"]


def test_generate_codex_config(tmp_path: Path) -> None:
    """Codex config has mcp_servers entry."""
    config = generate_codex_config(tmp_path)
    assert "mcp_servers" in config
    assert "autocode" in config["mcp_servers"]


def test_atomic_write_no_partial(tmp_path: Path) -> None:
    """Atomic write doesn't leave partial files."""
    config = tmp_path / "atomic.json"
    merge_json_config(config, {"data": "test"})

    # No .tmp files should remain
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
    assert config.exists()
