"""CLI entry point for AutoCode.

Typer app with commands: chat, ask, edit, config, version.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from autocode.config import (
    AutoCodeConfig,
    check_config,
    get_config_path,
    load_config,
)

if TYPE_CHECKING:
    from autocode.layer4.llm import OllamaProvider, OpenRouterProvider

app = typer.Typer(
    name="autocode",
    help="Edge-native AI coding assistant.",
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console()
telemetry_app = typer.Typer(help="Inspect local AutoCode telemetry.")
app.add_typer(telemetry_app, name="telemetry")
kairos_app = typer.Typer(help="Inspect KAIROS proactive-mode state.")
app.add_typer(kairos_app, name="kairos")

# Anvil — offline harness-evolution engine (PLAN_04/PLAN_05 copycat mode).
from autocode.anvil.cli import anvil_app  # noqa: E402

app.add_typer(anvil_app, name="anvil")

# Anvil teacher mode (PLAN_04) — mounted as `autocode anvil teacher ...`.
from autocode.anvil.teacher.cli import teacher_app  # noqa: E402

anvil_app.add_typer(teacher_app, name="teacher")


def _version_callback(value: bool) -> None:
    if value:
        from autocode import __version__

        console.print(f"autocode {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _default(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Default chat launch mode: inline or altscreen.",
    ),
    attach: str | None = typer.Option(
        None,
        "--attach",
        help="Attach the Rust TUI to an already-running backend at HOST:PORT.",
    ),
) -> None:
    """Edge-native AI coding assistant."""
    if ctx.invoked_subcommand is None:
        # Call chat with explicit defaults — Typer's OptionInfo objects
        # are truthy, so bare chat() would hit the legacy path
        chat(
            verbose=False,
            session=None,
            tui=False,
            alternate_screen=False,
            mode=mode,
            attach=attach,
            rust_altscreen=False,
            legacy=False,
        )


def _get_provider(
    config: AutoCodeConfig,
) -> OllamaProvider | OpenRouterProvider:
    """Create LLM provider from config."""
    from autocode.layer4.llm import create_provider

    return create_provider(config)


async def _stream_response(
    provider: OllamaProvider | OpenRouterProvider,
    messages: list[dict[str, str]],
) -> str:
    """Stream LLM response to console, return full text."""
    full_response = ""
    waiting = True

    with Live(Spinner("dots", text="Thinking..."), console=console, refresh_per_second=15) as live:
        async for chunk in provider.generate(messages, stream=True):
            if waiting:
                waiting = False
                live.update(Text(chunk))
            full_response += chunk
            live.update(Text(full_response))

    return full_response


async def _chat_loop(config: AutoCodeConfig) -> None:
    """Interactive chat REPL."""
    from autocode.app.commands import CommandRouter, create_default_router
    from autocode.layer4.llm import ConversationHistory
    from autocode.session.store import SessionStore

    class _LegacyReplCommandContext:
        """Small AppContext implementation for the Rich fallback REPL."""

        def __init__(self, router: CommandRouter) -> None:
            self.session_store = SessionStore(config.tui.session_db_path)
            self.session_id = self.session_store.create_session(
                title="Legacy REPL",
                model=config.llm.model,
                provider=config.llm.provider,
                project_dir=str(Path.cwd()),
            )
            self.config = config
            self.project_root = Path.cwd()
            self.command_router = router
            self._messages: list[str] = []
            self._approval_mode = config.tui.approval_mode
            self._shell_enabled = config.shell.enabled
            self._show_thinking = True
            self._exit_requested = False

        def add_system_message(self, content: str) -> None:
            self._messages.append(content)
            console.print(content)

        def clear_messages(self) -> None:
            self._messages.clear()
            console.print("[dim]Messages cleared.[/]")

        def display_messages(self, messages: list[Any]) -> None:
            for message in messages:
                content = getattr(message, "content", str(message))
                console.print(content)

        def get_assistant_messages(self) -> list[str]:
            return list(self._messages)

        def copy_to_clipboard(self, text: str) -> bool:
            from autocode.app.commands import _copy_to_clipboard

            return _copy_to_clipboard(text)

        def exit_app(self) -> None:
            self._exit_requested = True

        def set_agent_mode(self, mode: Any) -> None:
            self.add_system_message(f"Mode set to {getattr(mode, 'value', mode)}")

        async def run_loop_prompt(self, payload: str) -> None:
            self.add_system_message(
                f"Loop prompt execution is not available in legacy REPL: {payload}"
            )

        async def run_loop_command(self, payload: str) -> None:
            result = self.command_router.dispatch(payload)
            if result is None:
                self.add_system_message(f"Unknown command: {payload}")
                return
            cmd, args = result
            await cmd.handler(self, args)

        @property
        def approval_mode(self) -> str:
            return self._approval_mode

        @approval_mode.setter
        def approval_mode(self, value: str) -> None:
            self._approval_mode = value
            self.config.tui.approval_mode = value  # type: ignore[assignment]

        @property
        def shell_enabled(self) -> bool:
            return self._shell_enabled

        @shell_enabled.setter
        def shell_enabled(self, value: bool) -> None:
            self._shell_enabled = value
            self.config.shell.enabled = value

        @property
        def show_thinking(self) -> bool:
            return self._show_thinking

        @show_thinking.setter
        def show_thinking(self, value: bool) -> None:
            self._show_thinking = value

    provider = _get_provider(config)
    history = ConversationHistory(
        system_prompt="You are AutoCode, an AI coding assistant. Be concise and helpful."
    )
    command_router = create_default_router()
    command_context = _LegacyReplCommandContext(command_router)

    console.print(
        f"[bold]AutoCode[/] v{_get_version()} ({config.llm.provider}:{config.llm.model})",
    )
    console.print("[dim]Type 'exit' or Ctrl+C to quit.[/]\n")

    while True:
        try:
            user_input = console.input("[bold green]> [/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        if user_input.strip().lower() in ("exit", "quit", "/exit", "/quit"):
            console.print("[dim]Goodbye.[/]")
            break

        if not user_input.strip():
            continue

        command = command_router.dispatch(user_input)
        if command is not None:
            cmd, args = command
            try:
                await cmd.handler(command_context, args)
            except Exception as e:
                console.print(f"\n[bold red]Command error:[/] {e}")
            if command_context._exit_requested:
                break
            continue

        history.add_user(user_input)
        try:
            response_text = await _stream_response(provider, history.get_messages())
            history.add_assistant(response_text)
            console.print()  # newline after streamed output
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")


async def _ask_once(question: str, config: AutoCodeConfig, file: str | None) -> None:
    """Ask a single question and print the response."""
    provider = _get_provider(config)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": "You are AutoCode, an AI coding assistant. Be concise."},
    ]

    if file:
        from autocode.utils.file_tools import read_file

        try:
            content = read_file(file)
            messages.append(
                {
                    "role": "user",
                    "content": f"File: {file}\n```\n{content}\n```\n\n{question}",
                }
            )
        except (FileNotFoundError, ValueError) as e:
            console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(1) from e
    else:
        messages.append({"role": "user", "content": question})

    try:
        await _stream_response(provider, messages)
        console.print()  # newline after streamed output
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise typer.Exit(1) from e


def _get_version() -> str:
    from autocode import __version__

    return __version__


def _find_tui_binary() -> str | None:
    """Discover the Rust TUI binary.

    Discovery order:
      1. $AUTOCODE_TUI_BIN environment variable
      2. autocode/rtui/target/release/autocode-tui relative to the repo
      3. autocode-tui on PATH
    """
    import os
    import shutil
    import sys
    from pathlib import Path

    env_bin = os.environ.get("AUTOCODE_TUI_BIN")
    if env_bin and Path(env_bin).is_file():
        return env_bin

    ext = ".exe" if sys.platform == "win32" else ""
    # autocode/src/autocode/cli.py → autocode/rtui/target/release/autocode-tui
    rtui_path = (
        Path(__file__).resolve().parent.parent.parent
        / "rtui"
        / "target"
        / "release"
        / f"autocode-tui{ext}"
    )
    if rtui_path.is_file():
        return str(rtui_path)

    found = shutil.which(f"autocode-tui{ext}")
    if found:
        return found

    return None


# --- Commands ---


@app.command()
def chat(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    session: str | None = typer.Option(None, "--session", "-s", help="Resume a session by ID"),
    tui: bool = typer.Option(False, "--tui", help="Use fullscreen Textual TUI (fallback)"),
    alternate_screen: bool = typer.Option(False, "--alternate-screen", help="Alias for --tui"),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Rust TUI launch mode: inline or altscreen. Overrides the saved default.",
    ),
    attach: str | None = typer.Option(
        None,
        "--attach",
        help="Attach the Rust TUI to an already-running backend at HOST:PORT.",
    ),
    rust_altscreen: bool = typer.Option(
        False,
        "--rust-altscreen",
        help="Run the Rust TUI in alternate-screen mode instead of inline mode",
    ),
    legacy: bool = typer.Option(False, "--legacy", help="Use legacy Rich REPL (no agent loop)"),
) -> None:
    """Start an interactive chat session.

    Default: launches the Rust TUI binary (autocode/rtui/target/release/autocode-tui).
    Use --tui for the Textual fullscreen fallback, or --legacy for the Rich REPL.
    """
    import os
    import subprocess

    config = load_config()
    if verbose:
        config.ui.verbose = True

    from autocode.core.logging import setup_logging

    setup_logging(config.logging, verbose=verbose)

    if legacy:
        asyncio.run(_chat_loop(config))
        return

    if tui or alternate_screen:
        from autocode.tui.app import AutoCodeApp

        tui_app = AutoCodeApp(config=config, session_id=session or None)
        tui_app.run(inline=False)
        return

    # Default: Rust TUI
    rust_bin = _find_tui_binary()
    if rust_bin is None:
        console.print(
            "[red]Rust TUI binary not found.[/red]\n\n"
            "Build it with:\n"
            "    [bold]cd autocode/rtui && cargo build --release[/bold]\n\n"
            "Or set [bold]AUTOCODE_TUI_BIN[/bold] to an existing binary path.\n"
            "Fallbacks: [bold]autocode chat --tui[/bold] (Textual) or "
            "[bold]autocode chat --legacy[/bold] (Rich REPL)."
        )
        raise typer.Exit(1)

    env = os.environ.copy()
    if session:
        env["AUTOCODE_SESSION_ID"] = session

    argv = [rust_bin]
    resolved_mode = mode.strip().lower() if mode is not None else None
    if resolved_mode not in {None, "inline", "altscreen"}:
        console.print("[red]Invalid --mode.[/] Choose `inline` or `altscreen`.")
        raise typer.Exit(2)

    use_altscreen = config.tui.alternate_screen
    if rust_altscreen:
        use_altscreen = True
    if resolved_mode is not None:
        use_altscreen = resolved_mode == "altscreen"

    if use_altscreen:
        argv.append("--altscreen")
    if attach:
        argv.extend(["--attach", attach])

    result = subprocess.run(argv, env=env)
    raise typer.Exit(result.returncode)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask"),
    file: str | None = typer.Option(None, "--file", "-f", help="File for context"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Ask a single question and get a response."""
    config = load_config()
    if verbose:
        config.ui.verbose = True

    from autocode.core.logging import setup_logging

    setup_logging(config.logging, verbose=verbose)
    asyncio.run(_ask_once(question, config, file))


