"""Tests for benchmark adapter behavior (retry loop, grading, prompts)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# scripts/ is not a package — add project root to sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.adapters.autocode_adapter import (  # noqa: E402
    BASH_ONLY_TOOLS,
    MAX_GRADE_ATTEMPTS,
    MIN_ATTEMPT_BUDGET_S,
    AutoCodeAdapter,
    classify_provider_mode,
)

from scripts.adapters.base import BenchmarkTask, BudgetProfile  # noqa: E402  # isort: skip


# --- A1: AutoCode adapter constants ---


def test_autocode_retry_loop_constants():
    """MAX_GRADE_ATTEMPTS and MIN_ATTEMPT_BUDGET_S exist and are sane."""
    assert MAX_GRADE_ATTEMPTS >= 2, "Need at least 2 attempts"
    assert MAX_GRADE_ATTEMPTS <= 10, "More than 10 is excessive"
    assert MIN_ATTEMPT_BUDGET_S >= 30, "Need at least 30s per attempt"
    assert MIN_ATTEMPT_BUDGET_S <= 300, "More than 300s is too conservative"


# --- A1: Prompt tests ---


def test_build_prompt_includes_grading_command():
    """Grading command appears in prompt when task has one."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-1",
        description="Fix a bug",
        grading_command="pytest tests/test_foo.py -x",
    )
    prompt = adapter._build_prompt(task)
    assert "pytest tests/test_foo.py -x" in prompt
    assert "GRADING COMMAND" in prompt


def test_build_prompt_mentions_test_patch():
    """Prompt states that test patch is pre-applied."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-2",
        description="Fix a bug",
    )
    prompt = adapter._build_prompt(task)
    assert "pre-applied" in prompt
    assert "SOURCE" in prompt


def test_build_prompt_includes_source_candidates():
    """Initial prompt should surface likely source files early."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-source-candidates",
        description="Fix a bug",
        extra={
            "FAIL_TO_PASS": ["FAILED testing/test_unittest.py::test_case"],
            "test_patch": (
                "diff --git a/testing/test_unittest.py "
                "b/testing/test_unittest.py\n"
                "+++ b/testing/test_unittest.py\n"
            ),
        },
    )
    prompt = adapter._build_prompt(
        task,
        initial_test_output='  File "/work/src/core.py", line 10, in handle\n',
    )
    assert "LIKELY SOURCE FILES TO CHECK FIRST" in prompt
    assert "src/_pytest/unittest.py" in prompt
    assert "core.py" in prompt


def test_build_prompt_no_grading_command():
    """When no grading command, prompt omits the GRADING COMMAND section."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-3",
        description="Fix a bug",
        grading_command="",
    )
    prompt = adapter._build_prompt(task)
    assert "GRADING COMMAND" not in prompt


def test_build_prompt_bash_only_no_write_file():
    """Bash-only prompt uses run_command/sed, not write_file."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-bash",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
        extra={"tool_restriction": "bash-only"},
    )
    prompt = adapter._build_prompt(task)
    assert "write_file" not in prompt
    assert "run_command" in prompt
    assert "sed" in prompt
    assert "read_file" in prompt


