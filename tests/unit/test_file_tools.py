"""Tests for file tools utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from hybridcoder.utils.file_tools import list_files, read_file, write_file


class TestReadFile:
    """Test read_file function."""

    def test_read_whole_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        content = read_file(str(f))
        assert "line1" in content
        assert "line3" in content

    def test_read_line_range(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        content = read_file(str(f), start_line=2, end_line=3)
        assert "line2" in content
        assert "line3" in content
        assert "line1" not in content

    def test_read_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            read_file("/nonexistent/path.txt")

    def test_path_validation_blocks_traversal(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("secret")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(secret), project_root=str(tmp_path / "sub"))


class TestWriteFile:
    """Test write_file function."""

    def test_write_new_file(self, tmp_path: Path) -> None:
        path = write_file(tmp_path / "new.txt", "hello")
        assert path.read_text() == "hello"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = write_file(tmp_path / "a" / "b" / "c.txt", "deep")
        assert path.read_text() == "deep"

    def test_write_path_validation(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        with pytest.raises(ValueError, match="escapes project root"):
            write_file(tmp_path / "outside.txt", "bad", project_root=str(tmp_path / "sub"))


class TestListFiles:
    """Test list_files function."""

    def test_list_all_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        files = list_files(str(tmp_path))
        assert len(files) == 3

    def test_list_with_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        files = list_files(str(tmp_path), pattern="*.py")
        assert len(files) == 2
        assert all(f.endswith(".py") for f in files)

    def test_list_nonexistent_dir(self) -> None:
        files = list_files("/nonexistent/dir")
        assert files == []
