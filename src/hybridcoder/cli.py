"""CLI entry point for HybridCoder.

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

from hybridcoder.config import (
    HybridCoderConfig,
    check_config,
    get_config_path,
    load_config,
)

if TYPE_CHECKING:
    from hybridcoder.layer4.llm import OllamaProvider, OpenRouterProvider

app = typer.Typer(
    name="hybridcoder",
    help="Edge-native AI coding assistant.",
    no_args_is_help=True,
)
console = Console()


def _get_provider(
    config: HybridCoderConfig,
) -> OllamaProvider | OpenRouterProvider:
    """Create LLM provider from config."""
    from hybridcoder.layer4.llm import create_provider

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


async def _chat_loop(config: HybridCoderConfig) -> None:
    """Interactive chat REPL."""
    from hybridcoder.layer4.llm import ConversationHistory

    provider = _get_provider(config)
    history = ConversationHistory(
        system_prompt="You are HybridCoder, an AI coding assistant. Be concise and helpful."
    )

    console.print(
        f"[bold]HybridCoder[/] v{_get_version()} ({config.llm.provider}:{config.llm.model})",
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


async def _ask_once(question: str, config: HybridCoderConfig, file: str | None) -> None:
    """Ask a single question and print the response."""
    provider = _get_provider(config)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": "You are HybridCoder, an AI coding assistant. Be concise."},
    ]

    if file:
        from hybridcoder.utils.file_tools import read_file

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
    from hybridcoder import __version__

    return __version__


# --- Commands ---


@app.command()
def chat(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    session: str | None = typer.Option(None, "--session", "-s", help="Resume a session by ID"),
    alternate_screen: bool = typer.Option(False, "--alternate-screen", help="Use alternate screen"),
    legacy: bool = typer.Option(False, "--legacy", help="Use legacy Rich REPL instead of TUI"),
) -> None:
    """Start an interactive chat session."""
    config = load_config()
    if verbose:
        config.ui.verbose = True

    if legacy:
        asyncio.run(_chat_loop(config))
        return

    from hybridcoder.tui.app import HybridCoderApp

    use_inline = not (alternate_screen or config.tui.alternate_screen)
    tui_app = HybridCoderApp(config=config, session_id=session or None)
    tui_app.run(inline=use_inline)


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
            console.print("[red]Usage: hybridcoder config set section.key=value[/]")
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
        from hybridcoder.config import save_config as _save

        updated = HybridCoderConfig.model_validate(data)
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
def version() -> None:
    """Show HybridCoder version."""
    console.print(f"hybridcoder {_get_version()}")
