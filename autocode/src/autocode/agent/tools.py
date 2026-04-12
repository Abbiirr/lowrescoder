"""Tool registry and built-in tool definitions."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autocode.agent.conflict import check_file_conflict
from autocode.agent.tool_result_cache import ToolResultCache
from autocode.utils.file_tools import (
    edit_file,
    list_files,
    read_file,
    validate_path,
    write_file,
)


@dataclass
class ToolDefinition:
    """A tool that the agent can invoke.

    Expanded per PLAN.md Section 0.4 with metadata for:
    - concurrency safety
    - interruptibility
    - output budget hints
    - direct vs orchestrated call eligibility
    """

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters
    handler: Callable[..., str]
    requires_approval: bool = False
    mutates_fs: bool = False
    executes_shell: bool = False
    # Sprint 4B: AgentMode.PLANNING blocks tools with mutates_fs=True or executes_shell=True

    # Section 0.4: Scheduling/policy/compaction metadata
    concurrency_safe: bool = True  # Can run concurrent with other tools
    interruptible: bool = False  # Can be safely interrupted mid-execution
    output_budget_tokens: int = 1000  # Estimated max output tokens
    direct_call_eligible: bool = True  # Can be called directly by frontend
    orchestrated_eligible: bool = True  # Can be called via orchestrator


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

    def filter(self, allowed_names: set[str]) -> ToolRegistry:
        """Return a new registry containing only the named tools."""
        filtered = ToolRegistry()
        for name in allowed_names:
            tool = self._tools.get(name)
            if tool is not None:
                filtered.register(tool)
        return filtered

    def get_schemas_openai_format(self) -> list[dict[str, Any]]:
        """Return tool schemas in OpenAI function-calling format."""
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schemas

    def get_core_schemas_openai_format(self) -> list[dict[str, Any]]:
        """Return schemas for only CORE_TOOL_NAMES tools (reduces token usage)."""
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            if tool.name in CORE_TOOL_NAMES:
                schemas.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    }
                )
        return schemas

    def get_deferred_tool_names(self) -> list[str]:
        """Return names of tools not in the core set."""
        return [name for name in self._tools if name not in CORE_TOOL_NAMES]


CORE_TOOL_NAMES = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "run_command",
        "search_text",
        "list_files",
        "tool_search",
        # Typed git tools (deep-research-report Lane A) — read-only
        "git_status",
        "git_diff",
        "git_log",
        # Typed web fetch (deep-research-report Lane A, replaces curl/wget)
        "web_fetch",
        # Transactional multi-file patch (deep-research-report Phase B Item 1)
        "apply_patch",
    }
)


# --- Built-in tool handlers ---

_OBSERVED_FILE_MTIMES: dict[str, float] = {}
_WORKING_SET_CLOCK = 0


@dataclass
class WorkingSetEntry:
    """A recently active file in the current project."""

    hits: int = 0
    last_seen: int = 0


_ACTIVE_WORKING_SET: dict[str, dict[str, WorkingSetEntry]] = {}


def clear_observed_file_mtimes() -> None:
    """Clear the observed mtime cache. Call on session teardown to prevent cross-session bleed."""
    _OBSERVED_FILE_MTIMES.clear()


def _normalized_project_root(project_root: str = "") -> str:
    """Return a normalized absolute project root key."""
    return str(Path(project_root).resolve()) if project_root else str(Path(".").resolve())


def clear_active_working_set(project_root: str = "") -> None:
    """Clear the tracked working set for one project root or for all roots."""
    global _WORKING_SET_CLOCK  # noqa: PLW0603
    if project_root:
        _ACTIVE_WORKING_SET.pop(_normalized_project_root(project_root), None)
    else:
        _ACTIVE_WORKING_SET.clear()
        _WORKING_SET_CLOCK = 0


def record_active_file(
    path: str | Path,
    *,
    project_root: str = "",
    weight: int = 1,
) -> None:
    """Record a file as part of the current working set."""
    global _WORKING_SET_CLOCK  # noqa: PLW0603

    try:
        resolved = _resolve_tool_path(str(path), project_root)
    except Exception:
        return

    root = Path(_normalized_project_root(project_root))
    try:
        key = str(resolved.relative_to(root))
    except ValueError:
        key = str(resolved)

    bucket = _ACTIVE_WORKING_SET.setdefault(str(root), {})
    entry = bucket.setdefault(key, WorkingSetEntry())
    _WORKING_SET_CLOCK += 1
    entry.hits += max(1, weight)
    entry.last_seen = _WORKING_SET_CLOCK

    if len(bucket) > 24:
        ranked = sorted(
            bucket.items(),
            key=lambda item: (item[1].last_seen, item[1].hits),
            reverse=True,
        )
        bucket.clear()
        bucket.update(dict(ranked[:24]))


def get_active_working_set(project_root: str = "", limit: int = 5) -> list[str]:
    """Return the current active file set ordered by recency, then frequency."""
    bucket = _ACTIVE_WORKING_SET.get(_normalized_project_root(project_root), {})
    ranked = sorted(
        bucket.items(),
        key=lambda item: (item[1].last_seen, item[1].hits),
        reverse=True,
    )
    return [path for path, _entry in ranked[:limit]]


def _resolve_tool_path(path: str, project_root: str = "") -> Path:
    """Resolve a tool path the same way file_tools does."""
    file_path = Path(path)
    if project_root:
        return validate_path(file_path, Path(project_root))
    return file_path.resolve()


def _remember_observed_file(file_path: Path) -> None:
    """Store the latest observed mtime for conflict detection."""
    try:
        _OBSERVED_FILE_MTIMES[str(file_path)] = os.path.getmtime(file_path)
    except OSError:
        _OBSERVED_FILE_MTIMES.pop(str(file_path), None)


def _current_conflict_message(file_path: Path) -> str | None:
    """Return a conflict message if the file changed since last observation."""
    expected_mtime = _OBSERVED_FILE_MTIMES.get(str(file_path))
    if expected_mtime is None or not file_path.exists():
        return None

    conflict = check_file_conflict(file_path, expected_mtime)
    if conflict.has_conflict:
        return conflict.message
    return None


@dataclass
class EditPreview:
    """Preview information for a pending write/edit operation."""

    file_path: str
    before: str
    after: str
    conflict_message: str | None = None
    is_new_file: bool = False


def preview_file_change(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    project_root: str = "",
) -> EditPreview:
    """Build a diff preview for write/edit approval prompts."""
    resolved = _resolve_tool_path(str(arguments["path"]), project_root)
    before = ""
    if resolved.exists():
        before = resolved.read_text(encoding="utf-8")

    conflict_message = _current_conflict_message(resolved)

    if tool_name == "write_file":
        after = str(arguments.get("content", ""))
    elif tool_name == "edit_file":
        old_string = str(arguments.get("old_string", ""))
        new_string = str(arguments.get("new_string", ""))
        if not old_string:
            msg = "old_string must not be empty"
            raise ValueError(msg)
        count = before.count(old_string)
        if count == 0:
            msg = f"old_string not found in {resolved.name}"
            raise ValueError(msg)
        if count > 1:
            msg = (
                f"old_string matches {count} times in {resolved.name}"
                " — add more context to make it unique"
            )
            raise ValueError(msg)
        after = before.replace(old_string, new_string, 1)
    else:
        msg = f"Unsupported preview tool: {tool_name}"
        raise ValueError(msg)

    exists = resolved.exists()
    if exists:
        _remember_observed_file(resolved)

    return EditPreview(
        file_path=str(resolved),
        before=before,
        after=after,
        conflict_message=conflict_message,
        is_new_file=not exists,
    )


#: Hard cap on lines returned from read_file when no explicit end_line is
#: provided. Per the deep-research-report (Phase A Item 2): "byte/line caps
#: must be mandatory on reads to prevent token blowups."
_READ_FILE_DEFAULT_MAX_LINES = 2000

#: Absolute hard cap on BYTES returned regardless of line range, to protect
#: against single enormous lines (e.g. minified assets).
_READ_FILE_MAX_BYTES = 256 * 1024


def _handle_read_file(
    path: str,
    project_root: str = "",
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a file's contents, enforcing mandatory line + byte caps.

    If ``end_line`` is not explicitly specified, the output is capped at
    ``_READ_FILE_DEFAULT_MAX_LINES`` lines with a truncation marker. The
    output is additionally capped at ``_READ_FILE_MAX_BYTES`` bytes no
    matter what, to defeat single-giant-line edge cases.
    """
    try:
        root = project_root or None
        # Track whether the caller explicitly bounded the range — we only
        # auto-cap reads that requested "whole file" or an unbounded tail.
        explicit_end = end_line is not None

        content = read_file(
            path,
            project_root=root,
            start_line=start_line,
            end_line=end_line,
        )

        resolved = _resolve_tool_path(path, project_root)
        if resolved.exists():
            _remember_observed_file(resolved)
            record_active_file(resolved, project_root=project_root, weight=2)

        # Line cap (only when the caller didn't give us an explicit end_line)
        line_truncated = False
        if not explicit_end:
            lines = content.splitlines(keepends=True)
            if len(lines) > _READ_FILE_DEFAULT_MAX_LINES:
                kept = lines[:_READ_FILE_DEFAULT_MAX_LINES]
                dropped = len(lines) - _READ_FILE_DEFAULT_MAX_LINES
                content = "".join(kept)
                content += (
                    f"\n[...truncated at {_READ_FILE_DEFAULT_MAX_LINES} lines, "
                    f"{dropped} more. Call read_file again with start_line/end_line "
                    f"for a specific range.]\n"
                )
                line_truncated = True

        # Absolute byte cap
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > _READ_FILE_MAX_BYTES:
            content = content_bytes[:_READ_FILE_MAX_BYTES].decode(
                "utf-8", errors="replace"
            )
            suffix = f"\n[...truncated at {_READ_FILE_MAX_BYTES} bytes"
            if not line_truncated:
                suffix += " — try reading a narrower line range"
            suffix += "]\n"
            content += suffix

        return content
    except Exception as e:
        return f"Error reading file: {e}"