@app.command()
def edit(
    file: str = typer.Argument(..., help="File to edit"),
    instruction: str = typer.Argument(..., help="Edit instruction"),
) -> None:
    """Edit a file using AI (not yet implemented)."""
    console.print(f"[dim]Edit not yet implemented. File: {file}, Instruction: {instruction}[/]")


@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show | set | check | path"),
    key_value: str | None = typer.Argument(None, help="key=value pair (for 'set' action)"),
) -> None:
    """Show or manage configuration."""
    cfg = load_config()

    if action == "show":
        import yaml
        from rich.syntax import Syntax

        yaml_str = yaml.dump(cfg.model_dump(), default_flow_style=False, sort_keys=False)
        console.print(Syntax(yaml_str, "yaml", theme="monokai"))
    elif action == "set":
        if not key_value or "=" not in key_value:
            console.print("[red]Usage: autocode config set section.key=value[/]")
            raise typer.Exit(1)
        key, _, value = key_value.partition("=")
        parts = key.strip().split(".")
        if len(parts) != 2:  # noqa: PLR2004
            console.print("[red]Key must be section.field (e.g. llm.model)[/]")
            raise typer.Exit(1)
        section, field = parts
        data = cfg.model_dump()
        if section not in data:
            console.print(f"[red]Unknown section: {section}[/]")
            raise typer.Exit(1)
        if field not in data[section]:
            console.print(f"[red]Unknown field: {section}.{field}[/]")
            raise typer.Exit(1)
        data[section][field] = value.strip()
        from autocode.config import save_config as _save

        updated = AutoCodeConfig.model_validate(data)
        path = _save(updated)
        console.print(f"[green]Set {key.strip()} = {value.strip()}[/] (saved to {path})")
    elif action == "check":
        warnings = check_config(cfg)
        if warnings:
            for w in warnings:
                console.print(f"[yellow]Warning:[/] {w}")
        else:
            console.print("[green]Config OK[/]")
    elif action == "path":
        console.print(str(get_config_path()))
    else:
        console.print(f"[red]Unknown action: {action}[/]. Use: show, set, check, path")


