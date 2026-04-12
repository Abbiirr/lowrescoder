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

from benchmarks.adapters.autocode_adapter import (  # noqa: E402
    BASH_ONLY_TOOLS,
    MAX_GRADE_ATTEMPTS,
    MIN_ATTEMPT_BUDGET_S,
    AutoCodeAdapter,
    classify_provider_mode,
)

from benchmarks.adapters.base import BenchmarkTask, BudgetProfile  # noqa: E402  # isort: skip


# --- A1: AutoCode adapter constants ---


def test_autocode_retry_loop_constants():
    """MAX_GRADE_ATTEMPTS and MIN_ATTEMPT_BUDGET_S exist and are sane."""
    assert MAX_GRADE_ATTEMPTS >= 2, "Need at least 2 attempts"
    assert MAX_GRADE_ATTEMPTS <= 10, "More than 10 is excessive"
    assert MIN_ATTEMPT_BUDGET_S >= 30, "Need at least 30s per attempt"
    assert MIN_ATTEMPT_BUDGET_S <= 300, "More than 300s is too conservative"


def test_benchmark_task_from_dict_flattens_nested_extra():
    """Manifest nested `extra` fields should land directly in task.extra."""
    task = BenchmarkTask.from_dict({
        "task_id": "t1",
        "description": "desc",
        "grading_command": "bash verify.sh",
        "python_version": "3.11",
        "extra": {
            "protected_paths": ["test_app.py"],
            "force_host": True,
        },
    })

    assert task.extra["python_version"] == "3.11"
    assert task.extra["protected_paths"] == ["test_app.py"]
    assert task.extra["force_host"] is True


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
    assert "run_tests" in prompt


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


def test_build_prompt_includes_source_context():
    """Initial prompt should include test info and initial test output."""
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
    assert "FAILING TESTS" in prompt
    assert "test_unittest.py" in prompt
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


def test_build_prompt_normal_uses_edit_file():
    """Normal prompt uses edit_file as primary tool and includes grading workflow."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="test-normal",
        description="Fix a bug",
        grading_command="pytest tests/ -x",
    )
    prompt = adapter._build_prompt(task)
    assert "edit_file" in prompt
    workflow = prompt.split("MANDATORY WORKFLOW")[1].split("RULES")[0]
    assert "edit_file" in workflow
    assert "run_tests" in workflow


def test_run_grading_command_uses_host_mode_subprocess(tmp_path: Path):
    """Host-mode grading should execute locally in the sandbox cwd."""
    adapter = AutoCodeAdapter(model="test-model")
    adapter._bench_env = {"PATH": "/tmp/fake-bin"}

    completed = MagicMock(returncode=0, stdout="host ok\n", stderr="")

    with patch("subprocess.run", return_value=completed) as mock_run:
        rc, output = adapter._run_grading_command(
            tmp_path,
            "bash verify.sh",
            timeout=99,
        )

    assert rc == 0
    assert output == "host ok\n"
    mock_run.assert_called_once_with(
        "bash verify.sh",
        shell=True,
        cwd=str(tmp_path),
        env=adapter._bench_env,
        capture_output=True,
        text=True,
        timeout=99,
    )


def test_run_grading_command_uses_docker_when_container_present(tmp_path: Path):
    """Docker-backed grading should still go through docker_exec."""
    adapter = AutoCodeAdapter(model="test-model")
    docker_result = MagicMock(returncode=0, stdout="docker out", stderr="docker err")

    with patch(
        "benchmarks.adapters.autocode_adapter._docker_exec",
        return_value=docker_result,
    ) as mock_docker_exec:
        rc, output = adapter._run_grading_command(
            tmp_path,
            "bash verify.sh",
            container_name="bench-container",
            timeout=77,
        )

    assert rc == 0
    assert output == "docker outdocker err"
    mock_docker_exec.assert_called_once_with(
        "bench-container",
        "bash verify.sh",
        timeout=77,
    )


def test_is_grading_command_invocation_matches_cd_prefixed_commands(
    tmp_path: Path,
):
    """Benchmark grading detection should accept exact verifier calls with cd."""
    adapter = AutoCodeAdapter(model="test-model")
    sandbox = tmp_path / "sandbox"
    work_dir = sandbox / "repo"

    assert adapter._is_grading_command_invocation(
        "bash verify.sh",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )
    assert adapter._is_grading_command_invocation(
        f"cd {sandbox} && bash verify.sh",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )
    assert adapter._is_grading_command_invocation(
        f"cd {work_dir} && bash verify.sh",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )
    assert not adapter._is_grading_command_invocation(
        "python -m unittest test_writer -v",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )


def test_maybe_terminate_grading_command_result_wraps_success(tmp_path: Path):
    """Successful grading through run_command should emit a loop termination."""
    adapter = AutoCodeAdapter(model="test-model")
    sandbox = tmp_path / "sandbox"
    work_dir = sandbox

    output = adapter._maybe_terminate_grading_command_result(
        f"cd {sandbox} && bash verify.sh",
        "PASS: All tests pass\nRESULT: All checks passed",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )

    assert output.startswith("__AUTOCODE_TOOL_TERMINATE__:")
    assert "Benchmark verification passed" in output


def test_maybe_terminate_grading_command_result_ignores_failures(
    tmp_path: Path,
):
    """Failed grading should remain normal tool output, not terminate."""
    adapter = AutoCodeAdapter(model="test-model")
    sandbox = tmp_path / "sandbox"
    work_dir = sandbox

    output = adapter._maybe_terminate_grading_command_result(
        f"cd {sandbox} && bash verify.sh",
        "FAIL: Some tests fail\n[exit code 1]",
        "bash verify.sh",
        sandbox=sandbox,
        work_dir=work_dir,
    )

    assert output == "FAIL: Some tests fail\n[exit code 1]"


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
    """Feedback prompt truncates output tail to 1200 chars."""
    adapter = AutoCodeAdapter(model="test-model")
    long_output = "x" * 5000
    feedback = adapter._build_feedback_prompt(long_output, "pytest")
    # The tail should be at most 1200 chars of the output
    assert "x" * 1200 in feedback
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


def test_build_feedback_prompt_stagnation_different_approach():
    """Feedback prompt should warn about stagnation and suggest different approach."""
    adapter = AutoCodeAdapter(model="test-model")
    feedback = adapter._build_feedback_prompt(
        "FAILED test_bar", "pytest",
        stagnation_count=2,
    )
    assert "DIFFERENT approach" in feedback


def test_build_feedback_prompt_zero_diff_forces_edits():
    """Zero-diff retries should force the agent to actually write code changes."""
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
    assert "ZERO file edits" in feedback
    assert "edit_file" in feedback or "write_file" in feedback


def test_determine_protected_paths_auto_detects_tests_by_default():
    """Fixture tasks default to protecting edited tests unless opted out."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="protect-tests",
        description="desc",
    )

    protected = adapter._determine_protected_paths(
        task,
        ["app.py", "test_app.py", "docs/readme.md"],
        [],
    )

    assert protected == {"test_app.py"}


