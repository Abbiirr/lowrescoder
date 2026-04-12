"""Tests for the transactional apply_patch tool (Phase B Item 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.agent.apply_patch import (
    ApplyPatchResult,
    PatchConflict,
    PatchOperation,
    _handle_apply_patch,
    apply_patch,
)


# --- PatchOperation validation ---


class TestPatchOperationValidation:
    def test_valid_op(self) -> None:
        op = PatchOperation(path="a.txt", old_string="x", new_string="y")
        assert op.path == "a.txt"

    def test_empty_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="path"):
            PatchOperation(path="", old_string="x", new_string="y")

    def test_non_string_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="path"):
            PatchOperation(path=123, old_string="x", new_string="y")  # type: ignore

    def test_non_string_old_rejected(self) -> None:
        with pytest.raises(ValueError, match="old_string"):
            PatchOperation(path="a.txt", old_string=None, new_string="y")  # type: ignore


# --- Empty and simple cases ---


class TestEmptyAndSingle:
    def test_empty_operations_returns_no_op_result(self) -> None:
        result = apply_patch([])
        assert result.applied is False
        assert result.conflicts == []
        assert result.changed_files == []
        assert result.preview == {}

    def test_single_successful_apply(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("hello world\n")
        op = PatchOperation(
            path=str(f), old_string="world", new_string="AutoCode"
        )
        result = apply_patch([op])
        assert result.applied is True
        assert result.conflicts == []
        assert result.changed_files == [str(f)]
        assert f.read_text() == "hello AutoCode\n"

    def test_single_dry_run_does_not_write(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("hello world\n")
        op = PatchOperation(
            path=str(f), old_string="world", new_string="AutoCode"
        )
        result = apply_patch([op], dry_run=True)
        assert result.applied is False  # dry-run never applies
        assert result.conflicts == []
        assert result.changed_files == [str(f)]
        assert str(f) in result.preview
        assert result.preview[str(f)] == "hello AutoCode\n"
        # Disk unchanged
        assert f.read_text() == "hello world\n"


# --- Preflight conflicts ---


class TestPreflightConflicts:
    def test_missing_file_is_conflict(self, tmp_path: Path) -> None:
        op = PatchOperation(
            path=str(tmp_path / "missing.txt"), old_string="x", new_string="y"
        )
        result = apply_patch([op])
        assert result.applied is False
        assert len(result.conflicts) == 1
        assert "does not exist" in result.conflicts[0].reason
        assert result.changed_files == []

    def test_old_string_not_found_is_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("hello world\n")
        op = PatchOperation(
            path=str(f), old_string="NOT_THERE", new_string="y"
        )
        result = apply_patch([op])
        assert result.applied is False
        assert len(result.conflicts) == 1
        assert "old_string not found" in result.conflicts[0].reason
        assert f.read_text() == "hello world\n"  # unchanged

    def test_ambiguous_old_string_is_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("foo bar foo baz foo\n")
        op = PatchOperation(path=str(f), old_string="foo", new_string="X")
        result = apply_patch([op])
        assert result.applied is False
        assert len(result.conflicts) == 1
        assert "appears 3 times" in result.conflicts[0].reason
        assert f.read_text() == "foo bar foo baz foo\n"  # unchanged

    def test_directory_rejected(self, tmp_path: Path) -> None:
        op = PatchOperation(
            path=str(tmp_path), old_string="x", new_string="y"
        )
        result = apply_patch([op])
        assert result.applied is False
        assert "not a regular file" in result.conflicts[0].reason

    def test_duplicate_ops_in_batch_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("hello world\n")
        op1 = PatchOperation(path=str(f), old_string="world", new_string="A")
        op2 = PatchOperation(path=str(f), old_string="world", new_string="B")
        result = apply_patch([op1, op2])
        assert result.applied is False
        # The second op is the duplicate
        assert any("duplicate" in c.reason for c in result.conflicts)


# --- Atomicity ---


class TestAtomicity:
    def test_all_or_nothing_on_mixed_batch(self, tmp_path: Path) -> None:
        """If ANY op in a batch conflicts, NONE of them apply."""
        f1 = tmp_path / "good.txt"
        f1.write_text("this one is fine\n")
        f2 = tmp_path / "bad.txt"
        f2.write_text("this one has no match\n")

        ops = [
            PatchOperation(path=str(f1), old_string="fine", new_string="GREAT"),
            PatchOperation(
                path=str(f2), old_string="NOT_THERE", new_string="X"
            ),
        ]
        result = apply_patch(ops)
        assert result.applied is False
        assert len(result.conflicts) == 1
        assert result.conflicts[0].path == str(f2)
        # f1 must be UNCHANGED even though its op was valid
        assert f1.read_text() == "this one is fine\n"
        assert f2.read_text() == "this one has no match\n"

    def test_all_valid_batch_all_apply(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f1.write_text("aaa AAA aaa\n")
        f2 = tmp_path / "b.txt"
        f2.write_text("bbb BBB bbb\n")
        ops = [
            PatchOperation(path=str(f1), old_string="AAA", new_string="AUTOCODE"),
            PatchOperation(path=str(f2), old_string="BBB", new_string="CODE"),
        ]
        result = apply_patch(ops)
        assert result.applied is True
        assert len(result.changed_files) == 2
        assert f1.read_text() == "aaa AUTOCODE aaa\n"
        assert f2.read_text() == "bbb CODE bbb\n"

    def test_dry_run_with_conflicts_reports_all(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("hello\n")
        ops = [
            PatchOperation(path=str(f), old_string="NOT_THERE", new_string="X"),
            PatchOperation(
                path=str(tmp_path / "missing.txt"),
                old_string="x",
                new_string="y",
            ),
        ]
        result = apply_patch(ops, dry_run=True)
        assert result.applied is False
        assert len(result.conflicts) == 2
        # Neither file should change
        assert f.read_text() == "hello\n"


# --- Multi-op same file (sequential composition) ---


class TestMultiOpSameFile:
    def test_two_ops_same_file_both_apply(self, tmp_path: Path) -> None:
        """Multiple ops on the same file compose sequentially on the in-memory buffer."""
        f = tmp_path / "a.txt"
        f.write_text("alpha beta gamma\n")
        ops = [
            PatchOperation(path=str(f), old_string="alpha", new_string="A"),
            PatchOperation(path=str(f), old_string="gamma", new_string="G"),
        ]
        result = apply_patch(ops)
        assert result.applied is True
        assert f.read_text() == "A beta G\n"
        # changed_files should list the file ONCE even with multiple ops
        assert result.changed_files == [str(f)]

    def test_second_op_depends_on_first(self, tmp_path: Path) -> None:
        """The second op can match text introduced by the first op."""
        f = tmp_path / "a.txt"
        f.write_text("one\n")
        ops = [
            PatchOperation(path=str(f), old_string="one", new_string="TWO three"),
            PatchOperation(path=str(f), old_string="three", new_string="THREE"),
        ]
        result = apply_patch(ops)
        assert result.applied is True
        assert f.read_text() == "TWO THREE\n"


# --- Handler entry point ---


class TestHandler:
    def test_handler_empty_ops(self) -> None:
        result = _handle_apply_patch(operations=[])
        assert "required" in result

    def test_handler_none_ops(self) -> None:
        result = _handle_apply_patch(operations=None)
        assert "required" in result

    def test_handler_invalid_op_shape(self) -> None:
        result = _handle_apply_patch(operations=["not a dict"])
        assert "invalid operation" in result

    def test_handler_invalid_op_empty_path(self) -> None:
        result = _handle_apply_patch(
            operations=[{"path": "", "old_string": "x", "new_string": "y"}]
        )
        assert "path" in result

    def test_handler_dry_run_via_handler(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("hello world\n")
        result = _handle_apply_patch(
            operations=[
                {"path": str(f), "old_string": "world", "new_string": "Y"}
            ],
            dry_run=True,
        )
        assert "dry-run" in result.lower()
        assert f.read_text() == "hello world\n"

    def test_handler_successful_apply(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("hello world\n")
        result = _handle_apply_patch(
            operations=[
                {"path": str(f), "old_string": "world", "new_string": "Y"}
            ]
        )
        assert "applied 1 file" in result
        assert f.read_text() == "hello Y\n"


# --- Registry wiring ---


class TestApplyPatchRegistration:
    def test_apply_patch_in_core_tool_names(self) -> None:
        from autocode.agent.tools import CORE_TOOL_NAMES

        assert "apply_patch" in CORE_TOOL_NAMES

    def test_apply_patch_registered_in_default_registry(self) -> None:
        from autocode.agent.tools import create_default_registry

        registry = create_default_registry()
        tool = registry.get("apply_patch")
        assert tool is not None
        assert tool.name == "apply_patch"
        assert tool.requires_approval is True
        assert tool.mutates_fs is True
        assert "operations" in tool.parameters["properties"]
        assert "dry_run" in tool.parameters["properties"]


# --- to_text() formatter ---


class TestToText:
    def test_conflict_text(self) -> None:
        r = ApplyPatchResult(
            applied=False,
            conflicts=[PatchConflict(path="a.txt", reason="missing")],
        )
        text = r.to_text()
        assert "NO files written" in text
        assert "a.txt" in text
        assert "missing" in text

    def test_apply_text(self) -> None:
        r = ApplyPatchResult(
            applied=True,
            changed_files=["a.txt", "b.txt"],
        )
        text = r.to_text()
        assert "applied 2 file" in text
        assert "a.txt" in text
        assert "b.txt" in text

    def test_dry_run_text(self) -> None:
        r = ApplyPatchResult(
            applied=False,
            changed_files=["a.txt"],
            preview={"a.txt": "new"},
        )
        text = r.to_text()
        assert "dry-run" in text
        assert "a.txt" in text
