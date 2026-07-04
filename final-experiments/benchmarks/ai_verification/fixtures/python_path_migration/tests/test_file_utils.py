import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from file_utils import ensure_dir, list_text_files, read_if_exists


def test_list_text_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    (tmp_path / "c.md").write_text("nope")
    assert list_text_files(str(tmp_path)) == ["a.txt", "b.txt"]


def test_list_text_files_empty(tmp_path):
    assert list_text_files(str(tmp_path)) == []


def test_read_if_exists_present(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("content")
    assert read_if_exists(str(p)) == "content"


def test_read_if_exists_missing(tmp_path):
    assert read_if_exists(str(tmp_path / "missing.txt")) is None


def test_ensure_dir(tmp_path):
    new_dir = str(tmp_path / "sub" / "deep")
    result = ensure_dir(new_dir)
    assert result == new_dir
    assert os.path.isdir(new_dir)