def test_determine_protected_paths_allows_test_edits_when_flag_set():
    """Some fixtures legitimately require test-file edits."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="allow-tests",
        description="desc",
        extra={"allow_test_file_edits": True},
    )

    protected = adapter._determine_protected_paths(
        task,
        ["test_all.py", "test_formatter.py", "formatter.py"],
        [],
    )

    assert protected == set()


def test_determine_protected_paths_keeps_explicit_paths_even_when_tests_allowed():
    """Explicit protected paths still win when a task allows test edits."""
    adapter = AutoCodeAdapter(model="test-model")
    task = BenchmarkTask(
        task_id="protect-db",
        description="desc",
        extra={
            "allow_test_file_edits": True,
            "protected_paths": ["project/app.db"],
        },
    )

    protected = adapter._determine_protected_paths(
        task,
        ["project/app.db", "project/migrate.py"],
        [],
    )

    assert protected == {"project/app.db"}


# --- A2: Codex adapter grading behavior ---


def test_codex_adapter_uses_grading_command():
    """Codex adapter runs grading_command and uses its exit code for resolved."""
    from benchmarks.adapters.codex_adapter import CodexAdapter

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
    from benchmarks.adapters.codex_adapter import CodexAdapter

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
    from benchmarks.adapters.codex_adapter import CodexAdapter

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
    from benchmarks.adapters.claude_adapter import ClaudeCodeAdapter

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
    from benchmarks.adapters.claude_adapter import ClaudeCodeAdapter

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
    from benchmarks.benchmark_runner import _extract_patch_files

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
    from benchmarks.benchmark_runner import _extract_patch_files

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
    from benchmarks.benchmark_runner import _extract_patch_files

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


def test_parse_assertions_extracts_real_errors():
    """_parse_assertions should extract real assertion/error lines from test output."""
    output = (
        "FAILED test_foo.py::test_bar\n"
        "AssertionError: 1 != 2\n"
        "some normal output\n"
        "TypeError: unsupported operand\n"
    )
    assertions = AutoCodeAdapter._parse_assertions(output)
    assert len(assertions) == 2
    assert any("AssertionError" in a for a in assertions)
    assert any("TypeError" in a for a in assertions)


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