def _git_auto_commit(file_path: Path) -> str | None:
    """Create a safety commit before modifying a file.

    Returns the commit SHA if successful, None otherwise.
    Only commits if the file is tracked in a git repo.
    """
    import subprocess

    try:
        # Find git root
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(file_path.parent),
        )
        if git_root.returncode != 0:
            return None  # Not in a git repo

        # Check if file is tracked
        is_tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=git_root.stdout.strip(),
        )
        if is_tracked.returncode != 0:
            return None  # File not tracked

        # Check if file has changes worth committing
        diff_check = subprocess.run(
            ["git", "diff", "--quiet", str(file_path)],
            capture_output=True,
            timeout=5,
            cwd=git_root.stdout.strip(),
        )
        if diff_check.returncode == 0:
            return None  # No changes to commit

        # Auto-commit the current state
        subprocess.run(
            ["git", "add", str(file_path)],
            capture_output=True,
            timeout=5,
            cwd=git_root.stdout.strip(),
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"autocode: safety snapshot before edit ({file_path.name})"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=git_root.stdout.strip(),
            env=_safe_shell_env(),
        )
        if result.returncode == 0:
            sha = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=git_root.stdout.strip(),
            )
            return sha.stdout.strip()
    except Exception:
        pass
    return None


def _generate_diff(before: str, after: str, filepath: str) -> str:
    """Generate a unified diff between before and after content."""
    import difflib

    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        lineterm="",
    )
    return "".join(diff)


