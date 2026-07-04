import pytest
from src.report_gen import (
    ensure_report_dir,
    write_html_report,
    read_report,
    list_reports,
    delete_report,
)


def test_ensure_report_dir_creates(tmp_path):
    path = ensure_report_dir(str(tmp_path), "q1")
    import os
    assert os.path.isdir(path)


def test_write_and_read_report(tmp_path):
    rdir = ensure_report_dir(str(tmp_path), "sales")
    out = write_html_report(rdir, "Sales", [["A", "B"], ["1", "2"]])
    html = read_report(out)
    assert "<title>Sales</title>" in html
    assert "<td>A</td>" in html


def test_read_missing_report(tmp_path):
    assert read_report(str(tmp_path / "missing.html")) == ""


def test_list_reports(tmp_path):
    ensure_report_dir(str(tmp_path), "alpha")
    ensure_report_dir(str(tmp_path), "beta")
    names = list_reports(str(tmp_path))
    assert names == ["alpha", "beta"]


def test_delete_report(tmp_path):
    rdir = ensure_report_dir(str(tmp_path), "temp")
    write_html_report(rdir, "Temp", [])
    assert delete_report(rdir) is True
    assert delete_report(rdir) is False