@app.command()
def serve(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        help="Backend host transport: stdio or tcp.",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Bind host for TCP backend transport.",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        help="Bind port for TCP backend transport.",
    ),
) -> None:
    """Start the JSON-RPC backend server for the Rust TUI or other clients."""
    from autocode.backend.server import main as server_main
    from autocode.core.logging import setup_logging

    resolved_transport = transport.strip().lower()
    if resolved_transport not in {"stdio", "tcp"}:
        console.print("[red]Invalid --transport.[/] Choose `stdio` or `tcp`.")
        raise typer.Exit(2)
    from autocode.backend.tcp_host import is_loopback_bind_host

    if resolved_transport == "tcp" and not is_loopback_bind_host(host):
        console.print(
            "[red]Refusing non-loopback TCP bind host by default.[/] "
            "Use 127.0.0.1 or localhost for attach-mode backends."
        )
        raise typer.Exit(2)

    config = load_config()
    setup_logging(config.logging, verbose=verbose)
    asyncio.run(server_main(transport=resolved_transport, bind_host=host, port=port))


@app.command()
def daemon(
    watch: Path = typer.Option(..., "--watch", help="Repository path to watch."),
    attach: str = typer.Option(
        "127.0.0.1:8765",
        "--attach",
        help="Attached backend TCP address as HOST:PORT.",
    ),
    session: str | None = typer.Option(
        None,
        "--session",
        help="Optional backend session id to target.",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Send one tick and exit. Used for canary/smoke validation.",
    ),
    interval: float = typer.Option(
        30.0,
        "--interval",
        help="Seconds between daemon ticks.",
    ),
    max_ticks: int = typer.Option(
        0,
        "--max-ticks",
        help="Maximum ticks before exit; 0 means run until interrupted.",
    ),
    read_only: bool = typer.Option(
        True,
        "--read-only/--allow-mutations",
        help=(
            "Run proactive ticks through the backend read-only guard "
            "unless --allow-mutations is set."
        ),
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Log ticks without executing proactive work.",
    ),
) -> None:
    """Start the KAIROS daemon loop when the feature flag is enabled."""
    from autocode.agent.proactive import (
        KairosAuditLog,
        build_tick_message,
        kairos_enabled_from_env,
        new_tick_id,
        send_tick_rpc,
        should_skip_for_cost_cap,
    )

    if not kairos_enabled_from_env():
        console.print(
            "KAIROS is disabled. Set AUTOCODE_FEATURE_KAIROS=true and restart to opt in.",
            highlight=False,
        )
        return
    if not watch.exists():
        console.print(f"[red]Watch path does not exist:[/] {watch}")
        raise typer.Exit(1)

    config = load_config()
    audit = KairosAuditLog()
    tick_id = new_tick_id()
    if should_skip_for_cost_cap(
        cost_limit_usd=config.agent.cost_limit_usd,
        current_cost_usd=0.0,
    ):
        audit.record_action(
            session_id=session or "",
            action="kairos_cost_cap_skip",
            metadata={"tick_id": tick_id, "cost_limit_usd": config.agent.cost_limit_usd},
        )
        console.print("KAIROS tick skipped: cost cap reached.", highlight=False)
        return

    log_path = Path.home() / ".autocode" / "daemon.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"KAIROS daemon started for {watch.resolve()} (dry_run={dry_run})\n",
        encoding="utf-8",
    )
    console.print(f"KAIROS daemon initialized for {watch.resolve()}", highlight=False)
    if dry_run:
        console.print("Dry run: no proactive tool execution will run.", highlight=False)
    host, _, port_text = attach.partition(":")
    if not host or not port_text:
        console.print("[red]Invalid --attach.[/] Use HOST:PORT.")
        raise typer.Exit(2)

    def _send_one_tick() -> None:
        current_tick_id = new_tick_id()
        result = asyncio.run(
            send_tick_rpc(
                host=host,
                port=int(port_text),
                session_id=session,
                tick_id=current_tick_id,
                message=build_tick_message(),
                read_only=read_only,
            )
        )
        audit.record_action(
            session_id=session or "",
            action="kairos_tick_sent",
            metadata={"tick_id": current_tick_id, "attach": attach, "read_only": read_only},
        )
        console.print(f"KAIROS tick sent: {current_tick_id} result={result}", highlight=False)

    if once:
        if dry_run:
            audit.record_action(
                session_id=session or "",
                action="kairos_tick_dry_run",
                metadata={"tick_id": tick_id, "attach": attach, "read_only": read_only},
            )
            console.print(f"KAIROS dry-run tick prepared: {tick_id}", highlight=False)
            return
        _send_one_tick()
        return

    if dry_run:
        return

    import time

    sent = 0
    while max_ticks <= 0 or sent < max_ticks:
        _send_one_tick()
        sent += 1
        if max_ticks > 0 and sent >= max_ticks:
            break
        time.sleep(max(0.0, interval))