def _handle_write_file(path: str, content: str, project_root: str = "") -> str:
    """Write content to a file with diff preview and conflict detection."""
    try:
        root = project_root or None
        file_path = Path(path)
        resolved = _resolve_tool_path(path, project_root)

        # Conflict detection: check if file was modified externally
        before = ""
        is_new = not resolved.exists()
        if not is_new:
            try:
                before = resolved.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                before = ""  # binary or unreadable
            conflict_message = _current_conflict_message(resolved)
            if conflict_message:
                return (
                    "Error writing file: "
                    f"{conflict_message}. Re-read the file before overwriting it."
                )

        result = write_file(path, content, project_root=root)
        _remember_observed_file(resolved)
        record_active_file(resolved, project_root=project_root, weight=4)

        # Generate diff
        if is_new:
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return f"Created {result} ({line_count} lines, new file)"
        else:
            diff = _generate_diff(before, content, str(file_path))
            if diff:
                # Truncate very long diffs
                if len(diff) > 2000:
                    diff = diff[:2000] + "\n... (diff truncated)"
                return f"Written to {result}\n\nDiff:\n```diff\n{diff}\n```"
            else:
                return f"Written to {result} (no changes)"
    except Exception as e:
        return f"Error writing file: {e}"


def _handle_edit_file(
    path: str,
    old_string: str,
    new_string: str,
    project_root: str = "",
) -> str:
    """Edit a file by replacing a specific string, with diff preview."""
    try:
        root = project_root or None
        resolved = _resolve_tool_path(path, project_root)

        # Capture before content
        before = ""
        conflict_note = None
        if resolved.exists():
            try:
                before = resolved.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                pass
            conflict_note = _current_conflict_message(resolved)

        result = edit_file(path, old_string, new_string, project_root=root)
        _remember_observed_file(resolved)
        record_active_file(resolved, project_root=project_root, weight=4)

        # Generate diff
        after = ""
        if resolved.exists():
            try:
                after = resolved.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                pass

        response = f"Edited {result}"
        if before and after:
            diff = _generate_diff(before, after, str(resolved))
            if diff:
                if len(diff) > 2000:
                    diff = diff[:2000] + "\n... (diff truncated)"
                response = f"Edited {result}\n\nDiff:\n```diff\n{diff}\n```"

        if conflict_note:
            response += (
                "\n\nWarning: file changed since the last observation; "
                "the edit was applied to the latest contents."
            )
        return response
    except Exception as e:
        return f"Error editing file: {e}"


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
    pattern: str,
    directory: str,
    glob_pattern: str,
    max_results: int,
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
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
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
    pattern: str,
    directory: str,
    glob_pattern: str,
    max_results: int,
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
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
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
    pattern: str,
    directory: str,
    glob_pattern: str,
    max_results: int,
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


#: Hard upper bound on search_text result count, even if the caller
#: requests more. Per the deep-research-report Phase A Item 2.
_SEARCH_TEXT_MAX_RESULTS_CAP = 500

#: Hard upper bound on bytes returned from search_text.
_SEARCH_TEXT_MAX_BYTES = 64 * 1024


def _handle_search_text(
    pattern: str,
    directory: str = ".",
    glob_pattern: str = "**/*",
    max_results: int = 50,
) -> str:
    """Search for text in files. Tries ripgrep > grep > Python fallback.

    Args:
        pattern: The regex pattern to search for.
        directory: Root directory for the search (default: current dir).
        glob_pattern: Glob filter for which files to scan (default: '**/*').
        max_results: Max hits to return. Capped at
            ``_SEARCH_TEXT_MAX_RESULTS_CAP``; values outside ``[1, cap]``
            are clamped.

    Returns:
        Structured hit list truncated at the caps (results + bytes).
    """
    # Clamp the caller-supplied cap into a safe range
    if not isinstance(max_results, int) or max_results < 1:
        max_results = 50
    if max_results > _SEARCH_TEXT_MAX_RESULTS_CAP:
        max_results = _SEARCH_TEXT_MAX_RESULTS_CAP

    # Try ripgrep first (fastest)
    result = _search_with_ripgrep(pattern, directory, glob_pattern, max_results)
    if result is None:
        # Try grep (faster than Python)
        result = _search_with_grep(pattern, directory, glob_pattern, max_results)
    if result is None:
        # Python fallback (always works)
        result = _search_with_python(pattern, directory, glob_pattern, max_results)

    # Enforce the absolute byte cap regardless of which backend produced
    # the result — protects against a single giant matching line.
    if result and len(result) > _SEARCH_TEXT_MAX_BYTES:
        head = result[:_SEARCH_TEXT_MAX_BYTES]
        remaining = len(result) - _SEARCH_TEXT_MAX_BYTES
        result = (
            head
            + f"\n[...truncated at {_SEARCH_TEXT_MAX_BYTES} bytes, "
            + f"{remaining} more. Narrow the directory or glob_pattern.]"
        )

    return result


