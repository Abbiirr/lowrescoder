"""Tool registry and built-in tool definitions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hybridcoder.utils.file_tools import list_files, read_file, write_file


@dataclass
class ToolDefinition:
    """A tool that the agent can invoke."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters
    handler: Callable[..., str]
    requires_approval: bool = False


class ToolRegistry:
    """Registry of available tools with JSON Schema export."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_schemas_openai_format(self) -> list[dict[str, Any]]:
        """Return tool schemas in OpenAI function-calling format."""
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas


# --- Built-in tool handlers ---


def _handle_read_file(
    path: str,
    project_root: str = "",
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a file's contents."""
    try:
        root = project_root or None
        return read_file(path, project_root=root, start_line=start_line, end_line=end_line)
    except Exception as e:
        return f"Error reading file: {e}"


def _handle_write_file(path: str, content: str, project_root: str = "") -> str:
    """Write content to a file."""
    try:
        root = project_root or None
        result = write_file(path, content, project_root=root)
        return f"Written to {result}"
    except Exception as e:
        return f"Error writing file: {e}"


def _handle_list_files(directory: str = ".", pattern: str = "*", project_root: str = "") -> str:
    """List files in a directory."""
    try:
        root = project_root or None
        files = list_files(directory, pattern=pattern, project_root=root)
        if not files:
            return "No files found."
        return "\n".join(files[:100])
    except Exception as e:
        return f"Error listing files: {e}"


def _search_with_ripgrep(
    pattern: str, directory: str, glob_pattern: str, max_results: int,
) -> str | None:
    """Try searching with ripgrep (rg). Returns None if rg is not available."""
    import shutil
    import subprocess

    rg = shutil.which("rg")
    if rg is None:
        return None

    cmd = [rg, "--line-number", "--no-heading", "--max-count", str(max_results)]
    if glob_pattern != "**/*":
        cmd.extend(["--glob", glob_pattern])
    cmd.extend([pattern, directory])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()[:max_results]
            return "\n".join(lines) if lines else "No matches found."
        if result.returncode == 1:
            return "No matches found."
        return None  # Fall through to fallback
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _search_with_grep(
    pattern: str, directory: str, glob_pattern: str, max_results: int,
) -> str | None:
    """Try searching with grep. Returns None if grep is not available."""
    import shutil
    import subprocess

    grep = shutil.which("grep")
    if grep is None:
        return None

    # grep -rn pattern directory --include=glob
    cmd = [grep, "-rn", "--color=never"]
    if glob_pattern != "**/*":
        # Convert glob to grep --include format
        # e.g. "**/*.py" -> "*.py", "*.txt" stays as-is
        include = glob_pattern.replace("**/", "")
        cmd.extend(["--include", include])
    cmd.extend([pattern, directory])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()[:max_results]
            return "\n".join(lines) if lines else "No matches found."
        if result.returncode == 1:
            return "No matches found."
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _search_with_python(
    pattern: str, directory: str, glob_pattern: str, max_results: int,
) -> str:
    """Pure Python fallback search using pathlib + re."""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex: {e}"

    results: list[str] = []
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return f"Not a directory: {directory}"

    for file_path in dir_path.glob(glob_pattern):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = file_path.relative_to(dir_path)
                    results.append(f"{rel}:{i}: {line.strip()}")
                    if len(results) >= max_results:
                        results.append(f"... (truncated at {max_results} results)")
                        return "\n".join(results)
        except (PermissionError, OSError):
            continue

    return "\n".join(results) if results else "No matches found."


def _handle_search_text(
    pattern: str, directory: str = ".", glob_pattern: str = "**/*",
) -> str:
    """Search for text in files. Tries ripgrep > grep > Python fallback."""
    max_results = 50

    # Try ripgrep first (fastest)
    result = _search_with_ripgrep(pattern, directory, glob_pattern, max_results)
    if result is not None:
        return result

    # Try grep (faster than Python)
    result = _search_with_grep(pattern, directory, glob_pattern, max_results)
    if result is not None:
        return result

    # Python fallback (always works)
    return _search_with_python(pattern, directory, glob_pattern, max_results)


def _handle_run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command and return output.

    On Windows, uses PowerShell. On Unix, uses the default shell.
    """
    import platform
    import subprocess

    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
            )
        else:
            result = subprocess.run(
                command,
                shell=True,  # noqa: S602
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        output = result.stdout
        if result.returncode != 0:
            output += f"\n[exit code {result.returncode}]"
            if result.stderr:
                output += f"\nstderr: {result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Error running command: {e}"


def _handle_ask_user_placeholder(**kwargs: Any) -> str:
    """Placeholder handler — ask_user is intercepted by the agent loop."""
    return "ask_user requires an interactive UI callback."


def create_default_registry(project_root: str = "") -> ToolRegistry:
    """Create a registry with the 6 built-in tools."""
    registry = ToolRegistry()

    registry.register(ToolDefinition(
        name="read_file",
        description="Read file contents, optionally limited to a line range.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "start_line": {"type": "integer", "description": "Start line (1-based, optional)"},
                "end_line": {"type": "integer", "description": "End line (1-based, optional)"},
            },
            "required": ["path"],
        },
        handler=lambda **kwargs: _handle_read_file(project_root=project_root, **kwargs),
        requires_approval=False,
    ))

    registry.register(ToolDefinition(
        name="write_file",
        description="Write content to a file. Creates the file if it doesn't exist.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        handler=lambda **kwargs: _handle_write_file(project_root=project_root, **kwargs),
        requires_approval=True,
    ))

    registry.register(ToolDefinition(
        name="list_files",
        description="List files in a directory matching a glob pattern.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to search (default: '.')",
                },
                "pattern": {"type": "string", "description": "Glob pattern (default: '*')"},
            },
            "required": [],
        },
        handler=lambda **kwargs: _handle_list_files(project_root=project_root, **kwargs),
        requires_approval=False,
    ))

    registry.register(ToolDefinition(
        name="search_text",
        description="Search for a regex pattern in files under a directory.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "directory": {
                    "type": "string",
                    "description": "Directory to search (default: '.')",
                },
                "glob_pattern": {
                    "type": "string",
                    "description": "File glob pattern (default: '**/*')",
                },
            },
            "required": ["pattern"],
        },
        handler=_handle_search_text,
        requires_approval=False,
    ))

    registry.register(ToolDefinition(
        name="run_command",
        description="Run a shell command and return its output.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
            },
            "required": ["command"],
        },
        handler=_handle_run_command,
        requires_approval=True,
    ))

    registry.register(ToolDefinition(
        name="ask_user",
        description=(
            "Ask the user a question and wait for their response. "
            "Use this when you need clarification, want the user to choose "
            "between options, or need confirmation before proceeding."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Available choices (if empty, free-text input)",
                },
                "allow_text": {
                    "type": "boolean",
                    "description": "Allow free-text in addition to options (default: false)",
                },
            },
            "required": ["question"],
        },
        handler=_handle_ask_user_placeholder,
        requires_approval=False,
    ))

    return registry