@app.command("mcp-serve")
def mcp_serve(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        help="MCP transport: stdio.",
    ),
    project_root: str = typer.Option(
        ".",
        "--project-root",
        help="Project root exposed to read-only MCP tools.",
    ),
    audit_log_path: str | None = typer.Option(
        None,
        "--audit-log-path",
        help="JSONL audit log path for MCPToolCall records.",
    ),
) -> None:
    """Start the read-only MCP server for external agent clients."""
    from pathlib import Path

    from autocode.core.logging import setup_logging
    from autocode.doctor import default_mcp_audit_log_path
    from autocode.external.mcp_server import MCPServer, MCPServerConfig

    resolved_transport = transport.strip().lower()
    if resolved_transport != "stdio":
        console.print("[red]Invalid --transport.[/] Choose `stdio`.")
        raise typer.Exit(2)

    config = load_config()
    setup_logging(config.logging, verbose=verbose)

    server_config = MCPServerConfig(
        enabled=True,
        project_root=Path(project_root).resolve(),
        transport=resolved_transport,
        audit_log_path=(
            Path(audit_log_path).expanduser()
            if audit_log_path is not None
            else default_mcp_audit_log_path()
        ),
    )
    MCPServer(server_config).run()


@kairos_app.command("audit")
def kairos_audit(
    log_path: Path | None = typer.Option(
        None,
        "--log-path",
        help="KAIROS audit JSONL path.",
    ),
) -> None:
    """Print KAIROS blast-radius audit records."""
    import json

    from autocode.agent.proactive import KairosAuditLog

    records = KairosAuditLog(log_path).read_records()
    if not records:
        console.print("No KAIROS audit records.", highlight=False)
        return
    for record in records:
        console.print(json.dumps(record, sort_keys=True), highlight=False)