def _safe_shell_env() -> dict[str, str]:
    """Build a safe environment for shell commands.

    Blocks GIT_EDITOR to prevent interactive editor hijacking,
    and sets DEBIAN_FRONTEND=noninteractive.
    """
    env = os.environ.copy()
    env["GIT_EDITOR"] = "true"
    env["EDITOR"] = "true"
    env["VISUAL"] = "true"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["DEBIAN_FRONTEND"] = "noninteractive"
    return env


def _handle_run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command via OS sandbox when available.

    Uses sandbox.run_sandboxed() for process isolation (bwrap on Linux,
    Seatbelt on macOS). Falls back to restricted env if no sandbox —
    unless ``shell.fail_if_unavailable`` is set in AutoCodeConfig, in
    which case the command refuses to run with a non-zero exit code.
    Shell safety: GIT_EDITOR blocked, 30s default timeout.

    Hardening (deep-research-report gap analysis):
    Commands containing ``bash -lc``/``sh -c``/``eval``/``$(...)``/backticks
    are treated as **risk escalation** — still executed (per the existing
    approval gate) but prefixed with a ``[shell escalation]`` marker in the
    output so the caller can audit compound commands that hide multiple
    actions inside one string.
    """
    from autocode.agent.git_tools import detect_shell_escalation
    from autocode.agent.sandbox import SandboxConfig, SandboxPolicy, run_sandboxed

    escalation = detect_shell_escalation(command)

    # Consult the project config for the fail-closed flag and
    # pattern-based permission rules. Load lazily so tests that mock
    # the tool handler path don't pay the config import cost.
    fail_closed = False
    try:
        from autocode.config import load_config

        cfg = load_config()
        fail_closed = bool(cfg.shell.fail_if_unavailable)

        # Permission-rules enforcement (Phase B integration loose end 2).
        # Evaluate command against pattern rules before executing.
        if cfg.shell.permission_rules:
            from autocode.agent.permission_rules import evaluate, parse_rule

            rules = []
            for rule_dict in cfg.shell.permission_rules:
                try:
                    rules.append(
                        parse_rule(
                            rule_dict["header"],
                            rule_dict["effect"],
                            matches=rule_dict.get("matches"),
                            not_matches=rule_dict.get("not_matches"),
                        )
                    )
                except (KeyError, ValueError):
                    continue  # skip malformed rules
            if rules:
                decision = evaluate("Bash", command, rules)
                if decision.effect == "deny":
                    return (
                        f"[permission denied] Command refused: {decision.reason}\n"
                        f"Command: {command}"
                    )
    except Exception:
        pass

    config = SandboxConfig(
        policy=SandboxPolicy.WRITABLE_PROJECT,
        project_root=os.getcwd(),
        timeout_s=timeout,
        allow_network=True,  # commands may need network
        fail_if_unavailable=fail_closed,
    )
    sandbox_result = run_sandboxed(command, config)

    output = sandbox_result.stdout
    if sandbox_result.returncode != 0:
        output += f"\n[exit code {sandbox_result.returncode}]"
        if sandbox_result.stderr:
            output += f"\nstderr: {sandbox_result.stderr}"
    result = output.strip() or "(no output)"
    if escalation:
        result = f"[shell escalation: {', '.join(escalation)}]\n{result}"
    return result


def _handle_ask_user_placeholder(**kwargs: Any) -> str:
    """Placeholder handler — ask_user is intercepted by the agent loop."""
    return "ask_user requires an interactive UI callback."


def _handle_clear_tool_results(
    cache: ToolResultCache,
    mode: str = "summary",
    ids: list[str] | None = None,
    tool: str | None = None,
    older_than_seconds: float | None = None,
) -> str:
    """Clear or inspect the tool-result cache.

    Modes:
    - ``summary`` (default): return the cache summary without clearing.
    - ``all``: clear every entry.
    - ``by_tool``: clear entries for a specific tool name.
    - ``by_ids``: clear entries by their IDs.
    - ``older_than``: clear entries older than N seconds.

    Returns a human-readable status message.
    """
    if mode == "summary":
        return cache.summary()
    elif mode == "all":
        n = cache.clear(all=True)
        return f"Cleared {n} tool-result entries. {cache.summary()}"
    elif mode == "by_tool":
        if not tool:
            return "Error: mode='by_tool' requires a 'tool' parameter."
        n = cache.clear(tool=tool)
        return f"Cleared {n} entries for tool '{tool}'. {cache.summary()}"
    elif mode == "by_ids":
        if not ids:
            return "Error: mode='by_ids' requires an 'ids' parameter."
        n = cache.clear(ids=ids)
        return f"Cleared {n} entries by ID. {cache.summary()}"
    elif mode == "older_than":
        if older_than_seconds is None:
            return "Error: mode='older_than' requires 'older_than_seconds'."
        n = cache.clear(older_than_seconds=older_than_seconds)
        return f"Cleared {n} entries older than {older_than_seconds}s. {cache.summary()}"
    else:
        return f"Unknown mode '{mode}'. Valid: summary, all, by_tool, by_ids, older_than."


def _handle_tool_search(query: str, tool_registry: ToolRegistry) -> str:
    """Search all registered tools by name and description (case-insensitive)."""
    query_lower = query.lower()
    matches: list[ToolDefinition] = []
    for tool in tool_registry.get_all():
        if query_lower in tool.name.lower() or query_lower in tool.description.lower():
            matches.append(tool)

    if not matches:
        return f"No tools found matching '{query}'. Try a broader search term."

    lines: list[str] = [f"Found {len(matches)} tool(s) matching '{query}':\n"]
    for tool in matches:
        import json as _json

        lines.append(f"- **{tool.name}**: {tool.description}")
        lines.append(f"  Parameters: {_json.dumps(tool.parameters, indent=2)}")
        lines.append("")

    lines.append("These tools are now available for use.")
    return "\n".join(lines)


# --- Layer 1 tool handlers (Sprint 3G) ---


def _handle_find_references(symbol: str, file: str = "", project_root: str = "") -> str:
    """Find all references to a symbol in the project."""
    try:
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project_root or None)
        query = f"find references of {symbol}"
        if file:
            query += f" in {file}"
        response = handler.handle(query)
        return response.content
    except Exception as e:
        return f"Error finding references: {e}"


def _handle_find_definition(symbol: str, file: str = "", project_root: str = "") -> str:
    """Find the definition of a symbol."""
    try:
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project_root or None)
        query = f"find definition of {symbol}"
        if file:
            query += f" in {file}"
        response = handler.handle(query)
        return response.content
    except Exception as e:
        return f"Error finding definition: {e}"


def _handle_get_type_info(symbol: str, file: str = "", project_root: str = "") -> str:
    """Get type information for a symbol."""
    try:
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project_root or None)
        query = f"show signature of {symbol}"
        if file:
            query += f" in {file}"
        response = handler.handle(query)
        if file:
            record_active_file(file, project_root=project_root, weight=2)
        return response.content
    except Exception as e:
        return f"Error getting type info: {e}"


def _handle_list_symbols(file: str, kind: str = "symbols", project_root: str = "") -> str:
    """List symbols (functions, classes, methods) in a file."""
    try:
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project_root or None)
        response = handler.handle(f"list {kind} in {file}")
        record_active_file(file, project_root=project_root, weight=2)
        return response.content
    except Exception as e:
        return f"Error listing symbols: {e}"


_code_index_cache: Any = None
_code_index_project_root: str = ""


def clear_code_index_cache() -> None:
    """Clear the cached CodeIndex instance (e.g. after /index rebuild)."""
    global _code_index_cache, _code_index_project_root  # noqa: PLW0603
    _code_index_cache = None
    _code_index_project_root = ""


def set_code_index_cache(index: Any) -> None:
    """Set the cached CodeIndex instance (e.g. after /index rebuild)."""
    global _code_index_cache  # noqa: PLW0603
    _code_index_cache = index


def warm_code_index(
    project_root: str = "",
    *,
    force_rebuild: bool = False,
) -> tuple[Any, dict[str, int]]:
    """Warm and incrementally refresh the shared CodeIndex cache.

    Reuses the same index object for the same project root, but still calls
    ``build()`` so the index can cheaply pick up changed files via its
    incremental hash-based refresh logic.
    """
    global _code_index_cache, _code_index_project_root  # noqa: PLW0603
    from autocode.layer2.index import CodeIndex

    root = str(Path(project_root).resolve()) if project_root else str(Path(".").resolve())
    if force_rebuild or _code_index_cache is None or _code_index_project_root != root:
        _code_index_cache = CodeIndex()
        _code_index_project_root = root

    stats = _code_index_cache.build(root)
    return _code_index_cache, stats


def _handle_search_code(query: str, top_k: int = 5, project_root: str = "") -> str:
    """Search code using hybrid BM25 + vector search."""
    try:
        from autocode.layer2.embeddings import EmbeddingEngine
        from autocode.layer2.search import HybridSearch

        index, _stats = warm_code_index(project_root)
        engine = EmbeddingEngine()
        search = HybridSearch(index, embeddings=engine)
        results = search.search(query, top_k=top_k)
        working_set = get_active_working_set(project_root, limit=8)
        if working_set:
            working_rank = {path: idx for idx, path in enumerate(working_set)}
            root = Path(_normalized_project_root(project_root))
            for result in results:
                try:
                    relative_path = str(Path(result.chunk.file_path).resolve().relative_to(root))
                except ValueError:
                    relative_path = result.chunk.file_path
                if relative_path in working_rank:
                    boost = 0.05 * (len(working_set) - working_rank[relative_path])
                    result.score += boost
                    result.match_type = f"{result.match_type}+working-set"
            results.sort(key=lambda item: item.score, reverse=True)

        if not results:
            return "No results found."

        lines = [f"Found {len(results)} results:\n"]
        for rank, r in enumerate(results, start=1):
            record_active_file(
                r.chunk.file_path,
                project_root=project_root,
                weight=max(1, top_k - rank + 1),
            )
            lines.append(
                f"**{r.chunk.file_path}:{r.chunk.start_line}** "
                f"(score: {r.score:.3f}, {r.match_type})"
            )
            preview = r.chunk.content[:200]
            if len(r.chunk.content) > 200:
                preview += "..."
            lines.append(f"```\n{preview}\n```\n")

        return "\n".join(lines)
    except Exception as e:
        return f"Error searching code: {e}"


def create_default_registry(
    project_root: str = "",
    tool_result_cache: ToolResultCache | None = None,
) -> ToolRegistry:
    """Create a registry with the built-in tools for file, shell, and L1/L2 work.

    Args:
        project_root: Project root directory.
        tool_result_cache: Optional ToolResultCache instance. When provided,
            registers the ``clear_tool_results`` meta-tool so the agent can
            selectively clear cached tool results to manage context.
    """
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="read_file",
            description=(
                "Read file contents, optionally limited to a line range. "
                "Unbounded reads are auto-capped at 2000 lines and 256 KB "
                "with a truncation marker — pass explicit start_line/end_line "
                "to read a specific slice without the cap."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "start_line": {
                        "type": "integer",
                        "description": "Start line (1-based, optional)",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": (
                            "End line (1-based, optional). If omitted, the "
                            "read auto-caps at 2000 lines."
                        ),
                    },
                },
                "required": ["path"],
            },
            handler=lambda **kwargs: _handle_read_file(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
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
            mutates_fs=True,
        )
    )

    registry.register(
        ToolDefinition(
            name="edit_file",
            description=(
                "Edit an existing file by replacing a specific string. "
                "Preferred over write_file for modifying existing files."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to find (must match exactly once)",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement text",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
            handler=lambda **kwargs: _handle_edit_file(project_root=project_root, **kwargs),
            requires_approval=True,
            mutates_fs=True,
        )
    )

    registry.register(
        ToolDefinition(
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
        )
    )

    registry.register(
        ToolDefinition(
            name="search_text",
            description=(
                "Search for a regex pattern in files under a directory. "
                "Results are capped at max_results (default 50, hard cap "
                "500) and 64 KB of output with a truncation marker."
            ),
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
                    "max_results": {
                        "type": "integer",
                        "description": (
                            "Max hits to return (default 50, hard cap 500). "
                            "Values outside this range are clamped."
                        ),
                    },
                },
                "required": ["pattern"],
            },
            handler=_handle_search_text,
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="run_command",
            description="Run a shell command and return its output.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                    },
                },
                "required": ["command"],
            },
            handler=_handle_run_command,
            requires_approval=True,
            executes_shell=True,
        )
    )

    # --- Typed git tools (deep-research-report Lane A) ---
    from autocode.agent.git_tools import (
        _handle_git_diff,
        _handle_git_log,
        _handle_git_status,
    )

    registry.register(
        ToolDefinition(
            name="git_status",
            description=(
                "Return a structured git status snapshot for the project root "
                "(branch, staged/changed/untracked files, ahead/behind). "
                "Read-only; no approval required."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda **_kwargs: _handle_git_status(project_root=project_root),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_diff",
            description=(
                "Return a unified diff of working-tree or staged changes, "
                "truncated at max_bytes to cap tokens. Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of paths to scope the diff",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": (
                            "Diff staged changes instead of working tree"
                            " (default: false)"
                        ),
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines (default: 3)",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Hard byte cap on the returned diff (default: 32768)",
                    },
                },
                "required": [],
            },
            handler=lambda **kwargs: _handle_git_diff(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_log",
            description=(
                "Return recent commit history (up to max_commits, default 20). "
                "Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "max_commits": {
                        "type": "integer",
                        "description": "Max commits to return (default: 20, cap: 200)",
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of paths to scope the log",
                    },
                    "oneline": {
                        "type": "boolean",
                        "description": "Return oneline format (default: true)",
                    },
                },
                "required": [],
            },
            handler=lambda **kwargs: _handle_git_log(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    # --- Transactional patch (deep-research-report Phase B Item 1) ---
    from autocode.agent.apply_patch import _handle_apply_patch

    registry.register(
        ToolDefinition(
            name="apply_patch",
            description=(
                "Apply multiple old_string → new_string edits across one "
                "or more files atomically. Preflights every operation "
                "(file exists, old_string unique) before writing — if "
                "ANY op would conflict, NO files are written. Set "
                "dry_run=true to preview conflicts without touching disk. "
                "Prefer over chained edit_file calls when you need "
                "multi-step atomicity."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "description": "List of edit operations to apply atomically",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path"},
                                "old_string": {
                                    "type": "string",
                                    "description": "Exact text to find (must be unique per file)",
                                },
                                "new_string": {
                                    "type": "string",
                                    "description": "Replacement text",
                                },
                            },
                            "required": ["path", "old_string", "new_string"],
                        },
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview conflicts without writing (default: false)",
                    },
                },
                "required": ["operations"],
            },
            handler=lambda **kwargs: _handle_apply_patch(
                project_root=project_root, **kwargs
            ),
            requires_approval=True,
            mutates_fs=True,
        )
    )

    # --- Typed web fetch (deep-research-report Lane A) ---
    from autocode.agent.web_fetch import DEFAULT_MAX_BYTES, _handle_web_fetch

    registry.register(
        ToolDefinition(
            name="web_fetch",
            description=(
                "Fetch a URL with a domain allowlist and hard byte cap. "
                "Read-only (GET only). Refuses binary content types, "
                "off-allowlist hosts, and redirects that leave the "
                "allowlist. Preferred over `curl`/`wget` via run_command."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Absolute http(s) URL to fetch",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": (
                            f"Hard byte cap on the returned body "
                            f"(default {DEFAULT_MAX_BYTES}, cap 1048576)"
                        ),
                    },
                    "timeout_s": {
                        "type": "integer",
                        "description": "Socket timeout in seconds (default 10)",
                    },
                },
                "required": ["url"],
            },
            handler=_handle_web_fetch,
            requires_approval=False,
        )
    )

    # --- LSP tools via Jedi (deep-research-report Phase B Item 3) ---
    from autocode.agent.lsp_tools import (
        _handle_lsp_find_references,
        _handle_lsp_get_type,
        _handle_lsp_goto_definition,
        _handle_lsp_symbols,
    )

    _lsp_cursor_params = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Python file to analyze (relative to project or absolute)",
            },
            "line": {
                "type": "integer",
                "description": "1-based line number of the cursor",
            },
            "column": {
                "type": "integer",
                "description": "1-based column number of the cursor",
            },
        },
        "required": ["path", "line", "column"],
    }

    registry.register(
        ToolDefinition(
            name="lsp_goto_definition",
            description=(
                "Resolve the Python symbol under a cursor (path, line, col) "
                "to its definition sites. Uses Jedi static analysis — "
                "stricter than regex search, understands imports/types. "
                "Read-only."
            ),
            parameters=_lsp_cursor_params,
            handler=lambda **kwargs: _handle_lsp_goto_definition(
                project_root=project_root, **kwargs
            ),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="lsp_find_references",
            description=(
                "Find every reference to the Python symbol under a cursor "
                "(path, line, col). Uses Jedi static analysis — finds calls, "
                "imports, and re-exports across the project. Read-only."
            ),
            parameters=_lsp_cursor_params,
            handler=lambda **kwargs: _handle_lsp_find_references(
                project_root=project_root, **kwargs
            ),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="lsp_get_type",
            description=(
                "Return the inferred type of the Python symbol under a "
                "cursor (path, line, col). Uses Jedi static analysis. "
                "Read-only."
            ),
            parameters=_lsp_cursor_params,
            handler=lambda **kwargs: _handle_lsp_get_type(
                project_root=project_root, **kwargs
            ),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="lsp_symbols",
            description=(
                "List top-level Python symbols (functions, classes, "
                "imports) defined in a file. Uses Jedi. Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Python file to list symbols for",
                    },
                },
                "required": ["path"],
            },
            handler=lambda **kwargs: _handle_lsp_symbols(
                project_root=project_root, **kwargs
            ),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
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
        )
    )

    # --- Layer 1/2 tools (Sprint 3G) ---

    registry.register(
        ToolDefinition(
            name="find_references",
            description="Find all references to a symbol in the project (zero LLM tokens).",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name to find references for",
                    },
                    "file": {"type": "string", "description": "Optional file to search in"},
                },
                "required": ["symbol"],
            },
            handler=lambda **kwargs: _handle_find_references(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="find_definition",
            description="Find the definition of a symbol in the project (zero LLM tokens).",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name to find definition for",
                    },
                    "file": {"type": "string", "description": "Optional file to search in"},
                },
                "required": ["symbol"],
            },
            handler=lambda **kwargs: _handle_find_definition(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="get_type_info",
            description="Get type/signature information for a symbol (zero LLM tokens).",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol name to get type info for"},
                    "file": {"type": "string", "description": "Optional file to search in"},
                },
                "required": ["symbol"],
            },
            handler=lambda **kwargs: _handle_get_type_info(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="list_symbols",
            description=(
                "List symbols (functions, classes, methods) in a file (zero LLM tokens). "
                "Use kind='functions', 'classes', 'methods', or 'symbols' for all."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "File path to list symbols from"},
                    "kind": {
                        "type": "string",
                        "description": (
                            "Kind of symbols: functions, classes, methods, "
                            "symbols (default: symbols)"
                        ),
                    },
                },
                "required": ["file"],
            },
            handler=lambda **kwargs: _handle_list_symbols(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="search_code",
            description=(
                "Search the codebase using hybrid BM25 + vector search. "
                "Returns relevant code chunks ranked by relevance."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                    },
                },
                "required": ["query"],
            },
            handler=lambda **kwargs: _handle_search_code(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    registry.register(
        ToolDefinition(
            name="semantic_search",
            description=(
                "Semantic code search alias for search_code. "
                "Use this when you want ranked code/file matches for a natural-language query."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                    },
                },
                "required": ["query"],
            },
            handler=lambda **kwargs: _handle_search_code(project_root=project_root, **kwargs),
            requires_approval=False,
        )
    )

    # --- Meta tool: clear_tool_results (Phase B integration loose end 1) ---

    if tool_result_cache is not None:
        _cache = tool_result_cache  # capture for closure

        registry.register(
            ToolDefinition(
                name="clear_tool_results",
                description=(
                    "Inspect or selectively clear cached tool-call results to "
                    "manage context size. Modes: 'summary' (inspect), 'all' "
                    "(clear everything), 'by_tool' (clear one tool's results), "
                    "'by_ids' (clear specific IDs), 'older_than' (age-based). "
                    "Use this when stale read_file/search_text results dominate "
                    "the context window."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "description": (
                                "Operation mode: summary, all, by_tool, "
                                "by_ids, older_than (default: summary)"
                            ),
                            "enum": ["summary", "all", "by_tool", "by_ids", "older_than"],
                        },
                        "tool": {
                            "type": "string",
                            "description": "Tool name to clear (for mode='by_tool')",
                        },
                        "ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Entry IDs to clear (for mode='by_ids')",
                        },
                        "older_than_seconds": {
                            "type": "number",
                            "description": "Age threshold in seconds (for mode='older_than')",
                        },
                    },
                    "required": [],
                },
                handler=lambda **kwargs: _handle_clear_tool_results(
                    cache=_cache, **kwargs
                ),
                requires_approval=False,
            )
        )

    # --- Meta tool: tool_search (deferred tool loading) ---

    registry.register(
        ToolDefinition(
            name="tool_search",
            description=(
                "Search for additional tools by name or description. "
                "Use this when you need a capability not covered by the currently available tools. "
                "Returns matching tools with their descriptions and parameter schemas."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term to match against tool names and descriptions",
                    },
                },
                "required": ["query"],
            },
            handler=lambda **kwargs: _handle_tool_search(tool_registry=registry, **kwargs),
            requires_approval=False,
        )
    )

    # --- Todo tools (mandatory planning) ---
    _todo_state: list[dict[str, str]] = []

    def _handle_todo_write(**kwargs: Any) -> str:
        import json as _json
        todos = kwargs.get("todos", [])
        if isinstance(todos, str):
            try:
                todos = _json.loads(todos)
            except _json.JSONDecodeError:
                return "Error: todos must be a JSON array of {id, text, status} objects"
        _todo_state.clear()
        for item in todos:
            _todo_state.append({
                "id": str(item.get("id", len(_todo_state))),
                "text": str(item.get("text", "")),
                "status": str(item.get("status", "pending")),
            })
        return f"Todo list updated: {len(_todo_state)} items"

    def _handle_todo_read(**_kwargs: Any) -> str:
        if not _todo_state:
            return "No todos yet. Use todo_write to create a plan."
        lines = []
        for item in _todo_state:
            icon = "✓" if item["status"] == "done" else "○"
            lines.append(f"{icon} [{item['id']}] {item['text']} ({item['status']})")
        return "\n".join(lines)

    registry.register(ToolDefinition(
        name="todo_write",
        description=(
            "Write or replace the task plan. You MUST call this before making "
            "any code changes to plan your approach. Each todo is {id, text, status}."
        ),
        parameters={
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": (
                        "List of todo items with id, text, status (pending/in_progress/done)"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string"},
                        },
                        "required": ["id", "text", "status"],
                    },
                },
            },
            "required": ["todos"],
        },
        handler=_handle_todo_write,
        requires_approval=False,
    ))

    registry.register(ToolDefinition(
        name="todo_read",
        description="Read the current task plan / todo list.",
        parameters={"type": "object", "properties": {}},
        handler=_handle_todo_read,
        requires_approval=False,
    ))

    # --- Glob tool (fast file discovery) ---
    def _handle_glob(**kwargs: Any) -> str:
        import subprocess as _sp
        pattern = kwargs.get("pattern", "*")
        root = kwargs.get("directory", project_root or ".")
        try:
            proc = _sp.run(
                ["find", root, "-name", pattern, "-type", "f",
                 "-not", "-path", "*/.git/*",
                 "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/node_modules/*"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return "\n".join(proc.stdout.strip().splitlines()[:100])
        except Exception:
            pass
        from pathlib import Path as _Path
        files = sorted(str(p) for p in _Path(root).rglob(pattern) if p.is_file())[:100]
        return "\n".join(files) if files else "No files found."

    registry.register(ToolDefinition(
        name="glob_files",
        description="Find files matching a glob pattern. Use to locate files before reading them.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py')"},
                "directory": {
                    "type": "string",
                    "description": "Root directory (default: project root)",
                },
            },
            "required": ["pattern"],
        },
        handler=_handle_glob,
        requires_approval=False,
    ))

    # --- Grep tool (content search with line numbers) ---
    def _handle_grep(**kwargs: Any) -> str:
        import subprocess as _sp
        pattern = kwargs.get("pattern", "")
        directory = kwargs.get("directory", project_root or ".")
        file_pattern = kwargs.get("file_pattern", "")
        if not pattern:
            return "Error: pattern is required"
        try:
            cmd = ["grep", "-rn", "-E", pattern, directory]
            if file_pattern:
                cmd = ["grep", "-rn", f"--include={file_pattern}", "-E", pattern, directory]
            proc = _sp.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.stdout.strip():
                return "\n".join(proc.stdout.strip().splitlines()[:50])
            return "No matches found."
        except Exception as e:
            return f"Error running grep: {e}"

    registry.register(ToolDefinition(
        name="grep_content",
        description=(
            "Search file contents for a regex pattern."
            " Returns matching lines with paths and line numbers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "directory": {
                    "type": "string",
                    "description": "Directory to search (default: project root)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File glob to limit search (e.g. '*.py')",
                },
            },
            "required": ["pattern"],
        },
        handler=_handle_grep,
        requires_approval=False,
    ))

    return registry
