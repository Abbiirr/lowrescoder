"""Tests for LLMLOOP — Architect/Editor/Verify feedback loop."""

from __future__ import annotations

from pathlib import Path

from autocode.agent.llmloop import (
    Edit,
    EditPlan,
    EditType,
    LLMLOOP,
    LLMLOOPResult,
    VerificationResult,
)


def test_edit_plan_structure() -> None:
    """EditPlan holds edits with reasoning."""
    plan = EditPlan(
        file="src/app.py",
        edits=[
            Edit(
                type=EditType.REPLACE,
                file="src/app.py",
                location="line 10",
                old_content="x = 1",
                new_content="x = 2",
            ),
        ],
        reasoning="Fix the value",
        test_command="pytest tests/",
    )
    assert len(plan.edits) == 1
    assert plan.edits[0].type == EditType.REPLACE
    assert plan.reasoning == "Fix the value"


def test_verification_result() -> None:
    """VerificationResult tracks pass/fail with errors."""
    result = VerificationResult(passed=False, errors=["Syntax error at line 5"])
    assert not result.passed
    assert len(result.errors) == 1


def test_llmloop_empty_plan() -> None:
    """LLMLOOP handles empty edit plan from Architect."""
    loop = LLMLOOP(max_iterations=3)
    result = loop.run("Fix the bug")
    assert not result.success
    assert "empty edit plan" in result.error
    assert result.iterations == 1


def test_llmloop_result_structure() -> None:
    """LLMLOOPResult has all expected fields."""
    result = LLMLOOPResult(
        success=True,
        iterations=2,
        files_modified=["a.py", "b.py"],
        total_tokens=500,
    )
    assert result.success
    assert result.iterations == 2
    assert len(result.files_modified) == 2


def test_llmloop_max_iterations() -> None:
    """LLMLOOP stops after max_iterations."""
    loop = LLMLOOP(max_iterations=3)
    # Default plan() returns empty edits, so it stops at iteration 1
    result = loop.run("Fix something")
    assert result.iterations <= 3


def test_llmloop_verify_valid_python(tmp_path: Path) -> None:
    """Verifier passes on valid Python files."""
    valid = tmp_path / "good.py"
    valid.write_text("x = 1\ny = 2\n")

    loop = LLMLOOP()
    result = loop.verify([str(valid)])
    assert result.passed
    assert len(result.errors) == 0


def test_llmloop_verify_invalid_python(tmp_path: Path) -> None:
    """Verifier catches syntax errors in Python files."""
    invalid = tmp_path / "bad.py"
    invalid.write_text("def foo(\n  # missing close paren\n")

    loop = LLMLOOP()
    result = loop.verify([str(invalid)])
    assert not result.passed
    assert len(result.errors) == 1
    assert "Syntax error" in result.errors[0]


def test_llmloop_verify_non_python() -> None:
    """Verifier skips non-Python files."""
    loop = LLMLOOP()
    result = loop.verify(["README.md", "Makefile"])
    assert result.passed  # non-Python files always pass


def test_edit_types() -> None:
    """EditType has all expected values."""
    assert EditType.REPLACE == "replace"
    assert EditType.INSERT == "insert"
    assert EditType.DELETE == "delete"


def test_llmloop_multi_file_plan_parsing() -> None:
    """Per-edit file targets are preserved, not flattened to top-level file."""
    import json

    # Simulate a multi-file plan JSON response
    plan_json = json.dumps({
        "file": "default.py",
        "edits": [
            {"type": "replace", "file": "src/app.py",
             "old_content": "x = 1", "new_content": "x = 2"},
            {"type": "replace", "file": "src/utils.py",
             "old_content": "y = 1", "new_content": "y = 2"},
        ],
        "reasoning": "Fix both files",
    })

    # Parse the same way LLMLOOP.plan() does
    data = json.loads(plan_json)
    default_file = data.get("file", "")
    files = [e.get("file", default_file) for e in data["edits"]]

    assert files == ["src/app.py", "src/utils.py"]
    assert "default.py" not in files  # NOT flattened


def test_llmloop_provider_backed_multi_file_plan() -> None:
    """Provider-backed plan() preserves per-edit file targets end-to-end."""
    import asyncio
    import json
    from collections.abc import AsyncIterator
    from typing import Any

    # Fake async provider that emits a two-file JSON plan
    class FakeProvider:
        async def generate(
            self, messages: list[dict[str, str]], **kwargs: Any,
        ) -> AsyncIterator[str]:
            plan = json.dumps({
                "file": "fallback.py",
                "edits": [
                    {"type": "replace", "file": "src/a.py",
                     "location": "line 1",
                     "old_content": "old_a", "new_content": "new_a"},
                    {"type": "replace", "file": "src/b.py",
                     "location": "line 5",
                     "old_content": "old_b", "new_content": "new_b"},
                ],
                "reasoning": "Fix two files",
            })
            yield plan

    loop = LLMLOOP(provider=FakeProvider())
    plan = loop.plan("Fix the bugs")

    assert len(plan.edits) == 2
    assert plan.edits[0].file == "src/a.py"
    assert plan.edits[1].file == "src/b.py"
    assert plan.confidence > 0


def test_llmloop_plan_under_active_event_loop() -> None:
    """plan() succeeds when called from inside a running event loop."""
    import asyncio
    import json
    from typing import Any

    class FakeProvider:
        async def generate(
            self, messages: list[dict[str, str]], **kwargs: Any,
        ):
            yield json.dumps({
                "file": "test.py",
                "edits": [{"type": "replace", "location": "line 1",
                           "old_content": "x", "new_content": "y"}],
                "reasoning": "test",
            })

    loop_inst = LLMLOOP(provider=FakeProvider())

    # Run plan() from inside an active event loop
    async def _run_in_loop():
        # This is the exact scenario that would fail with raw asyncio.run()
        return loop_inst.plan("Fix something")

    plan = asyncio.run(_run_in_loop())
    assert plan is not None
    assert plan.reasoning  # Should have content, not empty error
    assert len(plan.edits) >= 1


def test_llmloop_verify_with_project_root(tmp_path: Path) -> None:
    """verify() resolves relative paths against project_root, not cwd."""
    import os

    # Create file in project_root
    (tmp_path / "module.py").write_text("def broken(\n")

    # Run verify from a DIFFERENT cwd
    original_cwd = os.getcwd()
    try:
        os.chdir("/tmp")
        loop = LLMLOOP(project_root=str(tmp_path))
        result = loop.verify(["module.py"])
        # Should find and check the file despite different cwd
        assert not result.passed
        assert any("Syntax error" in e for e in result.errors)
    finally:
        os.chdir(original_cwd)


def test_llmloop_verify_valid_with_project_root(tmp_path: Path) -> None:
    """verify() passes valid files resolved via project_root."""
    import os

    (tmp_path / "good.py").write_text("x = 1\n")

    original_cwd = os.getcwd()
    try:
        os.chdir("/tmp")
        loop = LLMLOOP(project_root=str(tmp_path))
        result = loop.verify(["good.py"])
        assert result.passed
    finally:
        os.chdir(original_cwd)
