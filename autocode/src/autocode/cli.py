"""CLI entry point for AutoCode.

Typer app with commands: chat, ask, edit, config, version.
"""

from __future__ import annotations

import asyncio
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
    from autocode.layer4.llm import ConversationHistory

    provider = _get_provider(config)
    history = ConversationHistory(
        system_prompt="You are AutoCode, an AI coding assistant. Be concise and helpful."
    )

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

    result = subprocess.run([rust_bin], env=env)
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
) -> None:
    """Start JSON-RPC backend server for the Go TUI frontend."""
    from autocode.backend.server import main as server_main
    from autocode.core.logging import setup_logging

    config = load_config()
    setup_logging(config.logging, verbose=verbose)
    asyncio.run(server_main())


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
