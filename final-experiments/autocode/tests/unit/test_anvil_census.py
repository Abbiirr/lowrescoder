"""Tests for the Anvil copycat capability model + ``--help`` surface parser.

Channel A reads the *observable* structure of a target. For a CLI agent the
observable structure is its command/flag surface, which ``--help`` exposes. The
parser turns that text into a normalized capability set we can diff and
serialize. Sample text is a faithful slice of real ``puku-cli --help`` output.
"""
# ruff: noqa: E501 - PUKU_HELP is a verbatim --help fixture; its lines are wide by design.

from __future__ import annotations

from pathlib import Path

from autocode.anvil.census import (
    Capability,
    Census,
    parse_help_text,
)

PUKU_HELP = """\
Usage: puku-cli [options] [command] [prompt]

Puku - starts an interactive session by default, use -p/--print for
non-interactive output

Arguments:
  prompt                                            Your prompt

Options:
  --add-dir <directories...>                        Additional directories to allow tool access to
  -c, --continue                                    Continue the most recent conversation in the current directory
  --effort <level>                                  Effort level for the current session (low, medium, high, max)
  --max-budget-usd <amount>                         Maximum dollar amount to spend on API calls (only works with --print)
  --output-format <format>                          Output format (only works with --print): "text" (default), "json" (single result), or "stream-json" (realtime streaming) (choices: "text", "json", "stream-json")
  --permission-mode <mode>                          Permission mode to use for the session (choices: "acceptEdits", "bypassPermissions", "default", "dontAsk", "plan", "auto")
  -p, --print                                       Print response and exit (useful for pipes).
  -v, --version                                     Output the version number

Commands:
  doctor                                            Check the health of your Puku auto-updater.
  mcp                                               Configure and manage MCP servers
  plugin|plugins                                    Manage Puku plugins
"""


def _by_id(caps: list[Capability]) -> dict[str, Capability]:
    return {c.id: c for c in caps}


def test_parses_long_flags() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    assert "flag:max-budget-usd" in caps
    cap = caps["flag:max-budget-usd"]
    assert cap.kind == "flag"
    assert "--max-budget-usd" in cap.surface
    assert "Maximum dollar amount" in cap.description


def test_parses_short_and_long_flag_pairs() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    # `-c, --continue` -> canonical id from the long flag, both tokens in surface.
    assert "flag:continue" in caps
    assert set(caps["flag:continue"].surface) == {"-c", "--continue"}


def test_extracts_choices_into_metadata() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    pm = caps["flag:permission-mode"]
    assert pm.metadata.get("choices") == [
        "acceptEdits",
        "bypassPermissions",
        "default",
        "dontAsk",
        "plan",
        "auto",
    ]
    of = caps["flag:output-format"]
    assert of.metadata.get("choices") == ["text", "json", "stream-json"]


def test_parses_bracket_style_choices() -> None:
    # yargs-style (e.g. opencode): choices live in [brackets], not (parens).
    help_text = (
        "Options:\n"
        '  --log-level    log level    [string] [choices: "DEBUG", "INFO", "WARN", "ERROR"]\n'
    )
    caps = {c.id: c for c in parse_help_text(help_text)}
    assert caps["flag:log-level"].metadata.get("choices") == ["DEBUG", "INFO", "WARN", "ERROR"]


def test_flag_value_arity_detected() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    assert caps["flag:max-budget-usd"].metadata.get("takes_value") is True
    assert caps["flag:print"].metadata.get("takes_value") is False


def test_parses_subcommands() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    assert "cmd:doctor" in caps
    assert caps["cmd:doctor"].kind == "subcommand"
    # `plugin|plugins` -> primary name is the gap target, alias recorded.
    assert "cmd:plugin" in caps
    assert "plugins" in caps["cmd:plugin"].metadata.get("aliases", [])


def test_ignores_usage_and_arguments_noise() -> None:
    caps = _by_id(parse_help_text(PUKU_HELP))
    # The "prompt" positional under Arguments: is not a flag or subcommand.
    assert "flag:prompt" not in caps
    assert "cmd:prompt" not in caps


def test_wrapped_command_descriptions_are_not_parsed_as_commands() -> None:
    # Real commands sit at the command column; clap/commander wrap long
    # descriptions to a deeper-indented continuation line that must NOT be
    # mistaken for a command (regression from real `codex --help`).
    help_text = (
        "Commands:\n"
        "  apply    Apply the latest diff to your local\n"
        "           working tree [aliases: a]\n"
        "  resume   Resume a session; use --last to continue\n"
        "           the most recent\n"
        "  fork     Fork a session\n"
    )
    ids = {c.id for c in parse_help_text(help_text)}
    assert {"cmd:apply", "cmd:resume", "cmd:fork"} <= ids
    assert "cmd:working" not in ids
    assert "cmd:the" not in ids


def test_census_roundtrips_through_yaml(tmp_path: Path) -> None:
    caps = parse_help_text(PUKU_HELP)
    census = Census(target="puku-cli", source="puku-cli --help (v1.8.27)", capabilities=tuple(caps))
    out = tmp_path / "puku-cli.yaml"
    census.write_yaml(out)
    loaded = Census.read_yaml(out)
    assert loaded.target == "puku-cli"
    assert loaded.source == census.source
    assert {c.id for c in loaded.capabilities} == {c.id for c in census.capabilities}
    # Metadata (choices) survives the round-trip.
    loaded_by_id = _by_id(list(loaded.capabilities))
    assert loaded_by_id["flag:output-format"].metadata.get("choices") == [
        "text",
        "json",
        "stream-json",
    ]