def test_build_prompt_normal_uses_write_file():
    """Normal prompt keeps edit_file primary and run_command as fallback."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-normal",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    prompt = adapter._build_prompt(task)
    assert "write_file" in prompt
    workflow = prompt.split("MANDATORY WORKFLOW")[1].split("RULES")[0]
    assert "edit_file" in workflow
    assert "run_command" in workflow


# --- A1: Feedback prompt ---


def test_build_feedback_prompt():
    """Feedback prompt contains structured failure info and grading command."""
    adapter = AutoCodeAdapter(model="test-model")
    grading_output = "FAILED test_foo.py::test_bar - AssertionError: 1 != 2"
    grading_command = "pytest tests/test_foo.py -x"

    feedback = adapter._build_feedback_prompt(grading_output, grading_command)

    assert "FAILING TESTS" in feedback
    assert "AssertionError" in feedback
    assert grading_command in feedback
    assert "SOURCE" in feedback


def test_build_feedback_prompt_truncates_long_output():
    """Feedback prompt truncates output tail to 1500 chars."""
    adapter = AutoCodeAdapter(model="test-model")
    long_output = "x" * 5000
    feedback = adapter._build_feedback_prompt(long_output, "pytest")
    # The tail should be at most 1500 chars of the output
    assert "x" * 1500 in feedback
    assert "x" * 2000 not in feedback


def test_build_feedback_prompt_test_file_warning():
    """Feedback prompt warns when test files were changed."""
    adapter = AutoCodeAdapter(model="test-model")
    feedback = adapter._build_feedback_prompt(
        "FAILED test_bar", "pytest",
        changed_files=["tests/test_foo.py", "src/foo.py"],
        test_files_changed=True,
    )
    assert "REVERTED" in feedback
    assert "test files" in feedback.lower()
    assert "src/foo.py" in feedback


def test_build_feedback_prompt_stagnation_warning():
    """Feedback prompt warns on stagnation."""
    adapter = AutoCodeAdapter(model="test-model")
    feedback = adapter._build_feedback_prompt(
        "FAILED test_bar", "pytest",
        stagnation_count=1,
    )
    assert "DIFFERENT approach" in feedback


def test_build_feedback_prompt_repeated_failure_warning():
    """Feedback prompt should call out repeated unchanged failures."""
    adapter = AutoCodeAdapter(model="test-model")
    feedback = adapter._build_feedback_prompt(
        "FAILED test_bar", "pytest",
        repeated_failure=True,
    )
    assert "SAME failure persisted" in feedback


def test_build_feedback_prompt_zero_diff_points_to_candidate_files():
    """Zero-diff retries should force a direct edit in candidate source files."""
    adapter = AutoCodeAdapter(model="test-model")
    feedback = adapter._build_feedback_prompt(
        "FAILED testing/test_unittest.py::test_case\n"
        '  File "/work/src/core.py", line 10, in handle\n',
        "pytest",
        consecutive_zero_diffs=1,
        test_patch=(
            "diff --git a/testing/test_unittest.py "
            "b/testing/test_unittest.py\n"
            "+++ b/testing/test_unittest.py\n"
        ),
    )
    assert "MUST modify one of these source files directly" in feedback
    assert "src/_pytest/unittest.py" in feedback


# --- A2: Codex adapter grading behavior ---


def test_codex_adapter_uses_grading_command():
    """Codex adapter runs grading_command and uses its exit code for resolved."""
    from scripts.adapters.codex_adapter import CodexAdapter

    adapter = CodexAdapter()
    task = BenchmarkTask(
        task_id="test-codex",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    sandbox = Path("/tmp/fake-sandbox")
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    # Mock subprocess.run to simulate CLI success + grading failure
    cli_result = MagicMock(
        returncode=0, stdout="Done", stderr="",
    )
    grade_result = MagicMock(
        returncode=1, stdout="FAILED", stderr="test error",
    )

    with patch("shutil.which", return_value="/usr/bin/codex"), \
         patch("subprocess.run", side_effect=[cli_result, grade_result]):
        result = asyncio.run(
            adapter.solve_task(task, sandbox, budget),
        )

    # CLI succeeded but grading failed → resolved must be False
    assert result.resolved is False
    assert result.task_id == "test-codex"


def test_codex_adapter_grading_pass():
    """Codex adapter marks resolved=True when grading passes."""
    from scripts.adapters.codex_adapter import CodexAdapter

    adapter = CodexAdapter()
    task = BenchmarkTask(
        task_id="test-codex-pass",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    sandbox = Path("/tmp/fake-sandbox")
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    cli_result = MagicMock(returncode=0, stdout="Done", stderr="")
    grade_result = MagicMock(
        returncode=0, stdout="PASSED", stderr="",
    )

    with patch("shutil.which", return_value="/usr/bin/codex"), \
         patch("subprocess.run", side_effect=[cli_result, grade_result]):
        result = asyncio.run(
            adapter.solve_task(task, sandbox, budget),
        )

    assert result.resolved is True


def test_codex_adapter_no_grading_uses_exit_code():
    """Without grading_command, Codex uses CLI exit code for resolved."""
    from scripts.adapters.codex_adapter import CodexAdapter

    adapter = CodexAdapter()
    task = BenchmarkTask(
        task_id="test-codex-no-grade",
        description="Fix a bug",
        grading_command="",
    )
    sandbox = Path("/tmp/fake-sandbox")
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    cli_result = MagicMock(returncode=0, stdout="Done", stderr="")

    with patch("shutil.which", return_value="/usr/bin/codex"), \
         patch("subprocess.run", return_value=cli_result):
        result = asyncio.run(
            adapter.solve_task(task, sandbox, budget),
        )

    assert result.resolved is True


# --- A2: Claude adapter grading behavior ---


def test_claude_adapter_uses_grading_command():
    """Claude adapter runs grading_command and uses its exit code for resolved."""
    from scripts.adapters.claude_adapter import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter()
    task = BenchmarkTask(
        task_id="test-claude",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    sandbox = Path("/tmp/fake-sandbox")
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    cli_result = MagicMock(returncode=0, stdout="Done", stderr="")
    grade_result = MagicMock(
        returncode=1, stdout="FAILED", stderr="test error",
    )

    with patch("shutil.which", return_value="/usr/bin/claude"), \
         patch("subprocess.run", side_effect=[cli_result, grade_result]):
        result = asyncio.run(
            adapter.solve_task(task, sandbox, budget),
        )

    # CLI succeeded but grading failed → resolved must be False
    assert result.resolved is False


def test_claude_adapter_grading_pass():
    """Claude adapter marks resolved=True when grading passes."""
    from scripts.adapters.claude_adapter import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter()
    task = BenchmarkTask(
        task_id="test-claude-pass",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    sandbox = Path("/tmp/fake-sandbox")
    budget = BudgetProfile(wall_time_s=60, token_cap=1000, max_tool_calls=10)

    cli_result = MagicMock(returncode=0, stdout="Done", stderr="")
    grade_result = MagicMock(
        returncode=0, stdout="PASSED", stderr="",
    )

    with patch("shutil.which", return_value="/usr/bin/claude"), \
         patch("subprocess.run", side_effect=[cli_result, grade_result]):
        result = asyncio.run(
            adapter.solve_task(task, sandbox, budget),
        )

    assert result.resolved is True


# --- B8: Provider classification ---


def test_classify_ollama_is_local_free():
    assert classify_provider_mode("ollama", "qwen2.5-coder:14b") == "local_free"


def test_classify_openrouter_free_is_local_free():
    assert classify_provider_mode("openrouter", "z-ai/glm-4.5-air:free") == "local_free"


def test_classify_openrouter_paid_is_paid_metered(monkeypatch):
    monkeypatch.delenv("AUTOCODE_LLM_API_BASE", raising=False)
    assert classify_provider_mode("openrouter", "anthropic/claude-3.5-sonnet") == "paid_metered"


def test_classify_unknown_fails_closed(monkeypatch):
    monkeypatch.delenv("AUTOCODE_LLM_API_BASE", raising=False)
    assert classify_provider_mode("some-cloud", "gpt-4") == "paid_metered"


def test_autocode_adapter_ollama_provider_mode():
    adapter = AutoCodeAdapter(model="qwen3-coder:latest")
    # Default provider is ollama (from env or default)
    adapter._provider = "ollama"
    assert adapter.provider_mode == "local_free"


def test_autocode_adapter_openrouter_free_provider_mode():
    adapter = AutoCodeAdapter(model="z-ai/glm-4.5-air:free")
    adapter._provider = "openrouter"
    assert adapter.provider_mode == "local_free"


def test_autocode_adapter_openrouter_paid_provider_mode(monkeypatch):
    monkeypatch.delenv("AUTOCODE_LLM_API_BASE", raising=False)
    adapter = AutoCodeAdapter(model="anthropic/claude-3.5-sonnet")
    adapter._provider = "openrouter"
    assert adapter.provider_mode == "paid_metered"


def test_autocode_pre_task_healthcheck_ollama():
    adapter = AutoCodeAdapter(model="test-model")
    adapter._provider = "ollama"
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=response):
        adapter.pre_task_healthcheck()


def test_autocode_pre_task_healthcheck_non_ollama_noop(monkeypatch):
    monkeypatch.delenv("AUTOCODE_LLM_API_BASE", raising=False)
    adapter = AutoCodeAdapter(model="test-model")
    adapter._provider = "openrouter"
    with patch("urllib.request.urlopen") as mock_urlopen:
        adapter.pre_task_healthcheck()
    mock_urlopen.assert_not_called()


# --- B8: Tool filtering ---


def test_tool_registry_filter():
    """ToolRegistry.filter() returns only the requested tools."""
    from autocode.agent.tools import ToolDefinition, ToolRegistry

    reg = ToolRegistry()
    reg.register(ToolDefinition(
        name="run_command", description="run", parameters={},
        handler=lambda: "",
    ))
    reg.register(ToolDefinition(
        name="read_file", description="read", parameters={},
        handler=lambda: "",
    ))
    reg.register(ToolDefinition(
        name="write_file", description="write", parameters={},
        handler=lambda: "",
    ))

    filtered = reg.filter({"run_command", "read_file"})
    names = {t.name for t in filtered.get_all()}
    assert names == {"run_command", "read_file"}


def test_bash_only_constant_is_correct():
    """BASH_ONLY_TOOLS contains exactly run_command and read_file."""
    assert BASH_ONLY_TOOLS == frozenset({"run_command", "read_file"})


# --- P0: Patch file extraction ---


def test_extract_patch_files_unified_diff():
    """_extract_patch_files parses unified diff headers."""
    from scripts.benchmark_runner import _extract_patch_files

    patch = (
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,3 +1,5 @@\n"
        "+import bar\n"
    )
    files = _extract_patch_files(patch)
    assert files == ["tests/test_foo.py"]


def test_extract_patch_files_multiple():
    """_extract_patch_files handles multi-file patches."""
    from scripts.benchmark_runner import _extract_patch_files

    patch = (
        "--- a/tests/test_a.py\n"
        "+++ b/tests/test_a.py\n"
        "@@ -1 +1 @@\n"
        "--- a/tests/test_b.py\n"
        "+++ b/tests/test_b.py\n"
        "@@ -1 +1 @@\n"
    )
    files = _extract_patch_files(patch)
    assert files == ["tests/test_a.py", "tests/test_b.py"]


def test_extract_patch_files_empty():
    """_extract_patch_files returns empty list for empty input."""
    from scripts.benchmark_runner import _extract_patch_files

    assert _extract_patch_files("") == []


# --- P0: Grading output parsers ---


def test_parse_failing_tests():
    """_parse_failing_tests extracts FAILED lines."""
    output = (
        "PASSED test_foo.py::test_ok\n"
        "FAILED test_foo.py::test_bar - AssertionError\n"
        "ERROR test_baz.py::test_crash\n"
        "some other line\n"
    )
    tests = AutoCodeAdapter._parse_failing_tests(output)
    assert len(tests) == 2
    assert any("test_bar" in t for t in tests)
    assert any("test_crash" in t for t in tests)


def test_parse_assertions():
    """_parse_assertions extracts error lines."""
    output = (
        "AssertionError: 1 != 2\n"
        "some normal output\n"
        "TypeError: unsupported operand\n"
    )
    assertions = AutoCodeAdapter._parse_assertions(output)
    assert len(assertions) == 2
    assert any("AssertionError" in a for a in assertions)
    assert any("TypeError" in a for a in assertions)


def test_is_docker_exec_infra_output():
    assert AutoCodeAdapter._is_docker_exec_infra_output(
        "Error response from daemon: container abc is not running",
    )
    assert not AutoCodeAdapter._is_docker_exec_infra_output(
        "FAILED test_foo.py::test_bar - AssertionError",
    )


def test_git_changed_files_filters_benchmark_bookkeeping(tmp_path: Path):
    adapter = AutoCodeAdapter.__new__(AutoCodeAdapter)
    proc = MagicMock(
        returncode=0,
        stdout="\n".join([
            ".benchmark-sessions.db",
            ".benchmark-sessions.db-wal",
            "src/foo.py",
        ]),
    )
    with patch("subprocess.run", return_value=proc):
        changed = adapter._git_changed_files(tmp_path)
    assert changed == ["src/foo.py"]
