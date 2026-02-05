"""Slash command router for the TUI."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hybridcoder.tui.app import HybridCoderApp


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


def _get_chat(app: HybridCoderApp) -> Any:
    """Get the ChatView widget from the app."""
    from hybridcoder.tui.widgets.chat_view import ChatView

    return app.query_one("#chat-view", ChatView)


def _get_status(app: HybridCoderApp) -> Any:
    """Get the StatusBar widget from the app."""
    from hybridcoder.tui.widgets.status_bar import StatusBar

    return app.query_one("#status-bar", StatusBar)


# --- Sprint 2A command handlers ---


async def _handle_exit(app: HybridCoderApp, args: str) -> None:
    app.exit()


async def _handle_new(app: HybridCoderApp, args: str) -> None:
    title = args.strip() or "New session"
    session_id = app.session_store.create_session(
        title=title,
        model=app.config.llm.model,
        provider=app.config.llm.provider,
        project_dir=str(app.project_root),
    )
    app.session_id = session_id
    chat = _get_chat(app)
    chat.remove_children()
    chat.add_message("system", f"Started new session: {title}")


async def _handle_sessions(app: HybridCoderApp, args: str) -> None:
    sessions = app.session_store.list_sessions()
    chat = _get_chat(app)
    if not sessions:
        chat.add_message("system", "No sessions found.")
        return
    lines = ["**Sessions:**"]
    for s in sessions[:10]:
        lines.append(f"- `{s.id[:8]}` {s.title} ({s.model})")
    chat.add_message("system", "\n".join(lines))


async def _handle_resume(app: HybridCoderApp, args: str) -> None:
    session_id = args.strip()
    chat = _get_chat(app)

    # No args: list available sessions with overview
    if not session_id:
        sessions = app.session_store.list_sessions()
        if not sessions:
            chat.add_message("system", "No sessions to resume.")
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
            lines.append(f"- `{s.id[:8]}` **{title_display}** ({s.model})")
            if overview:
                lines.append(f"  _{overview}_")
        lines.append("\nUsage: `/resume <id-prefix>`")
        chat.add_message("system", "\n".join(lines))
        return

    sessions = app.session_store.list_sessions()
    match = None
    for s in sessions:
        if s.id.startswith(session_id):
            match = s
            break

    if match is None:
        chat.add_message("system", f"Session not found: {session_id}")
        return

    app.session_id = match.id
    chat.remove_children()
    chat.add_message("system", f"Resumed session: {match.title}")

    messages = app.session_store.get_messages(match.id)
    for msg in messages:
        chat.add_message(msg.role, msg.content)


# --- Sprint 2B command handlers ---


async def _handle_help(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    lines = ["**Available commands:**"]
    for cmd in app.command_router.get_all():
        aliases_str = ""
        if cmd.aliases:
            aliases = ", ".join(f"/{a}" for a in cmd.aliases)
            aliases_str = f" ({aliases})"
        lines.append(f"- `/{cmd.name}`{aliases_str} — {cmd.description}")
    chat.add_message("system", "\n".join(lines))


async def _handle_model(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    arg = args.strip()

    if not arg or arg == "list":
        lines = [f"**Current model:** {app.config.llm.model}"]
        # Try to list available models from Ollama
        available = _list_ollama_models()
        if available:
            lines.append("**Available models:**")
            for m in available:
                marker = " (active)" if m == app.config.llm.model else ""
                lines.append(f"- `{m}`{marker}")
        else:
            lines.append("_Could not list models (Ollama not running?)_")
        chat.add_message("system", "\n".join(lines))
        return

    app.config.llm.model = arg
    status = _get_status(app)
    status.model = arg
    chat.add_message("system", f"Switched model to: {arg}")


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Windows":
            process = subprocess.Popen(
                ["clip.exe"], stdin=subprocess.PIPE, text=True,
            )
            process.communicate(input=text)
            return process.returncode == 0
        if system == "Darwin":
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE, text=True,
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
            capture_output=True, text=True, timeout=5,
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


async def _handle_mode(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    valid_modes = ("read-only", "suggest", "auto")
    if not args.strip():
        chat.add_message(
            "system", f"Current mode: {app.config.tui.approval_mode}",
        )
        return
    mode = args.strip().lower()
    if mode not in valid_modes:
        chat.add_message(
            "system", f"Invalid mode. Choose: {', '.join(valid_modes)}",
        )
        return
    app.config.tui.approval_mode = mode  # type: ignore[assignment]
    status = _get_status(app)
    status.mode = mode
    if hasattr(app, "_approval_manager") and app._approval_manager is not None:
        from hybridcoder.agent.approval import ApprovalMode

        app._approval_manager.mode = ApprovalMode(mode)
    chat.add_message("system", f"Switched to {mode} mode.")


async def _handle_compact(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    messages = app.session_store.get_messages(app.session_id)
    if len(messages) <= 4:
        chat.add_message("system", "Not enough messages to compact.")
        return

    summary_parts = [
        f"{m.role}: {m.content[:100]}" for m in messages[:-4]
    ]
    summary = "Summary of previous conversation:\n" + "\n".join(
        summary_parts,
    )

    app.session_store.compact_session(app.session_id, summary=summary)
    chat.add_message("system", "Compacted session. Kept last 4 messages.")


async def _handle_shell(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    arg = args.strip().lower()

    if arg in ("on", "enable", "true"):
        app.config.shell.enabled = True
        if app._approval_manager is not None:
            app._approval_manager.shell_config.enabled = True
        chat.add_message("system", "Shell execution enabled.")
    elif arg in ("off", "disable", "false"):
        app.config.shell.enabled = False
        if app._approval_manager is not None:
            app._approval_manager.shell_config.enabled = False
        chat.add_message("system", "Shell execution disabled.")
    else:
        status = "enabled" if app.config.shell.enabled else "disabled"
        chat.add_message(
            "system",
            f"Shell execution is **{status}**.\n"
            "Usage: `/shell on` or `/shell off`",
        )


async def _handle_copy(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
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
            chat.add_message("system", "Usage: `/copy last N` (e.g. `/copy last 5`)")
            return
        tail = messages[-count:] if count <= len(messages) else messages
        text = "\n\n".join(f"{m.role}: {m.content}" for m in tail)
    elif arg.isdigit():
        # /copy N — Nth-last assistant message (1 = most recent)
        n = int(arg)
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        if not assistant_msgs:
            chat.add_message("system", "No assistant messages to copy.")
            return
        if n < 1 or n > len(assistant_msgs):
            chat.add_message(
                "system",
                f"Only {len(assistant_msgs)} assistant messages. Use 1-{len(assistant_msgs)}.",
            )
            return
        text = assistant_msgs[-n].content
    else:
        # /copy (no args) — last assistant message
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        if not assistant_msgs:
            chat.add_message("system", "No assistant messages to copy.")
            return
        text = assistant_msgs[-1].content

    if _copy_to_clipboard(text):
        chat.add_message("system", f"Copied {len(text)} characters to clipboard.")
    else:
        # Fallback: show text in chat for manual copy
        preview = text[:500]
        if len(text) > 500:
            preview += "\n...(truncated)"
        chat.add_message("system", f"Clipboard unavailable. Text:\n```\n{preview}\n```")


async def _handle_freeze(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    if chat.frozen:
        chat.unfreeze()
        chat.add_message("system", "Auto-scroll resumed.")
    else:
        chat.freeze()
        message = (
            "Auto-scroll paused. Use PageUp/PageDown to scroll. "
            "Use `/freeze` again to resume."
        )
        chat.add_message("system", message)


async def _handle_init(app: HybridCoderApp, args: str) -> None:
    chat = _get_chat(app)
    memory_dir = app.project_root / ".hybridcoder"
    memory_file = memory_dir / "memory.md"

    if memory_file.exists():
        chat.add_message(
            "system", f"Memory file already exists: {memory_file}",
        )
        return

    lines = ["# Project Memory\n"]
    key_files = [
        "README.md", "pyproject.toml", "CLAUDE.md",
        "package.json", "Cargo.toml",
    ]
    for name in key_files:
        path = app.project_root / name
        if path.exists():
            content = path.read_text(encoding="utf-8")[:500]
            lines.append(f"## {name}\n```\n{content}\n```\n")

    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_file.write_text("\n".join(lines), encoding="utf-8")
    chat.add_message(
        "system", f"Created project memory at {memory_file}",
    )


def create_default_router() -> CommandRouter:
    """Create router with all slash commands."""
    router = CommandRouter()

    # Sprint 2A commands
    router.register(SlashCommand(
        name="exit", aliases=["quit", "q"],
        description="Quit the application",
        handler=_handle_exit,
    ))
    router.register(SlashCommand(
        name="new", aliases=[],
        description="Start a new session",
        handler=_handle_new,
    ))
    router.register(SlashCommand(
        name="sessions", aliases=["s"],
        description="List sessions",
        handler=_handle_sessions,
    ))
    router.register(SlashCommand(
        name="resume", aliases=[],
        description="Resume a session by ID",
        handler=_handle_resume,
    ))

    # Sprint 2B commands
    router.register(SlashCommand(
        name="help", aliases=["h", "?"],
        description="Show available commands",
        handler=_handle_help,
    ))
    router.register(SlashCommand(
        name="model", aliases=["m"],
        description="Show or switch the LLM model",
        handler=_handle_model,
    ))
    router.register(SlashCommand(
        name="mode", aliases=["permissions"],
        description="Show or switch approval mode",
        handler=_handle_mode,
    ))
    router.register(SlashCommand(
        name="compact", aliases=[],
        description="Compact session history",
        handler=_handle_compact,
    ))
    router.register(SlashCommand(
        name="init", aliases=[],
        description="Create project memory file",
        handler=_handle_init,
    ))
    router.register(SlashCommand(
        name="shell", aliases=[],
        description="Enable or disable shell execution",
        handler=_handle_shell,
    ))
    router.register(SlashCommand(
        name="copy", aliases=["cp"],
        description="Copy last response (/copy N, /copy all, /copy last N)",
        handler=_handle_copy,
    ))
    router.register(SlashCommand(
        name="freeze", aliases=["scroll-lock"],
        description="Toggle auto-scroll (pause for text selection)",
        handler=_handle_freeze,
    ))
    return router
