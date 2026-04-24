"""Shared slash command runtime and application command catalog."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from autocode.agent.loop import AgentMode
from autocode.config import AutoCodeConfig, save_config
from autocode.session.store import SessionStore


@runtime_checkable
class AppContext(Protocol):
    """Minimal interface for slash command handlers.

    Frontends and backend-host adapters implement this protocol so the
    command runtime can live outside UI-specific packages.
    """

    session_store: SessionStore
    session_id: str
    config: AutoCodeConfig
    project_root: Path
    command_router: CommandRouter

    def add_system_message(self, content: str) -> None: ...
    def clear_messages(self) -> None: ...
    def display_messages(self, messages: list[Any]) -> None: ...
    def get_assistant_messages(self) -> list[str]: ...
    def copy_to_clipboard(self, text: str) -> bool: ...
    def exit_app(self) -> None: ...
    def set_agent_mode(self, mode: AgentMode) -> None: ...
    async def run_loop_prompt(self, payload: str) -> None: ...
    async def run_loop_command(self, payload: str) -> None: ...

    @property
    def approval_mode(self) -> str: ...
    @approval_mode.setter
    def approval_mode(self, value: str) -> None: ...

    @property
    def shell_enabled(self) -> bool: ...
    @shell_enabled.setter
    def shell_enabled(self, value: bool) -> None: ...

    @property
    def show_thinking(self) -> bool: ...
    @show_thinking.setter
    def show_thinking(self, value: bool) -> None: ...


@dataclass
class LoopJob:
    """Session-scoped recurring loop job."""

    id: int
    interval_seconds: float
    payload: str
    task: asyncio.Task[None] | None = None
    run_count: int = 0
    skipped_count: int = 0
    running: bool = False
    cancelled: bool = False


def _ensure_loop_state(app: AppContext) -> tuple[dict[int, LoopJob], int]:
    jobs = getattr(app, "_loop_jobs", None)
    if jobs is None:
        jobs = {}
        setattr(app, "_loop_jobs", jobs)
    next_id = getattr(app, "_loop_next_id", 1)
    return jobs, next_id


def _parse_loop_interval(raw: str) -> float | None:
    raw = raw.strip().lower()
    if not raw:
        return None
    unit = raw[-1]
    factor = {"s": 1, "m": 60, "h": 3600}.get(unit)
    if factor is None:
        if raw.isdigit():
            return float(raw)
        return None
    value = raw[:-1]
    if not value.isdigit():
        return None
    seconds = int(value) * factor
    return float(seconds) if seconds > 0 else None


def _format_interval(seconds: float) -> str:
    if seconds.is_integer() and int(seconds) % 3600 == 0:
        return f"{int(seconds // 3600)}h"
    if seconds.is_integer() and int(seconds) % 60 == 0:
        return f"{int(seconds // 60)}m"
    if seconds.is_integer():
        return f"{int(seconds)}s"
    return f"{seconds:.1f}s"


def _loop_is_busy(app: AppContext) -> bool:
    generation_active = getattr(app, "_generation_active", None)
    if callable(generation_active):
        try:
            if bool(generation_active()):
                return True
        except Exception:
            pass

    if bool(getattr(app, "_generating", False)):
        return True

    agent_task = getattr(app, "_agent_task", None)
    if agent_task is not None and hasattr(agent_task, "done"):
        try:
            return not bool(agent_task.done())
        except Exception:
            return False
    return False


async def _execute_loop_payload(app: AppContext, payload: str) -> None:
    payload = payload.strip()
    if not payload:
        return

    if payload.startswith("/"):
        await app.run_loop_command(payload)
        return

    await app.run_loop_prompt(payload)


async def _run_loop_job(app: AppContext, job: LoopJob) -> None:
    try:
        while not job.cancelled:
            await asyncio.sleep(job.interval_seconds)
            if job.cancelled:
                break
            if job.running or _loop_is_busy(app):
                job.skipped_count += 1
                continue
            job.running = True
            try:
                await _execute_loop_payload(app, job.payload)
                job.run_count += 1
            except Exception as e:
                app.add_system_message(f"Loop #{job.id} run failed: {e}")
            finally:
                job.running = False
    except asyncio.CancelledError:
        return


def _cancel_loop_job(job: LoopJob) -> None:
    job.cancelled = True
    if job.task is not None:
        job.task.cancel()


def _cleanup_finished_loop_jobs(app: AppContext) -> None:
    jobs, _ = _ensure_loop_state(app)
    to_drop = [
        job_id
        for job_id, job in jobs.items()
        if job.cancelled and (job.task is None or job.task.done())
    ]
    for job_id in to_drop:
        jobs.pop(job_id, None)


@dataclass
class SlashCommand:
    """A registered slash command."""

    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    handler: Callable[..., Coroutine[Any, Any, None]] = field(
        default=None,  # type: ignore[assignment]
    )


class CommandRouter:
    """Routes /commands to their handlers."""

    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}
        self._aliases: dict[str, str] = {}

    def register(self, cmd: SlashCommand) -> None:
        """Register a slash command."""
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._aliases[alias] = cmd.name

    def dispatch(self, text: str) -> tuple[SlashCommand, str] | None:
        """Parse text and return (command, args) or None."""
        if not text.startswith("/"):
            return None
        parts = text.split(maxsplit=1)
        name = parts[0][1:]  # strip leading /
        args = parts[1] if len(parts) > 1 else ""

        if name in self._commands:
            return self._commands[name], args
        if name in self._aliases:
            return self._commands[self._aliases[name]], args
        return None

    def get_all(self) -> list[SlashCommand]:
        """Return all registered commands."""
        return list(self._commands.values())


# --- Sprint 2A command handlers ---


async def _handle_exit(app: AppContext, args: str) -> None:
    app.exit_app()


def _reset_runtime_state(app: AppContext) -> None:
    """Best-effort reset of frontend-local runtime state after session changes."""
    for attr in ("_agent_loop", "_session_stats"):
        if hasattr(app, attr):
            setattr(app, attr, None)

    if hasattr(app, "_session_titled"):
        setattr(app, "_session_titled", False)

    if hasattr(app, "_session_approved_tools"):
        approved = getattr(app, "_session_approved_tools")
        if hasattr(approved, "clear"):
            approved.clear()

    from autocode.agent.tools import clear_observed_file_mtimes

    clear_observed_file_mtimes()


async def _handle_new(app: AppContext, args: str) -> None:
    title = args.strip() or "New session"
    session_id = app.session_store.create_session(
        title=title,
        model=app.config.llm.model,
        provider=app.config.llm.provider,
        project_dir=str(app.project_root),
    )
    app.session_id = session_id
    _reset_runtime_state(app)
    app.clear_messages()
    app.add_system_message(f"Started new session: {title}")


async def _handle_sessions(app: AppContext, args: str) -> None:
    sessions = app.session_store.list_sessions()
    if not sessions:
        app.add_system_message("No sessions found.")
        return
    lines = ["**Sessions:**"]
    for s in sessions[:10]:
        title = s.title or "(untitled)"
        if len(title) > 40:
            title = title[:37] + "..."
        lines.append(f"- `{s.id[:8]}` {title} ({s.model})")
    app.add_system_message("\n".join(lines))


async def _handle_resume(app: AppContext, args: str) -> None:
    session_id = args.strip()

    # No args: list available sessions with overview
    if not session_id:
        sessions = app.session_store.list_sessions()
        if not sessions:
            app.add_system_message("No sessions to resume.")
            return
        lines = ["**Sessions available to resume:**"]
        for s in sessions[:15]:
            # Build a short overview from first user message
            msgs = app.session_store.get_messages(s.id)
            overview = ""
            for m in msgs:
                if m.role == "user":
                    overview = m.content[:60].replace("\n", " ")
                    if len(m.content) > 60:
                        overview += "..."
                    break
            title_display = s.title or "Untitled"
            if len(title_display) > 40:
                title_display = title_display[:37] + "..."
            lines.append(f"- `{s.id[:8]}` **{title_display}** ({s.model})")
            if overview:
                lines.append(f"  _{overview}_")
        lines.append("\nUsage: `/resume <id-prefix>`")
        app.add_system_message("\n".join(lines))
        return

    sessions = app.session_store.list_sessions()
    match = None
    for s in sessions:
        if s.id.startswith(session_id):
            match = s
            break

    if match is None:
        app.add_system_message(f"Session not found: {session_id}")
        return

    app.session_id = match.id
    _reset_runtime_state(app)
    app.clear_messages()
    app.add_system_message(f"Resumed session: {match.title}")

    messages = app.session_store.get_messages(match.id)
    app.display_messages(messages)


# --- Sprint 2B command handlers ---


async def _handle_help(app: AppContext, args: str) -> None:
    lines = ["**Available commands:**"]
    for cmd in app.command_router.get_all():
        aliases_str = ""
        if cmd.aliases:
            aliases = ", ".join(f"/{a}" for a in cmd.aliases)
            aliases_str = f" ({aliases})"
        lines.append(f"- `/{cmd.name}`{aliases_str} — {cmd.description}")
    app.add_system_message("\n".join(lines))


async def _handle_model(app: AppContext, args: str) -> None:
    arg = args.strip()

    if not arg or arg == "list":
        provider = app.config.llm.provider
        api_base = app.config.llm.api_base
        current_model = app.config.llm.model

        lines = [f"**Current model:** {current_model}  (provider: {provider})"]
        available = _list_models(provider, api_base)
        if available:
            displayed, remaining = _prioritize_models(available, current_model)
            lines.append("**Available models:**")
            for m in displayed:
                marker = " (active)" if m == current_model else ""
                lines.append(f"- `{m}`{marker}")
            if remaining:
                lines.append(f"_...and {remaining} more models available_")
        elif provider == "ollama":
            lines.append("_Could not list Ollama models_")
        else:
            lines.append(f"_Could not list gateway models from {api_base}_")
        app.add_system_message("\n".join(lines))
        return

    app.config.llm.model = arg
    # Update status bar if available (Textual TUI only)
    if hasattr(app, "query_one"):
        from autocode.tui.widgets.status_bar import StatusBar

        status = app.query_one("#status-bar", StatusBar)
        status.model = arg
    app.add_system_message(f"Switched model to: {arg}")


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Windows":
            process = subprocess.Popen(
                ["clip.exe"],
                stdin=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text)
            return process.returncode == 0
        if system == "Darwin":
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text)
            return process.returncode == 0
        # Linux: try xclip, then xsel
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            try:
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
        return False
    except Exception:
        return False


def _list_ollama_models() -> list[str]:
    """Query Ollama for available models. Returns empty list on failure."""
    import subprocess

    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        models: list[str] = []
        for line in result.stdout.strip().splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []


_GATEWAY_DISPLAY_LIMIT = 20

_GATEWAY_PRIORITY_NAMES = frozenset(
    {
        "coding",
        "tools",
        "terminal_bench",
        "reasoning",
        "fast",
        "smart",
        "default",
        "chat",
    }
)


def _list_models(provider: str, api_base: str) -> list[str]:
    """List available models for the given provider."""
    if provider == "ollama":
        return _list_ollama_models()
    return _list_openai_models(api_base)


def _list_openai_models(api_base: str) -> list[str]:
    """Query an OpenAI-compatible /models endpoint. Returns sorted model IDs."""
    import json
    import urllib.request

    from autocode.gateway_auth import build_gateway_headers

    url = f"{api_base.rstrip('/')}/models"
    try:
        req = urllib.request.Request(url, headers=build_gateway_headers())
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        models = sorted(m["id"] for m in data.get("data", []) if "id" in m)
        return models
    except Exception:
        return []


def _prioritize_models(models: list[str], current_model: str) -> tuple[list[str], int]:
    """Sort models: current first, known aliases next, then alphabetical.

    Returns (displayed_list, remaining_count).
    If the catalog exceeds _GATEWAY_DISPLAY_LIMIT, truncate and report remainder.
    """
    if len(models) <= _GATEWAY_DISPLAY_LIMIT:
        return _sort_models(models, current_model), 0

    priority: list[str] = []
    rest: list[str] = []
    for m in models:
        if m == current_model or m in _GATEWAY_PRIORITY_NAMES:
            priority.append(m)
        else:
            rest.append(m)

    priority_sorted = _sort_models(priority, current_model)
    remaining_slots = _GATEWAY_DISPLAY_LIMIT - len(priority_sorted)
    if remaining_slots <= 0:
        return priority_sorted[:_GATEWAY_DISPLAY_LIMIT], len(models) - _GATEWAY_DISPLAY_LIMIT

    displayed = priority_sorted + sorted(rest)[:remaining_slots]
    remaining = len(models) - len(displayed)
    return displayed, remaining


def _sort_models(models: list[str], current_model: str) -> list[str]:
    """Sort: current model first, then known aliases, then alphabetical."""

    def _key(m: str) -> tuple[int, str]:
        if m == current_model:
            return (0, m)
        if m in _GATEWAY_PRIORITY_NAMES:
            return (1, m)
        return (2, m)

    return sorted(models, key=_key)


_SUPPORTED_PROVIDERS: tuple[str, ...] = ("ollama", "openrouter")


async def _handle_provider(app: AppContext, args: str) -> None:
    """Show, list, or switch the LLM provider.

    Usage:
        /provider              -> show current provider
        /provider list         -> list supported providers
        /provider <name>       -> switch to the given provider
    """
    arg = args.strip().lower()

    if not arg:
        current = app.config.llm.provider
        app.add_system_message(
            f"**Current provider:** `{current}`\n"
            f"Use `/provider list` to see available options or "
            f"`/provider <name>` to switch."
        )
        return

    if arg == "list":
        lines = ["**Available providers:**"]
        for name in _SUPPORTED_PROVIDERS:
            marker = " (active)" if name == app.config.llm.provider else ""
            lines.append(f"- `{name}`{marker}")
        app.add_system_message("\n".join(lines))
        return

    if arg not in _SUPPORTED_PROVIDERS:
        app.add_system_message(
            f"Invalid provider: `{arg}`. Choose: {', '.join(_SUPPORTED_PROVIDERS)}"
        )
        return

    app.config.llm.provider = arg
    if hasattr(app, "query_one"):
        try:
            from autocode.tui.widgets.status_bar import StatusBar

            status = app.query_one("#status-bar", StatusBar)
            if hasattr(status, "provider"):
                status.provider = arg
        except Exception:
            pass
    app.add_system_message(f"Switched provider to: {arg}")


async def _handle_mode(app: AppContext, args: str) -> None:
    valid_modes = ("read-only", "suggest", "auto", "autonomous")
    if not args.strip():
        app.add_system_message(f"Current mode: {app.approval_mode}")
        return
    mode = args.strip().lower()
    if mode not in valid_modes:
        app.add_system_message(f"Invalid mode. Choose: {', '.join(valid_modes)}")
        return
    app.approval_mode = mode
    # Update status bar if available (Textual TUI only)
    if hasattr(app, "query_one"):
        from autocode.tui.widgets.status_bar import StatusBar

        status = app.query_one("#status-bar", StatusBar)
        status.mode = mode
    app.add_system_message(f"Switched to {mode} mode.")


async def _handle_tui(app: AppContext, args: str) -> None:
    arg = args.strip().lower()
    current = "altscreen" if app.config.tui.alternate_screen else "inline"

    if not arg or arg == "status":
        app.add_system_message(
            f"Current TUI launch mode: **{current}**\n"
            "Use `/tui inline` or `/tui altscreen` to save the default for future launches."
        )
        return

    if arg not in {"inline", "altscreen"}:
        app.add_system_message("Invalid TUI mode. Choose: inline, altscreen")
        return

    app.config.tui.alternate_screen = arg == "altscreen"
    try:
        path = save_config(app.config)
    except Exception as e:
        app.add_system_message(f"Failed to save TUI mode: {e}")
        return

    app.add_system_message(
        f"Saved TUI launch mode: **{arg}** (saved to `{path}`). "
        "Restart AutoCode to use the new default."
    )


async def _handle_compact(app: AppContext, args: str) -> None:
    messages = app.session_store.get_messages(app.session_id)
    if len(messages) <= 4:
        app.add_system_message("Not enough messages to compact.")
        return

    summary_parts = [f"{m.role}: {m.content[:100]}" for m in messages[:-4]]
    summary = "Summary of previous conversation:\n" + "\n".join(
        summary_parts,
    )

    app.session_store.compact_session(app.session_id, summary=summary)
    app.add_system_message("Compacted session. Kept last 4 messages.")


async def _handle_shell(app: AppContext, args: str) -> None:
    arg = args.strip().lower()

    if arg in ("on", "enable", "true"):
        app.shell_enabled = True
        app.add_system_message("Shell execution enabled.")
    elif arg in ("off", "disable", "false"):
        app.shell_enabled = False
        app.add_system_message("Shell execution disabled.")
    else:
        status = "enabled" if app.config.shell.enabled else "disabled"
        app.add_system_message(
            f"Shell execution is **{status}**.\nUsage: `/shell on` or `/shell off`",
        )


async def _handle_copy(app: AppContext, args: str) -> None:
    arg = args.strip()

    messages = app.session_store.get_messages(app.session_id)

    if arg.lower() == "all":
        # /copy all — every message
        text = "\n\n".join(f"{m.role}: {m.content}" for m in messages)
    elif arg.lower().startswith("last"):
        # /copy last N — last N messages (all roles)
        count_str = arg[4:].strip()
        try:
            count = int(count_str) if count_str else 3
        except ValueError:
            app.add_system_message("Usage: `/copy last N` (e.g. `/copy last 5`)")
            return
        tail = messages[-count:] if count <= len(messages) else messages
        text = "\n\n".join(f"{m.role}: {m.content}" for m in tail)
    elif arg.isdigit():
        # /copy N — Nth-last assistant message (1 = most recent)
        n = int(arg)
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        if not assistant_msgs:
            app.add_system_message("No assistant messages to copy.")
            return
        if n < 1 or n > len(assistant_msgs):
            app.add_system_message(
                f"Only {len(assistant_msgs)} assistant messages. Use 1-{len(assistant_msgs)}.",
            )
            return
        text = assistant_msgs[-n].content
    else:
        # /copy (no args) — last assistant message
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        if not assistant_msgs:
            app.add_system_message("No assistant messages to copy.")
            return
        text = assistant_msgs[-1].content

    if app.copy_to_clipboard(text):
        app.add_system_message(f"Copied {len(text)} characters to clipboard.")
    else:
        # Fallback: show text in chat for manual copy
        preview = text[:500]
        if len(text) > 500:
            preview += "\n...(truncated)"
        app.add_system_message(f"Clipboard unavailable. Text:\n```\n{preview}\n```")


async def _handle_thinking(app: AppContext, args: str) -> None:
    app.show_thinking = not app.show_thinking
    state = "on" if app.show_thinking else "off"
    app.add_system_message(f"Thinking: **{state}**")


async def _handle_clear(app: AppContext, args: str) -> None:
    # Print ANSI clear sequence + reprint welcome banner
    import sys

    # In JSON-RPC backend mode stdout is the wire protocol, not a terminal.
    # Guard raw ANSI writes to avoid corrupting RPC framing.
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    app.add_system_message("Screen cleared.")


async def _handle_loop(app: AppContext, args: str) -> None:
    """Manage recurring session-scoped loop jobs."""
    arg = args.strip()
    jobs, next_id = _ensure_loop_state(app)
    _cleanup_finished_loop_jobs(app)

    if not arg:
        app.add_system_message(
            "Usage: `/loop <interval> <payload>`, `/loop list`, `/loop cancel <id>`"
        )
        return

    lowered = arg.lower()
    if lowered in {"list", "ls"}:
        if not jobs:
            app.add_system_message("No active loop jobs.")
            return
        lines = ["**Loop jobs:**"]
        for job in sorted(jobs.values(), key=lambda item: item.id):
            status = "running" if job.running else "idle"
            if job.cancelled:
                status = "cancelled"
            lines.append(
                f"- `#{job.id}` every {_format_interval(job.interval_seconds)} "
                f"{status} runs={job.run_count} skipped={job.skipped_count} :: {job.payload}"
            )
        app.add_system_message("\n".join(lines))
        return

    if lowered.startswith("cancel"):
        parts = arg.split()
        if len(parts) != 2 or not parts[1].isdigit():
            app.add_system_message("Usage: `/loop cancel <id>`")
            return
        job_id = int(parts[1])
        job = jobs.get(job_id)
        if job is None:
            app.add_system_message(f"Loop job not found: {job_id}")
            return
        _cancel_loop_job(job)
        if job.task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await job.task
        jobs.pop(job_id, None)
        app.add_system_message(f"Cancelled loop #{job_id}.")
        return

    parts = arg.split(maxsplit=1)
    if len(parts) != 2:
        app.add_system_message(
            "Usage: `/loop <interval> <payload>` (example: `/loop 10m /checkpoint save autosnap`)"
        )
        return

    interval_seconds = _parse_loop_interval(parts[0])
    payload = parts[1].strip()
    if interval_seconds is None:
        app.add_system_message("Invalid interval. Use forms like `30s`, `5m`, or `1h`.")
        return
    if not payload:
        app.add_system_message("Loop payload cannot be empty.")
        return

    job_id = next_id
    setattr(app, "_loop_next_id", job_id + 1)
    job = LoopJob(
        id=job_id,
        interval_seconds=interval_seconds,
        payload=payload,
    )
    task = asyncio.create_task(_run_loop_job(app, job))
    job.task = task
    jobs[job_id] = job

    app.add_system_message(
        f"Started loop #{job_id}: every {_format_interval(interval_seconds)} -> `{payload}`"
    )


async def _handle_plan(app: AppContext, args: str) -> None:
    """Toggle or query plan mode, or export/sync plan artifacts."""
    arg = args.strip().lower()

    if not arg:
        app.add_system_message(
            "Usage: `/plan on` (enter plan mode), "
            "`/plan approve` or `/plan off` (exit plan mode), "
            "`/plan export` (save plan), `/plan sync <path>` (sync from markdown)"
        )
        return

    if arg == "on":
        if hasattr(app, "set_plan_mode"):
            app.set_plan_mode(True)  # type: ignore[attr-defined]
            app.add_system_message(
                "**Plan mode ON** — tools that modify files or run commands are "
                "blocked. Use `/plan approve` to switch to execution mode."
            )
        else:
            app.add_system_message("Plan mode is not supported in this context.")
    elif arg in ("off", "approve"):
        if hasattr(app, "set_plan_mode"):
            app.set_plan_mode(False)  # type: ignore[attr-defined]
            app.add_system_message("**Plan mode OFF** — all tools are available.")
        else:
            app.add_system_message("Plan mode is not supported in this context.")
    elif arg == "export":
        try:
            from autocode.agent.plan_artifact import export
            from autocode.session.task_store import TaskStore

            conn = app.session_store.get_connection()
            task_store = TaskStore(conn, app.session_id)
            path = export(app.session_id, task_store, project_root=app.project_root)
            app.add_system_message(f"Plan exported to: {path}")
        except Exception as e:
            app.add_system_message(f"Export failed: {e}")
    elif arg.startswith("sync"):
        sync_path = args.strip()[4:].strip()
        if not sync_path:
            app.add_system_message("Usage: `/plan sync <path-to-markdown>`")
            return
        try:
            from autocode.agent.plan_artifact import sync_from_markdown
            from autocode.session.task_store import TaskStore

            conn = app.session_store.get_connection()
            task_store = TaskStore(conn, app.session_id)
            updated = sync_from_markdown(app.session_id, task_store, sync_path)
            if updated:
                app.add_system_message(f"Synced {len(updated)} tasks: {', '.join(updated)}")
            else:
                app.add_system_message("No task status changes found in plan file.")
        except Exception as e:
            app.add_system_message(f"Sync failed: {e}")
    else:
        app.add_system_message(
            f"Unknown plan argument: {arg}. "
            "Use: `/plan on`, `/plan off`, `/plan approve`, `/plan export`, `/plan sync <path>`"
        )


async def _handle_research(app: AppContext, args: str) -> None:
    """Toggle or query research mode."""
    arg = args.strip().lower()

    if not arg:
        app.add_system_message(
            "Usage: `/research on` (enter read-only comprehension mode), "
            "`/research off` (return to normal execution), `/research status`"
        )
        return

    if arg == "on":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.RESEARCH)
            app.add_system_message(
                "**Research mode ON** — file mutations and shell commands are "
                "blocked. Use this mode to locate candidate files/symbols and "
                "produce a concise implementation handoff."
            )
        else:
            app.add_system_message("Research mode is not supported in this context.")
    elif arg == "off":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.NORMAL)
            app.add_system_message("**Research mode OFF** — all tools are available.")
        else:
            app.add_system_message("Research mode is not supported in this context.")
    elif arg == "status":
        mode = "unknown"
        if hasattr(app, "_agent_mode"):
            mode_obj = getattr(app, "_agent_mode")
            mode = getattr(mode_obj, "value", str(mode_obj))
        elif hasattr(app, "_plan_mode_enabled"):
            mode = "planning" if getattr(app, "_plan_mode_enabled") else "normal"
        app.add_system_message(f"**Current agent mode:** {mode}")
    else:
        app.add_system_message(
            f"Unknown research argument: {arg}. "
            "Use: `/research on`, `/research off`, `/research status`"
        )


async def _handle_build(app: AppContext, args: str) -> None:
    """Toggle build mode — edits allowed, verification required."""
    arg = args.strip().lower()
    if arg == "on":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.BUILD)
            app.add_system_message(
                "**Build mode ON** — edits and commands allowed. "
                "Verification is required before marking tasks complete."
            )
        else:
            app.add_system_message("Build mode is not supported in this context.")
    elif arg == "off":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.NORMAL)
            app.add_system_message("**Build mode OFF** — back to normal mode.")
        else:
            app.add_system_message("Build mode is not supported in this context.")
    else:
        app.add_system_message("Usage: `/build on` (verification required), `/build off`")


async def _handle_review(app: AppContext, args: str) -> None:
    """Toggle review mode — read-only, produces risk summary."""
    arg = args.strip().lower()
    if arg == "on":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.REVIEW)
            app.add_system_message(
                "**Review mode ON** — read-only. File edits and shell commands "
                "are blocked. Review diffs, verify evidence, produce risk summary."
            )
        else:
            app.add_system_message("Review mode is not supported in this context.")
    elif arg == "off":
        if hasattr(app, "set_agent_mode"):
            app.set_agent_mode(AgentMode.NORMAL)
            app.add_system_message("**Review mode OFF** — all tools available.")
        else:
            app.add_system_message("Review mode is not supported in this context.")
    else:
        app.add_system_message("Usage: `/review on` (read-only review), `/review off`")


async def _handle_memory(app: AppContext, args: str) -> None:
    """Show learned patterns from MemoryStore."""
    try:
        from autocode.agent.memory import MemoryStore
        from autocode.session.models import ensure_tables

        conn = app.session_store.get_connection()
        ensure_tables(conn)
        project_id = str(app.project_root)
        store = MemoryStore(conn, project_id)
        memories = store.get_memories(limit=20)
        if not memories:
            app.add_system_message("No learned patterns yet.")
            return
        lines = ["**Learned Patterns:**"]
        for mem in memories:
            lines.append(
                f"- [{mem['category']}] {mem['content'][:80]} (relevance: {mem['relevance']:.2f})"
            )
        app.add_system_message("\n".join(lines))
    except Exception as e:
        app.add_system_message(f"Error loading memories: {e}")


async def _handle_checkpoint(app: AppContext, args: str) -> None:
    """List or save checkpoints."""
    try:
        from autocode.session.checkpoint_store import CheckpointStore
        from autocode.session.models import ensure_tables
        from autocode.session.task_store import TaskStore

        conn = app.session_store.get_connection()
        ensure_tables(conn)

        arg = args.strip().lower()
        if arg.startswith("save"):
            label = args.strip()[4:].strip() or "checkpoint"
            task_store = TaskStore(conn, app.session_id)
            cp_store = CheckpointStore(conn, app.session_id)
            cp_id = cp_store.save_checkpoint(task_store, label)
            app.add_system_message(f"Checkpoint saved: `{cp_id}` ({label})")
        elif arg.startswith("restore"):
            cp_id = args.strip()[7:].strip()
            if not cp_id:
                app.add_system_message(
                    "Usage: `/checkpoint restore <id>` — use `/checkpoint` to list IDs."
                )
                return
            task_store = TaskStore(conn, app.session_id)
            cp_store = CheckpointStore(conn, app.session_id)
            result = cp_store.restore_checkpoint(cp_id, task_store, app.session_store)
            app.add_system_message(
                f"Restored checkpoint: **{result['label']}**\n"
                f"Active files: {', '.join(result.get('active_files', []))}"
            )
        else:
            cp_store = CheckpointStore(conn, app.session_id)
            checkpoints = cp_store.list_checkpoints()
            if not checkpoints:
                app.add_system_message(
                    "No checkpoints. Use `/checkpoint save <label>` to create one."
                )
                return
            lines = ["**Checkpoints:**"]
            for cp in checkpoints:
                lines.append(f"- `{cp.id}` {cp.label} ({cp.created_at})")
            app.add_system_message("\n".join(lines))
    except Exception as e:
        app.add_system_message(f"Error: {e}")


async def _handle_tasks(app: AppContext, args: str) -> None:
    """Show the task board for the current session."""
    try:
        from autocode.session.task_store import TaskStore

        conn = app.session_store.get_connection()
        task_store = TaskStore(conn, app.session_id)
        summary = task_store.summary()
        app.add_system_message(f"**Tasks:**\n{summary}")
    except Exception as e:
        app.add_system_message(f"Error loading tasks: {e}")


async def _handle_index(app: AppContext, args: str) -> None:
    """Build or rebuild the code index for the current project."""
    try:
        from autocode.agent.tools import clear_code_index_cache, set_code_index_cache
        from autocode.layer2.index import CodeIndex

        clear_code_index_cache()
        app.add_system_message("Building code index...")
        index = CodeIndex()
        stats = index.build(app.project_root)
        set_code_index_cache(index)
        app.add_system_message(
            f"Index built: {stats['files_scanned']} files scanned, "
            f"{stats['files_indexed']} indexed, "
            f"{stats['total_chunks']} chunks, "
            f"{stats['time_ms']}ms"
        )
    except ImportError:
        app.add_system_message(
            "Layer 2 dependencies not installed. Run: uv pip install -e '.[layer1,layer2]'"
        )
    except Exception as e:
        app.add_system_message(f"Index build failed: {e}")


async def _handle_freeze(app: AppContext, args: str) -> None:
    # Textual TUI has a frozen ChatView; inline mode uses native scrollback
    if hasattr(app, "query_one"):
        from autocode.tui.widgets.chat_view import ChatView

        chat = app.query_one("#chat-view", ChatView)
        if chat.frozen:
            chat.unfreeze()
            app.add_system_message("Auto-scroll resumed.")
        else:
            chat.freeze()
            app.add_system_message(
                "Auto-scroll paused. Use PageUp/PageDown to scroll. Use `/freeze` again to resume.",
            )
    else:
        app.add_system_message(
            "Scroll-lock is not needed in inline mode — use your terminal's native scrollback."
        )


async def _handle_init(app: AppContext, args: str) -> None:
    memory_dir = app.project_root / ".autocode"
    memory_file = memory_dir / "memory.md"

    if memory_file.exists():
        app.add_system_message(f"Memory file already exists: {memory_file}")
        return

    lines = ["# Project Memory\n"]
    key_files = [
        "README.md",
        "pyproject.toml",
        "CLAUDE.md",
        "package.json",
        "Cargo.toml",
    ]
    for name in key_files:
        path = app.project_root / name
        if path.exists():
            content = path.read_text(encoding="utf-8")[:500]
            lines.append(f"## {name}\n```\n{content}\n```\n")

    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_file.write_text("\n".join(lines), encoding="utf-8")
    app.add_system_message(f"Created project memory at {memory_file}")


def create_default_router() -> CommandRouter:
    """Create router with all slash commands."""
    router = CommandRouter()

    # Sprint 2A commands
    router.register(
        SlashCommand(
            name="exit",
            aliases=["quit", "q"],
            description="Quit the application",
            handler=_handle_exit,
        )
    )
    router.register(
        SlashCommand(
            name="new",
            aliases=[],
            description="Start a new session",
            handler=_handle_new,
        )
    )
    router.register(
        SlashCommand(
            name="sessions",
            aliases=["s"],
            description="List sessions",
            handler=_handle_sessions,
        )
    )
    router.register(
        SlashCommand(
            name="resume",
            aliases=[],
            description="Resume a session by ID",
            handler=_handle_resume,
        )
    )

    # Sprint 2B commands
    router.register(
        SlashCommand(
            name="help",
            aliases=["h", "?"],
            description="Show available commands",
            handler=_handle_help,
        )
    )
    router.register(
        SlashCommand(
            name="model",
            aliases=["m"],
            description="Show or switch the LLM model",
            handler=_handle_model,
        )
    )
    router.register(
        SlashCommand(
            name="provider",
            aliases=[],
            description="Show, list, or switch the LLM provider",
            handler=_handle_provider,
        )
    )
    router.register(
        SlashCommand(
            name="mode",
            aliases=["permissions"],
            description="Show or switch approval mode",
            handler=_handle_mode,
        )
    )
    router.register(
        SlashCommand(
            name="tui",
            aliases=["screen"],
            description="Show or save the default Rust TUI launch mode",
            handler=_handle_tui,
        )
    )
    router.register(
        SlashCommand(
            name="compact",
            aliases=[],
            description="Compact session history",
            handler=_handle_compact,
        )
    )
    router.register(
        SlashCommand(
            name="init",
            aliases=[],
            description="Create project memory file",
            handler=_handle_init,
        )
    )
    router.register(
        SlashCommand(
            name="shell",
            aliases=[],
            description="Enable or disable shell execution",
            handler=_handle_shell,
        )
    )
    router.register(
        SlashCommand(
            name="copy",
            aliases=["cp"],
            description="Copy last response (/copy N, /copy all, /copy last N)",
            handler=_handle_copy,
        )
    )
    router.register(
        SlashCommand(
            name="freeze",
            aliases=["scroll-lock"],
            description="Toggle auto-scroll (pause for text selection)",
            handler=_handle_freeze,
        )
    )
    router.register(
        SlashCommand(
            name="thinking",
            aliases=["think"],
            description="Toggle thinking token visibility",
            handler=_handle_thinking,
        )
    )
    router.register(
        SlashCommand(
            name="clear",
            aliases=["cls"],
            description="Clear the terminal screen",
            handler=_handle_clear,
        )
    )
    router.register(
        SlashCommand(
            name="loop",
            aliases=[],
            description="Recurring jobs: /loop <interval> <payload>, /loop list, /loop cancel <id>",
            handler=_handle_loop,
        )
    )
    router.register(
        SlashCommand(
            name="index",
            aliases=[],
            description="Build or rebuild the code search index",
            handler=_handle_index,
        )
    )
    router.register(
        SlashCommand(
            name="tasks",
            aliases=["t"],
            description="Show task board",
            handler=_handle_tasks,
        )
    )
    router.register(
        SlashCommand(
            name="plan",
            aliases=[],
            description="Plan mode: /plan on, /plan approve, /plan off, /plan export, /plan sync",
            handler=_handle_plan,
        )
    )
    router.register(
        SlashCommand(
            name="research",
            aliases=["comprehend"],
            description="Research mode: /research on, /research off, /research status",
            handler=_handle_research,
        )
    )
    router.register(
        SlashCommand(
            name="build",
            description="Build mode: /build on (verification required), /build off",
            handler=_handle_build,
        )
    )
    router.register(
        SlashCommand(
            name="review",
            description="Review mode: /review on (read-only review), /review off",
            handler=_handle_review,
        )
    )
    router.register(
        SlashCommand(
            name="memory",
            aliases=["mem"],
            description="Show learned patterns",
            handler=_handle_memory,
        )
    )
    router.register(
        SlashCommand(
            name="checkpoint",
            aliases=["ckpt"],
            description="List or save checkpoints: /checkpoint, /checkpoint save <label>",
            handler=_handle_checkpoint,
        )
    )
    router.register(
        SlashCommand(
            name="undo",
            aliases=[],
            description="Undo: restore the most recent checkpoint",
            handler=_handle_undo,
        )
    )
    router.register(
        SlashCommand(
            name="diff",
            aliases=[],
            description="Show git diff of changes in the current session",
            handler=_handle_diff,
        )
    )
    router.register(
        SlashCommand(
            name="cost",
            aliases=["tokens", "usage"],
            description="Show token usage and estimated cost for this session",
            handler=_handle_cost,
        )
    )
    router.register(
        SlashCommand(
            name="export",
            aliases=[],
            description="Export conversation to markdown file",
            handler=_handle_export,
        )
    )
    return router


async def _handle_undo(app: AppContext, args: str) -> None:
    """Restore the most recent checkpoint (undo last agent action)."""
    try:
        from autocode.session.checkpoint_store import CheckpointStore
        from autocode.session.models import ensure_tables
        from autocode.session.task_store import TaskStore

        conn = app.session_store.get_connection()
        ensure_tables(conn)
        cp_store = CheckpointStore(conn, app.session_id)
        checkpoints = cp_store.list_checkpoints()
        if not checkpoints:
            app.add_system_message("Nothing to undo — no checkpoints saved yet.")
            return
        latest = checkpoints[-1]
        task_store = TaskStore(conn, app.session_id)
        result = cp_store.restore_checkpoint(latest.id, task_store, app.session_store)
        app.add_system_message(f"Undone to checkpoint: **{result['label']}**")
    except Exception as e:
        app.add_system_message(f"Undo failed: {e}")


async def _handle_diff(app: AppContext, args: str) -> None:
    """Show git diff of changes in the current working directory."""
    import subprocess

    try:
        proc = subprocess.run(
            "git diff --stat && echo '---' && git diff",
            shell=True,
            cwd=str(app.project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            app.add_system_message(f"git diff failed: {proc.stderr[:200]}")
            return
        output = proc.stdout.strip()
        if not output or output == "---":
            app.add_system_message("No changes detected.")
            return
        if len(output) > 3000:
            output = output[:3000] + "\n...(truncated)"
        app.add_system_message(f"```diff\n{output}\n```")
    except Exception as e:
        app.add_system_message(f"Error running diff: {e}")


async def _handle_cost(app: AppContext, args: str) -> None:
    """Show token usage and estimated cost for the current session."""
    messages = app.session_store.get_messages(app.session_id)
    total_chars = sum(len(m.content) for m in messages)
    est_tokens = total_chars // 4
    user_msgs = sum(1 for m in messages if m.role == "user")
    assistant_msgs = sum(1 for m in messages if m.role == "assistant")
    tool_msgs = sum(1 for m in messages if m.role == "tool")

    lines = [
        "**Session Usage:**",
        f"- Messages: {len(messages)}"
        f" ({user_msgs} user, {assistant_msgs} assistant, {tool_msgs} tool)",
        f"- Estimated tokens: ~{est_tokens:,}",
        f"- Provider: {app.config.llm.provider} / {app.config.llm.model}",
    ]
    app.add_system_message("\n".join(lines))


async def _handle_export(app: AppContext, args: str) -> None:
    """Export conversation history to a markdown file."""
    from pathlib import Path

    messages = app.session_store.get_messages(app.session_id)
    if not messages:
        app.add_system_message("No messages to export.")
        return

    lines = [f"# Session {app.session_id[:8]}\n"]
    for m in messages:
        lines.append(f"## {m.role.capitalize()}\n\n{m.content}\n")

    filename = args.strip() or f"session-{app.session_id[:8]}.md"
    out_path = Path(app.project_root) / filename
    try:
        out_path.write_text("\n".join(lines), encoding="utf-8")
        app.add_system_message(f"Exported to `{out_path}`")
    except Exception as e:
        app.add_system_message(f"Export failed: {e}")
