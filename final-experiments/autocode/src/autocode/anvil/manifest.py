"""Introspect AutoCode's own CLI surface into the copycat capability model.

The manifest is the *baseline* a target census is diffed against (PLAN_05 §2.3,
step 2). It reuses the same :class:`Capability` / :class:`Census` types so the
gap-diff is an apples-to-apples set operation. Introspection is read-only: it
walks the Typer/Click command tree, it does not execute any command.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
import typer

from autocode.anvil.census import Capability, Census

if TYPE_CHECKING:
    pass


def _flag_capability(opt: click.Option, command_path: str) -> Capability | None:
    tokens = [o for o in opt.opts if o.startswith("-")]
    if not tokens:
        return None
    longs = [t for t in tokens if t.startswith("--")]
    canonical = max(longs, key=len) if longs else tokens[0]
    metadata: dict[str, object] = {
        "takes_value": not opt.is_flag,
        "commands": [command_path] if command_path else [],
    }
    if isinstance(opt.type, click.Choice):
        metadata["choices"] = list(opt.type.choices)
    return Capability(
        id="flag:" + canonical.lstrip("-"),
        kind="flag",
        surface=tuple(tokens),
        description=(opt.help or "").strip(),
        metadata=metadata,
    )


def _walk(
    cmd: click.Command,
    path: str,
    caps: dict[str, Capability],
) -> None:
    # Record this command's own options as flags.
    for param in cmd.params:
        if isinstance(param, click.Option):
            cap = _flag_capability(param, path)
            if cap is None:
                continue
            existing = caps.get(cap.id)
            if existing is None:
                caps[cap.id] = cap
            else:
                # Merge the list of commands that expose this flag.
                merged = list(dict.fromkeys(
                    [*existing.metadata.get("commands", []), *cap.metadata.get("commands", [])]
                ))
                existing.metadata["commands"] = merged

    if isinstance(cmd, click.Group):
        for name, sub in cmd.commands.items():
            cmd_id = "cmd:" + name
            if cmd_id not in caps:
                caps[cmd_id] = Capability(
                    id=cmd_id,
                    kind="subcommand",
                    surface=(name,),
                    description=(sub.help or "").strip(),
                    metadata={"parent": path} if path else {},
                )
            child_path = f"{path} {name}".strip()
            _walk(sub, child_path, caps)


def manifest_from_typer(app: typer.Typer, *, name: str = "autocode") -> Census:
    """Introspect a Typer app into a :class:`Census` of AutoCode capabilities."""
    command = typer.main.get_command(app)
    caps: dict[str, Capability] = {}
    _walk(command, "", caps)
    return Census(
        target=name,
        source="autocode CLI introspection",
        capabilities=tuple(caps.values()),
    )


def autocode_manifest() -> Census:
    """The live AutoCode capability manifest from its real Typer app."""
    from autocode.cli import app

    return manifest_from_typer(app, name="autocode")
