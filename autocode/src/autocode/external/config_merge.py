"""Safe config merge generator for external tool integration.

Generates tool-specific configs with `# managed-by: autocode` markers.
NEVER overwrites user config — deep merge with atomic writes.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANAGED_MARKER = "# managed-by: autocode"
MANAGED_JSON_KEY = "__managed_by_autocode"


def _backup_config(config_path: Path, backup_dir: Path) -> Path | None:
    """Create a timestamped backup of a config file."""
    if not config_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"{config_path.name}.{ts}.bak"
    shutil.copy2(config_path, backup)
    return backup


def _atomic_write(path: Path, content: str) -> None:
    """Write-temp-rename for atomic file updates."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def merge_json_config(
    config_path: Path,
    autocode_section: dict[str, Any],
    backup_dir: Path | None = None,
) -> Path:
    """Merge AutoCode section into a JSON config file.

    - Creates backup before modifying
    - Adds __managed_by_autocode marker
    - Uses atomic write
    - Never overwrites non-AutoCode sections
    """
    backup = backup_dir or config_path.parent / ".autocode" / "backups"

    if config_path.exists():
        _backup_config(config_path, backup)
        existing = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        existing = {}

    # Remove old managed section
    existing.pop(MANAGED_JSON_KEY, None)

    # Merge new section
    existing[MANAGED_JSON_KEY] = autocode_section

    _atomic_write(config_path, json.dumps(existing, indent=2) + "\n")
    return config_path


def remove_managed_section(config_path: Path) -> bool:
    """Remove AutoCode-managed sections from a config file.

    Only removes sections with the managed marker.
    Returns True if changes were made.
    """
    if not config_path.exists():
        return False

    content = config_path.read_text(encoding="utf-8")

    # JSON files
    if config_path.suffix == ".json":
        try:
            data = json.loads(content)
            if MANAGED_JSON_KEY in data:
                del data[MANAGED_JSON_KEY]
                _atomic_write(config_path, json.dumps(data, indent=2) + "\n")
                return True
        except json.JSONDecodeError:
            pass

    # Text files (CLAUDE.md, etc.)
    if MANAGED_MARKER in content:
        lines = content.splitlines(keepends=True)
        filtered = []
        in_managed = False
        for line in lines:
            if MANAGED_MARKER in line:
                in_managed = True
                continue
            if in_managed and line.strip() == f"{MANAGED_MARKER} end":
                in_managed = False
                continue
            if not in_managed:
                filtered.append(line)
        _atomic_write(config_path, "".join(filtered))
        return True

    return False


def generate_claude_code_config(project_dir: Path) -> dict[str, Any]:
    """Generate Claude Code MCP server config."""
    return {
        "mcpServers": {
            "autocode": {
                "command": "uv",
                "args": ["run", "autocode", "mcp-serve"],
                "cwd": str(project_dir),
            },
        },
        "tools": [
            "search_code", "find_definition", "find_references",
            "list_symbols", "read_file", "get_diagnostics",
        ],
    }


def generate_opencode_config(project_dir: Path) -> dict[str, Any]:
    """Generate OpenCode MCP server config."""
    return {
        "mcp": {
            "autocode": {
                "command": "uv",
                "args": ["run", "autocode", "mcp-serve"],
                "cwd": str(project_dir),
            },
        },
    }


def generate_codex_config(project_dir: Path) -> dict[str, Any]:
    """Generate Codex MCP server config."""
    return {
        "mcp_servers": {
            "autocode": {
                "command": "uv run autocode mcp-serve",
                "cwd": str(project_dir),
            },
        },
    }