@telemetry_app.command("summary")
def telemetry_summary(
    last: str = typer.Option("7d", "--last", help="Window: 7d, 30d, all, or YYYY-MM-DD."),
) -> None:
    """Show local telemetry event counts."""
    from autocode.telemetry.aggregator import TelemetryAggregator, since_from_window

    summary = TelemetryAggregator().summary(since=since_from_window(last))
    console.print(f"Total events: {summary.total_events}")
    if summary.by_kind:
        console.print("By kind:")
        for kind, count in sorted(summary.by_kind.items()):
            console.print(f"  {kind}: {count}")
    if summary.by_session:
        console.print("By session:")
        for session_id, count in sorted(summary.by_session.items()):
            console.print(f"  {session_id}: {count}")
    if summary.alerts:
        console.print("Alerts:")
        for alert in summary.alerts:
            console.print(f"  {alert}")


@telemetry_app.command("events")
def telemetry_events(
    kind: str | None = typer.Option(None, "--kind", help="Filter by telemetry event kind."),
    session_id: str | None = typer.Option(None, "--session", help="Filter by session ID."),
    last: str = typer.Option("7d", "--last", help="Window: 7d, 30d, all, or YYYY-MM-DD."),
) -> None:
    """Print local telemetry events as JSONL."""
    import json

    from autocode.telemetry.aggregator import TelemetryAggregator, since_from_window

    for event in TelemetryAggregator().events(
        kind=kind,
        session_id=session_id,
        since=since_from_window(last),
    ):
        console.print(json.dumps(event, separators=(",", ":")), highlight=False)


