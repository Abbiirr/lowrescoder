"""Concrete copycat census collectors.

Channel A reads a target's *observable* surface via ``--help``; a bundled
snapshot keeps the census reproducible when the binary is absent. Nothing here
vendors target source — only the public command surface is read.

Targets:
  - ``puku-cli`` (``@puku/puku-cli``) — Claude-Code-compatible headless agent CLI,
    also the harness-tester's known-good control.
  - ``codex`` (OpenAI Codex CLI) — a second structural target demonstrating the
    census/gap-diff system generalizes beyond a single agent.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from autocode.anvil.census import Census, parse_help_text

PUKU_TARGET_ID = "puku-cli"
PUKU_BINARY = "puku-cli"
CODEX_TARGET_ID = "codex"
CODEX_BINARY = "codex"

_DATA = Path(__file__).resolve().parent / "data"
_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")

Runner = Callable[[list[str]], str | None]


def _make_runner(binary: str) -> Runner:
    """A runner that invokes ``<binary> <args>`` and returns stdout, or None."""

    def run(args: list[str]) -> str | None:
        exe = shutil.which(binary)
        if not exe:
            return None
        try:
            proc = subprocess.run(  # noqa: S603 - fixed binary, fixed args
                [exe, *args],
                capture_output=True,
                text=True,
                timeout=20,
                stdin=subprocess.DEVNULL,
            )
        except Exception:
            return None
        out = (proc.stdout or "").strip()
        return out or None

    return run


def _clean_version(raw: str | None) -> str:
    """Extract the first semver-like token (handles ``codex-cli 0.141.0``)."""
    if not raw:
        return ""
    match = _VERSION_RE.search(raw)
    if match:
        return match.group(0)
    parts = raw.strip().split()
    return parts[0] if parts else ""


def _collect_cli_census(
    *,
    target_id: str,
    binary: str,
    snapshot_file: str,
    help_text: str | None = None,
    version: str | None = None,
    runner: Runner | None = None,
) -> Census:
    """Collect a structural census for one CLI target.

    Resolution order for the help surface:
      1. ``help_text`` argument (used as-is, for tests/replays);
      2. the live binary via ``runner(["--help"])``;
      3. the bundled snapshot (always present).
    """
    run = runner or _make_runner(binary)
    source: str

    if help_text is not None:
        source = "injected --help text"
    else:
        live = run(["--help"])
        if live:
            help_text = live
            source = f"{binary} --help (live binary)"
        else:
            help_text = (_DATA / snapshot_file).read_text(encoding="utf-8")
            source = f"bundled snapshot ({binary} --help)"

    if version is None:
        version = _clean_version(run(["--version"])) if help_text is not None else ""
    else:
        version = _clean_version(version)

    return Census(
        target=target_id,
        source=source,
        capabilities=tuple(parse_help_text(help_text)),
        target_version=version,
    )


def collect_puku_census(
    *,
    help_text: str | None = None,
    version: str | None = None,
    runner: Runner | None = None,
) -> Census:
    """Collect the ``puku-cli`` capability census (Channel A — structural)."""
    return _collect_cli_census(
        target_id=PUKU_TARGET_ID,
        binary=PUKU_BINARY,
        snapshot_file="puku_cli_help.txt",
        help_text=help_text,
        version=version,
        runner=runner,
    )


def collect_codex_census(
    *,
    help_text: str | None = None,
    version: str | None = None,
    runner: Runner | None = None,
) -> Census:
    """Collect the ``codex`` capability census (Channel A — structural)."""
    return _collect_cli_census(
        target_id=CODEX_TARGET_ID,
        binary=CODEX_BINARY,
        snapshot_file="codex_help.txt",
        help_text=help_text,
        version=version,
        runner=runner,
    )


# Registry of census collectors keyed by target id.
_COLLECTORS: dict[str, Callable[..., Census]] = {
    PUKU_TARGET_ID: collect_puku_census,
    CODEX_TARGET_ID: collect_codex_census,
}


def has_collector(target: str) -> bool:
    return target in _COLLECTORS


def collect_census(target: str, *, runner: Runner | None = None) -> Census:
    """Collect the census for ``target`` via its registered collector."""
    collector = _COLLECTORS.get(target)
    if collector is None:
        known = ", ".join(sorted(_COLLECTORS)) or "(none)"
        raise ValueError(
            f"no census collector for target '{target}' (collectors: {known})"
        )
    return collector(runner=runner)
