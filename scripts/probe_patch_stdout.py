"""Manual probe for prompt_toolkit.patch_stdout(raw=True) + Rich ANSI output.

Goal: validate whether `patch_stdout(raw=True)` keeps Rich ANSI intact while the
prompt remains editable (Claude Code / Aider style UX building block).

Run:
  uv run python scripts/probe_patch_stdout.py

Expected (PASS):
  - While you're typing at the prompt, colored Rich output appears ABOVE it.
  - No visible ANSI garbage like '?[0m' or mangled escape sequences.

If it FAILS on Windows Terminal/PowerShell/cmd:
  - Do not attempt an always-on prompt + streaming output design in inline mode.
  - Prefer `hybridcoder chat --tui` for true concurrent input.
"""

from __future__ import annotations

import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console


async def _spam_output(console: Console, stop: asyncio.Event) -> None:
    i = 0
    while not stop.is_set():
        console.print(f"[bold green]Output line {i}[/bold green] - [dim]ANSI probe[/dim]")
        i += 1
        await asyncio.sleep(0.5)


async def main() -> None:
    stop = asyncio.Event()
    session: PromptSession[str] = PromptSession()

    with patch_stdout(raw=True):
        # Important: create Console inside patch_stdout so it targets the proxy stdout.
        console = Console()

        console.print("[dim]Probe running. Type while output is printing. Type 'exit' to stop.[/dim]")
        spam_task = asyncio.create_task(_spam_output(console, stop))

        try:
            while True:
                try:
                    text = await session.prompt_async("type here> ")
                except EOFError:
                    break

                if text.strip().lower() in ("exit", "quit"):
                    break

                console.print(f"[cyan]You typed:[/cyan] {text}")
        finally:
            stop.set()
            spam_task.cancel()
            try:
                await spam_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())