@telemetry_app.command("session")
def telemetry_session(
    session_id: str = typer.Argument(..., help="Session ID to inspect."),
) -> None:
    """Print telemetry events for one session as JSONL."""
    import json

    from autocode.telemetry.aggregator import TelemetryAggregator

    for event in TelemetryAggregator().events(session_id=session_id):
        console.print(json.dumps(event, separators=(",", ":")), highlight=False)


@telemetry_app.command("drift")
def telemetry_drift(
    last: str = typer.Option("7d", "--last", help="Window: 7d, 30d, all, or YYYY-MM-DD."),
) -> None:
    """Show local drift detector telemetry counts."""
    from autocode.telemetry.aggregator import TelemetryAggregator, since_from_window

    summary = TelemetryAggregator().drift_summary(since=since_from_window(last))
    if not summary:
        console.print("No drift events.")
        return
    for (tool_name, drift_kind, severity), count in sorted(summary.items()):
        console.print(f"{tool_name} {drift_kind} {severity}: {count}")


@telemetry_app.command("export")
def telemetry_export(
    since: str | None = typer.Option(None, "--since", help="Start date: YYYY-MM-DD."),
    format: str = typer.Option("jsonl", "--format", help="Export format: jsonl or csv."),
) -> None:
    """Export local telemetry data."""
    from autocode.telemetry.aggregator import TelemetryAggregator, since_from_window

    aggregator = TelemetryAggregator()
    since_date = since_from_window(since)
    resolved_format = format.strip().lower()
    if resolved_format == "jsonl":
        console.print(aggregator.export_jsonl(since=since_date), highlight=False)
    elif resolved_format == "csv":
        console.print(aggregator.export_csv(since=since_date), highlight=False, end="")
    else:
        console.print("[red]Invalid --format.[/] Choose `jsonl` or `csv`.")
        raise typer.Exit(2)


@telemetry_app.command("public-report")
def telemetry_public_report(
    output: Path = typer.Option(..., "--output", help="Output JSON file path."),
    last: str = typer.Option("30d", "--last", help="Window: 7d, 30d, all, or YYYY-MM-DD."),
) -> None:
    """Write a public-safe telemetry summary without session ids or payloads."""
    import json

    from autocode.telemetry.aggregator import TelemetryAggregator, since_from_window

    report = TelemetryAggregator().public_report(since=since_from_window(last))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    console.print(f"Public telemetry report written to {output}", highlight=False, soft_wrap=True)


@telemetry_app.command("purge")
def telemetry_purge() -> None:
    """Delete the local telemetry store."""
    from autocode.telemetry.store import purge_telemetry

    purge_telemetry()
    console.print("Telemetry store purged.")


@app.command()
def version() -> None:
    """Show AutoCode version."""
    console.print(f"autocode {_get_version()}", highlight=False)


@app.command()
def doctor() -> None:
    """Run system readiness checks."""
    from autocode.doctor import format_report, run_doctor

    results = run_doctor()
    console.print(format_report(results))
    passed = sum(1 for r in results if r.passed)
    raise typer.Exit(code=0 if passed == len(results) else 1)


@app.command()
def setup() -> None:
    """Run first-time setup and bootstrap checks."""
    from autocode.packaging.bootstrap import run_bootstrap

    result = run_bootstrap()
    console.print(result.summary())
    raise typer.Exit(code=0 if result.ready else 1)


