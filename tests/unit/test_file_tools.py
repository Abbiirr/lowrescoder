"""Tests for file tools utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.utils.file_tools import list_files, read_file, write_file


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

    def test_path_validation_blocks_prefix_bypass(self, tmp_path: Path) -> None:
        """Regression: /repo-evil should not pass validation for /repo."""
        repo = tmp_path / "repo"
        repo.mkdir()
        repo_evil = tmp_path / "repo-evil"
        repo_evil.mkdir()
        evil_file = repo_evil / "steal.txt"
        evil_file.write_text("stolen")
        with pytest.raises(ValueError, match="escapes project root"):
            read_file(str(evil_file), project_root=str(repo))

    def test_relative_path_resolves_to_project_root(self, tmp_path: Path) -> None:
        """Relative paths should resolve against project_root, not CWD."""
        (tmp_path / "src").mkdir()
        target = tmp_path / "src" / "hello.txt"
        target.write_text("content")
        content = read_file("src/hello.txt", project_root=str(tmp_path))
        assert content == "content"

    def test_container_style_work_path_maps_to_project_root(self, tmp_path: Path) -> None:
        """Absolute /work/<repo>/... paths should map into project_root."""
        repo = tmp_path / "django"
        (repo / "django" / "db").mkdir(parents=True)
        target = repo / "django" / "db" / "models.py"
        target.write_text("value = 1")
        content = read_file("/work/django/django/db/models.py", project_root=str(repo))
        assert content == "value = 1"


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

    def test_write_relative_path_resolves_to_project_root(self, tmp_path: Path) -> None:
        """Relative paths should resolve against project_root."""
        path = write_file("output.txt", "hello", project_root=str(tmp_path))
        assert path.read_text() == "hello"
        assert path.parent == tmp_path

    def test_write_container_style_work_path_maps_to_project_root(self, tmp_path: Path) -> None:
        """write_file should accept /work/<repo>/... paths in benchmark traces."""
        repo = tmp_path / "django"
        repo.mkdir()
        path = write_file(
            "/work/django/django/db/models.py",
            "x = 1",
            project_root=str(repo),
        )
        assert path.read_text() == "x = 1"
        assert path == (repo / "django" / "db" / "models.py")


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
