"""Tests for Phase B items 2-5 + integration loose ends: tool-result cache,
LSP tools, fail-closed sandbox, pattern-based permission rules,
clear_tool_results meta-tool, and permission_rules enforcement at
_handle_run_command.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.agent.lsp_tools import (
    _JEDI_OK,
    find_references,
    get_type_hint,
    goto_definition,
    list_symbols,
)
from autocode.agent.permission_rules import (
    evaluate,
    parse_rule,
    validate_rules,
)
from autocode.agent.sandbox import (
    SandboxConfig,
    SandboxPolicy,
    SandboxResult,
    run_sandboxed,
)
from autocode.agent.tool_result_cache import (
    ToolResultCache,
)

# --- Item 2: Tool-result clearing primitive -------------------------------


class TestToolResultCacheRecord:
    def test_record_returns_id(self) -> None:
        cache = ToolResultCache()
        tid = cache.record("read_file", {"path": "a.txt"}, "content")
        assert tid.startswith("tr")
        assert len(cache.entries) == 1

    def test_record_assigns_size(self) -> None:
        cache = ToolResultCache()
        cache.record("read_file", {"path": "a.txt"}, "hello")
        assert cache.entries[0].size_bytes == 5

    def test_record_string_args(self) -> None:
        cache = ToolResultCache()
        cache.record("run_command", "ls -la", "output")
        assert cache.entries[0].args_preview == "ls -la"

    def test_record_long_args_preview_truncated(self) -> None:
        cache = ToolResultCache()
        long_args = {"cmd": "x" * 200}
        cache.record("run_command", long_args, "output")
        assert "..." in cache.entries[0].args_preview
        assert len(cache.entries[0].args_preview) <= 80


class TestToolResultCacheClearModes:
    def test_clear_all(self) -> None:
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        cache.record("read_file", {"p": "b"}, "b")
        n = cache.clear(all=True)
        assert n == 2
        assert len(cache.live_entries()) == 0

    def test_clear_by_id(self) -> None:
        cache = ToolResultCache()
        id1 = cache.record("read_file", {"p": "a"}, "a")
        id2 = cache.record("read_file", {"p": "b"}, "b")
        n = cache.clear(ids=[id1])
        assert n == 1
        live = cache.live_entries()
        assert len(live) == 1
        assert live[0].id == id2

    def test_clear_by_tool(self) -> None:
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        cache.record("read_file", {"p": "b"}, "b")
        cache.record("search_text", {"q": "x"}, "hit")
        n = cache.clear(tool="read_file")
        assert n == 2
        live = cache.live_entries()
        assert len(live) == 1
        assert live[0].tool == "search_text"

    def test_clear_older_than(self) -> None:
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        # Force an older created_at on the first entry
        cache.entries[0].created_at -= 10_000
        cache.record("read_file", {"p": "b"}, "b")
        n = cache.clear(older_than_seconds=1000)
        assert n == 1
        assert len(cache.live_entries()) == 1

    def test_summary_empty(self) -> None:
        assert "empty" in ToolResultCache().summary()

    def test_summary_with_entries(self) -> None:
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "hello")
        text = cache.summary()
        assert "read_file" in text
        assert "tr" in text  # id prefix

    def test_budget_evicts_by_count(self) -> None:
        cache = ToolResultCache(max_entries=3)
        for i in range(5):
            cache.record("read_file", {"p": str(i)}, f"content{i}")
        assert len(cache.entries) == 3

    def test_budget_evicts_by_bytes(self) -> None:
        # Tight byte budget
        cache = ToolResultCache(max_entries=100, max_total_bytes=20)
        for i in range(5):
            cache.record("read_file", {"p": str(i)}, "x" * 10)
        # After 5 x 10-byte entries with a 20-byte budget, only a couple fit
        live = cache.live_entries()
        assert sum(e.size_bytes for e in live) <= 20


# --- Item 3: LSP tools via Jedi -------------------------------------------


@pytest.fixture()
def mini_module(tmp_path: Path) -> Path:
    f = tmp_path / "mini.py"
    f.write_text(
        "def greet(name: str) -> str:\n"
        "    return f'hello {name}'\n"
        "\n"
        "\n"
        "class Greeter:\n"
        "    def __init__(self, prefix: str) -> None:\n"
        "        self.prefix = prefix\n"
        "\n"
        "    def say(self, name: str) -> str:\n"
        "        return f'{self.prefix} {name}'\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        "    msg = greet('world')\n"
        "    print(msg)\n"
    )
    return f


class TestLspGotoDefinition:
    def test_goto_definition_resolves_local_function(self, mini_module: Path) -> None:
        if not _JEDI_OK:
            pytest.skip("jedi not installed")
        # Line 14 is `msg = greet('world')` — cursor on `greet`
        result = goto_definition(str(mini_module), line=14, column=11)
        assert result.error == ""
        assert len(result.locations) >= 1
        # Should point back at the def on line 1
        assert any(loc.line == 1 for loc in result.locations)

    def test_goto_definition_missing_file(self, tmp_path: Path) -> None:
        if not _JEDI_OK:
            pytest.skip("jedi not installed")
        result = goto_definition(
            str(tmp_path / "nope.py"), line=1, column=1
        )
        assert "does not exist" in result.error


class TestLspFindReferences:
    def test_find_references_finds_greet_call(self, mini_module: Path) -> None:
        if not _JEDI_OK:
            pytest.skip("jedi not installed")
        # Cursor on `greet` at its definition (line 1, col ~5)
        result = find_references(str(mini_module), line=1, column=5)
        assert result.error == ""
        # Expect at least 2 references: the def and the call in main()
        assert len(result.locations) >= 2


class TestLspGetType:
    def test_get_type_hint_returns_string(self, mini_module: Path) -> None:
        if not _JEDI_OK:
            pytest.skip("jedi not installed")
        # Cursor on `msg` (line 14, col ~5)
        result = get_type_hint(str(mini_module), line=14, column=5)
        assert result.error == ""
        # type_hint should mention str or be a non-empty description
        assert result.type_hint != ""


class TestLspSymbols:
    def test_list_symbols_finds_top_level_defs(self, mini_module: Path) -> None:
        if not _JEDI_OK:
            pytest.skip("jedi not installed")
        result = list_symbols(str(mini_module))
        assert result.error == ""
        names = " ".join(result.symbols)
        assert "greet" in names
        assert "Greeter" in names
        assert "main" in names


# --- Item 4: Fail-closed sandbox mode -------------------------------------


class TestSandboxFailClosed:
    def test_fail_closed_when_no_sandbox(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When fail_if_unavailable=True and no sandbox is detected, refuse."""
        # Force detect_sandbox_support to report no sandbox available
        monkeypatch.setattr(
            "autocode.agent.sandbox.detect_sandbox_support",
            lambda: {"bwrap": False, "seatbelt": False, "seccomp": False, "none": True},
        )
        cfg = SandboxConfig(
            policy=SandboxPolicy.WRITABLE_PROJECT,
            fail_if_unavailable=True,
            timeout_s=5,
        )
        result = run_sandboxed("echo hi", cfg)
        assert result.returncode != 0
        assert "fail_if_unavailable" in result.stderr
        assert result.enforced is False
        # Must NOT have executed the command
        assert "hi" not in result.stdout

    def test_default_still_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When fail_if_unavailable=False (default), falls back to restricted."""
        monkeypatch.setattr(
            "autocode.agent.sandbox.detect_sandbox_support",
            lambda: {"bwrap": False, "seatbelt": False, "seccomp": False, "none": True},
        )
        cfg = SandboxConfig(
            policy=SandboxPolicy.WRITABLE_PROJECT,
            fail_if_unavailable=False,
            timeout_s=5,
        )
        result = run_sandboxed("echo fallback_ok", cfg)
        # Should have actually run via restricted path
        assert "fallback_ok" in result.stdout or result.returncode == 0

    def test_config_defaults_to_false(self) -> None:
        """Back-compat: SandboxConfig() should default to fail_if_unavailable=False."""
        cfg = SandboxConfig()
        assert cfg.fail_if_unavailable is False


# --- Item 5: Pattern-based permission rules -------------------------------


class TestPermissionRuleParsing:
    def test_parse_valid_header(self) -> None:
        rule = parse_rule("Bash(npm run test *)", "allow")
        assert rule.tool == "Bash"
        assert rule.pattern == "npm run test *"
        assert rule.effect == "allow"

    def test_parse_read_rule(self) -> None:
        rule = parse_rule("Read(**/*.py)", "allow")
        assert rule.tool == "Read"
        assert rule.pattern == "**/*.py"

    def test_parse_invalid_header_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_rule("not a rule", "allow")

    def test_parse_invalid_effect_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_rule("Bash(ls)", "maybe")  # type: ignore

    def test_parse_with_inline_tests(self) -> None:
        rule = parse_rule(
            "Bash(npm run test *)",
            "allow",
            matches=["npm run test", "npm run test --coverage"],
            not_matches=["npm run start"],
        )
        assert len(rule.matches) == 2
        assert len(rule.not_matches) == 1


class TestPermissionRuleMatching:
    def test_exact_match(self) -> None:
        rule = parse_rule("Bash(git status)", "allow")
        assert rule.test("git status") is True
        assert rule.test("git diff") is False

    def test_wildcard_suffix(self) -> None:
        rule = parse_rule("Bash(npm run test*)", "allow")
        assert rule.test("npm run test") is True
        assert rule.test("npm run test:unit") is True
        assert rule.test("npm run build") is False

    def test_double_star_substring(self) -> None:
        rule = parse_rule("Read(**/*.py)", "allow")
        assert rule.test("src/foo.py") is True
        assert rule.test("a/b/c/deep.py") is True
        assert rule.test("foo.go") is False


class TestDenyFirstPrecedence:
    def test_deny_wins_even_when_allow_matches(self) -> None:
        rules = [
            parse_rule("Bash(npm run *)", "allow"),
            parse_rule("Bash(npm run start)", "deny"),
        ]
        decision = evaluate("Bash", "npm run start", rules)
        assert decision.effect == "deny"
        assert "deny" in decision.reason.lower() or "denied" in decision.reason.lower()

    def test_allow_wins_when_no_deny(self) -> None:
        rules = [parse_rule("Bash(npm run *)", "allow")]
        decision = evaluate("Bash", "npm run test", rules)
        assert decision.effect == "allow"

    def test_no_match_returns_default(self) -> None:
        rules = [parse_rule("Bash(npm run *)", "allow")]
        decision = evaluate("Bash", "rm -rf /", rules, default="deny")
        assert decision.effect == "deny"
        assert "no matching rule" in decision.reason

    def test_tool_mismatch_ignored(self) -> None:
        rules = [parse_rule("Read(*.py)", "allow")]
        # Same target but different tool
        decision = evaluate("Bash", "foo.py", rules, default="deny")
        assert decision.effect == "deny"


class TestPermissionInlineSelfTests:
    def test_rule_with_passing_tests(self) -> None:
        rule = parse_rule(
            "Bash(npm run test*)",
            "allow",
            matches=["npm run test", "npm run test:unit"],
            not_matches=["npm run start"],
        )
        errors = rule.run_self_tests()
        assert errors == []

    def test_rule_with_failing_match_test(self) -> None:
        rule = parse_rule(
            "Bash(git status)",
            "allow",
            matches=["git status", "git diff"],  # git diff should NOT match exact pattern
        )
        errors = rule.run_self_tests()
        assert len(errors) == 1
        assert "git diff" in errors[0]

    def test_rule_with_failing_not_match_test(self) -> None:
        rule = parse_rule(
            "Bash(npm *)",
            "allow",
            not_matches=["npm install"],  # "npm install" DOES match, so self-test fails
        )
        errors = rule.run_self_tests()
        assert len(errors) == 1
        assert "should NOT match" in errors[0]

    def test_validate_rules_aggregates_errors(self) -> None:
        rules = [
            parse_rule(
                "Bash(good *)",
                "allow",
                matches=["good thing"],  # passes
            ),
            parse_rule(
                "Bash(bad)",
                "allow",
                matches=["wrong"],  # fails
            ),
        ]
        errors = validate_rules(rules)
        assert len(errors) == 1


# --- Integration Loose End 1: clear_tool_results meta-tool -----------------


class TestClearToolResultsHandler:
    """Tests for the _handle_clear_tool_results handler function."""

    def test_handler_exists(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        assert callable(_handle_clear_tool_results)

    def test_summary_mode(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        cache.record("read_file", {"path": "a.txt"}, "content")
        result = _handle_clear_tool_results(cache=cache, mode="summary")
        assert "read_file" in result
        assert "1 live" in result

    def test_clear_all_mode(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        cache.record("read_file", {"p": "b"}, "b")
        result = _handle_clear_tool_results(cache=cache, mode="all")
        assert "2" in result  # cleared count
        assert len(cache.live_entries()) == 0

    def test_clear_by_tool_mode(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        cache.record("search_text", {"q": "x"}, "hit")
        result = _handle_clear_tool_results(cache=cache, mode="by_tool", tool="read_file")
        assert "1" in result
        assert len(cache.live_entries()) == 1
        assert cache.live_entries()[0].tool == "search_text"

    def test_clear_by_ids_mode(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        id1 = cache.record("read_file", {"p": "a"}, "a")
        cache.record("read_file", {"p": "b"}, "b")
        result = _handle_clear_tool_results(cache=cache, mode="by_ids", ids=[id1])
        assert "1" in result
        assert len(cache.live_entries()) == 1

    def test_clear_older_than_mode(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        cache.entries[0].created_at -= 10_000
        cache.record("read_file", {"p": "b"}, "b")
        result = _handle_clear_tool_results(
            cache=cache, mode="older_than", older_than_seconds=1000
        )
        assert "1" in result
        assert len(cache.live_entries()) == 1

    def test_invalid_mode_returns_error(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        result = _handle_clear_tool_results(cache=cache, mode="bogus")
        assert "unknown mode" in result.lower() or "invalid" in result.lower()

    def test_default_mode_is_summary(self) -> None:
        from autocode.agent.tools import _handle_clear_tool_results
        cache = ToolResultCache()
        cache.record("read_file", {"p": "a"}, "a")
        result = _handle_clear_tool_results(cache=cache)
        assert "read_file" in result  # summary output


class TestClearToolResultsRegistration:
    """Tests that clear_tool_results is registered when cache is provided."""

    def test_registered_when_cache_provided(self) -> None:
        from autocode.agent.tools import create_default_registry
        cache = ToolResultCache()
        reg = create_default_registry(project_root="/tmp", tool_result_cache=cache)
        tool = reg.get("clear_tool_results")
        assert tool is not None
        assert "clear" in tool.description.lower() or "result" in tool.description.lower()

    def test_not_registered_without_cache(self) -> None:
        from autocode.agent.tools import create_default_registry
        reg = create_default_registry(project_root="/tmp")
        tool = reg.get("clear_tool_results")
        assert tool is None

    def test_handler_works_through_registry(self) -> None:
        from autocode.agent.tools import create_default_registry
        cache = ToolResultCache()
        cache.record("read_file", {"p": "test"}, "content")
        reg = create_default_registry(project_root="/tmp", tool_result_cache=cache)
        tool = reg.get("clear_tool_results")
        assert tool is not None
        result = tool.handler(mode="summary")
        assert "read_file" in result


# --- Integration Loose End 2: permission_rules enforcement at run_command ---


class TestRunCommandPermissionEnforcement:
    """Tests that _handle_run_command evaluates permission rules before executing."""

    def test_denied_command_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A command matching a deny rule should not execute."""
        from autocode.agent.tools import _handle_run_command
        from autocode.config import AutoCodeConfig

        # Mock load_config to return config with a deny rule
        cfg = AutoCodeConfig()
        cfg.shell.permission_rules = [
            {"header": "Bash(rm -rf *)", "effect": "deny"},
        ]
        monkeypatch.setattr(
            "autocode.config.load_config",
            lambda: cfg,
        )
        result = _handle_run_command(command="rm -rf /tmp/foo")
        assert "denied" in result.lower() or "permission" in result.lower()
        # Should NOT contain actual command output
        assert "[exit code" not in result or "denied" in result.lower()

    def test_allowed_command_proceeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A command matching an allow rule should execute normally."""
        from autocode.agent.tools import _handle_run_command
        from autocode.config import AutoCodeConfig

        cfg = AutoCodeConfig()
        cfg.shell.permission_rules = [
            {"header": "Bash(echo *)", "effect": "allow"},
        ]
        monkeypatch.setattr(
            "autocode.config.load_config",
            lambda: cfg,
        )
        # Also mock run_sandboxed to avoid real shell execution in tests

        monkeypatch.setattr(
            "autocode.agent.sandbox.run_sandboxed",
            lambda cmd, cfg: SandboxResult(
                stdout="hello", stderr="", returncode=0, enforced=False
            ),
        )
        result = _handle_run_command(command="echo hello")
        assert "hello" in result
        assert "denied" not in result.lower()

    def test_no_rules_allows_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no permission rules exist, commands proceed normally."""
        from autocode.agent.tools import _handle_run_command
        from autocode.config import AutoCodeConfig

        cfg = AutoCodeConfig()
        # No permission_rules set — should default to empty list
        monkeypatch.setattr(
            "autocode.config.load_config",
            lambda: cfg,
        )

        monkeypatch.setattr(
            "autocode.agent.sandbox.run_sandboxed",
            lambda cmd, cfg: SandboxResult(
                stdout="ok", stderr="", returncode=0, enforced=False
            ),
        )
        result = _handle_run_command(command="echo ok")
        assert "ok" in result

    def test_deny_rule_takes_precedence_over_allow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deny-first semantics: deny wins even when an allow also matches."""
        from autocode.agent.tools import _handle_run_command
        from autocode.config import AutoCodeConfig

        cfg = AutoCodeConfig()
        cfg.shell.permission_rules = [
            {"header": "Bash(npm *)", "effect": "allow"},
            {"header": "Bash(npm run start)", "effect": "deny"},
        ]
        monkeypatch.setattr(
            "autocode.config.load_config",
            lambda: cfg,
        )
        result = _handle_run_command(command="npm run start")
        assert "denied" in result.lower() or "permission" in result.lower()