@app.command()
def team(
    action: str = typer.Argument("list", help="Action: list, show, create"),
    name: str = typer.Argument("", help="Team name"),
) -> None:
    """Manage agent teams."""
    from autocode.agent.team import AgentTeam, TeamStore

    store = TeamStore()

    if action == "list":
        teams = store.list_teams()
        if not teams:
            console.print("No teams defined. Use 'autocode team create bugfix' to create one.")
        else:
            for t in teams:
                console.print(f"  {t}")
    elif action == "show" and name:
        t = store.load(name)
        if t:
            console.print(f"Team: {t.name}")
            console.print(f"Description: {t.description}")
            console.print(f"Agents: {len(t.agents)}")
            for a in t.agents:
                console.print(f"  - {a.id} ({a.role.value}, {a.model.provider})")
        else:
            console.print(f"Team '{name}' not found.")
    elif action == "create" and name:
        if name == "bugfix":
            t = AgentTeam.bugfix_team()
        else:
            t = AgentTeam(name=name, description=f"Custom team: {name}")
        store.save(t)
        console.print(f"Team '{name}' created.")
    else:
        console.print("Usage: autocode team [list|show|create] [name]")


@app.command()
def rename(
    old_name: str = typer.Argument(..., help="Symbol to rename"),
    new_name: str = typer.Argument(..., help="New name"),
    apply: bool = typer.Option(False, "--apply", help="Apply the rename (default: preview only)"),
) -> None:
    """Rename a symbol across the project."""
    from pathlib import Path

    from autocode.agent.refactor import apply_rename, format_rename_preview, preview_rename

    project_root = Path.cwd()

    if apply:
        result = apply_rename(old_name, new_name, project_root)
        if result.success:
            console.print(f"Renamed {old_name} → {new_name} in {len(result.files_modified)} files")
            for f in result.files_modified:
                console.print(f"  {f}")
        else:
            console.print(f"Error: {result.error}")
            raise typer.Exit(code=1)
    else:
        result = preview_rename(old_name, new_name, project_root)
        console.print(format_rename_preview(result))
        if result.occurrences:
            console.print("\nRun with --apply to execute the rename.")


@app.command("exec")
def exec_cmd(
    prompt: str = typer.Argument(..., help="Prompt to send to the agent"),
    json_output: bool = typer.Option(
        False, "--json", help="Output Tier 4.4 NDJSON event stream to stdout."
    ),
    output_schema: str | None = typer.Option(
        None,
        "--output-schema",
        help="Path to a JSON Schema file; the response is validated against it.",
    ),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve",
        help="Auto-approve tool requests in headless --json mode.",
    ),
    permission_mode: str | None = typer.Option(
        None,
        "--permission-mode",
        help=(
            "Session permission mode: acceptEdits | bypassPermissions | default | "
            "dontAsk | plan | auto. Ported clean-room from puku-cli; generalizes "
            "--auto-approve (explicit mode wins). 'plan' runs read-only."
        ),
    ),
    max_budget_usd: float | None = typer.Option(
        None,
        "--max-budget-usd",
        help=(
            "Maximum USD to spend on this run (per-invocation cost cap). Ported "
            "clean-room from puku-cli; overrides agent.cost_limit_usd."
        ),
    ),
    system_prompt: str | None = typer.Option(
        None,
        "--system-prompt",
        help=(
            "Replace the default system prompt for this run (dynamic runtime state "
            "is preserved). Ported clean-room from puku-cli."
        ),
    ),
    append_system_prompt: str | None = typer.Option(
        None,
        "--append-system-prompt",
        help="Append text to the default system prompt. Ported clean-room from puku-cli.",
    ),
    add_dir: list[str] = typer.Option(
        [],
        "--add-dir",
        help=(
            "Additional directory tools may access beyond the project root "
            "(repeatable). Ported clean-room from puku-cli."
        ),
    ),
    output_format: str | None = typer.Option(
        None,
        "--output-format",
        help=(
            "Headless output format: text | json | stream-json. Ported clean-room "
            "from puku-cli. 'stream-json' == --json (NDJSON event stream); 'json' is "
            "a single consolidated result object; 'text' is the final message only."
        ),
    ),
    cd: str | None = typer.Option(
        None,
        "--cd",
        "-C",
        help="Run the agent in this directory instead of the cwd. Ported clean-room from codex.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Execute a single agent turn in headless mode."""
    from autocode.core.logging import setup_logging

    config = load_config()
    if verbose:
        config.ui.verbose = True

    # Validate the permission mode early (applies to any output path).
    if permission_mode is not None:
        from autocode.agent.permission_mode import resolve_permission_mode

        try:
            resolve_permission_mode(permission_mode)
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(2) from exc

    if output_format is not None and output_format not in {"text", "json", "stream-json"}:
        console.print(
            "[red]Invalid --output-format.[/] Choose text, json, or stream-json."
        )
        raise typer.Exit(2)

    project_root: Path | None = None
    if cd is not None:
        project_root = Path(cd).expanduser()
        if not project_root.is_dir():
            console.print(f"[red]--cd directory does not exist:[/] {cd}")
            raise typer.Exit(2)

    if json_output or output_format == "stream-json":
        import logging as _logging

        _logging.basicConfig(stream=sys.stderr, level=_logging.WARNING)
        setup_logging(config.logging, verbose=False)

        from autocode.backend.headless_runner import HeadlessRunner

        try:
            runner = HeadlessRunner(
                config=config,
                auto_approve=auto_approve,
                permission_mode=permission_mode,
                max_budget_usd=max_budget_usd,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                add_dirs=tuple(add_dir),
                project_root=project_root,
            )
            asyncio.run(runner.run(prompt))
        except Exception as exc:
            from autocode.backend.headless_schema import ErrorEvent, emit_event

            emit_event(ErrorEvent(message=str(exc)))
            raise typer.Exit(1) from exc
    elif output_format in {"json", "text"}:
        import io
        import json as _json
        import logging as _logging

        _logging.basicConfig(stream=sys.stderr, level=_logging.WARNING)
        setup_logging(config.logging, verbose=False)

        from autocode.backend.headless_runner import HeadlessRunner
        from autocode.backend.headless_schema import collapse_ndjson_to_result

        buf = io.StringIO()
        try:
            runner = HeadlessRunner(
                config=config,
                output=buf,
                auto_approve=auto_approve,
                permission_mode=permission_mode,
                max_budget_usd=max_budget_usd,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                add_dirs=tuple(add_dir),
                project_root=project_root,
            )
            asyncio.run(runner.run(prompt))
        except Exception as exc:
            err = {"type": "result", "is_error": True, "result": str(exc)}
            print(_json.dumps(err, indent=2) if output_format == "json" else str(exc))
            raise typer.Exit(1) from exc

        result = collapse_ndjson_to_result(buf.getvalue().splitlines())
        if output_format == "text":
            print(result.get("result", ""))
        else:
            print(_json.dumps(result, indent=2))
        if result.get("is_error"):
            raise typer.Exit(1)
    elif output_schema:
        from autocode.layer4.llm import create_provider

        setup_logging(config.logging, verbose=verbose)

        schema_path = Path(output_schema)
        schema_text = schema_path.read_text()
        import json

        schema_dict = json.loads(schema_text)

        provider = create_provider(config)
        messages = [
            {"role": "system", "content": "You are AutoCode, an AI coding assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = asyncio.run(
                provider.generate_json(messages, schema=schema_dict)
            )
            print(json.dumps(result, indent=2))
        except Exception as exc:
            print(f'{{"error": "{exc}"}}', file=sys.stderr)
            raise typer.Exit(1) from exc
    else:
        console.print("Use --json for NDJSON output or --output-schema for typed JSON.")
        raise typer.Exit(1)


@app.command("generate-schema")
def generate_schema(
    out: str = typer.Option(
        "./schemas",
        "--out",
        help="Output directory for JSON Schema files.",
    ),
) -> None:
    """Emit JSON Schema files for the headless NDJSON event protocol."""
    from autocode.backend.headless_schema import write_schema_files

    written = write_schema_files(out)
    for path in written:
        console.print(f"  {path}")
    console.print(f"Generated {len(written)} schema files in {out}")
