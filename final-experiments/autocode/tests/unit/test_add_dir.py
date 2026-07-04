"""Tests for ``--add-dir`` — additional tool-access directories (puku-cli).

puku-cli's ``--add-dir <directories...>`` lets tools access directories beyond the
project root. AutoCode confines file tools to the project root via
``validate_path``; this extends that guard with an explicit allow-list of extra
roots. Default (empty) preserves the exact prior confinement — the security
sandbox is unchanged unless the operator opts in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.utils.file_tools import validate_path


def test_path_inside_project_root_is_allowed(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    assert validate_path(proj / "a.py", proj) == (proj / "a.py").resolve()


def test_path_outside_root_still_rejected_by_default(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    other = tmp_path / "other"
    proj.mkdir()
    other.mkdir()
    with pytest.raises(ValueError, match="escapes project root"):
        validate_path(other / "a.py", proj)


def test_extra_root_allows_access(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    extra = tmp_path / "extra"
    proj.mkdir()
    extra.mkdir()
    # Without extra_roots -> rejected; with it -> allowed.
    with pytest.raises(ValueError):
        validate_path(extra / "lib.py", proj)
    resolved = validate_path(extra / "lib.py", proj, extra_roots=[extra])
    assert resolved == (extra / "lib.py").resolve()


def test_path_outside_all_allowed_roots_still_rejected(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    extra = tmp_path / "extra"
    outside = tmp_path / "outside"
    for d in (proj, extra, outside):
        d.mkdir()
    with pytest.raises(ValueError, match="escapes project root"):
        validate_path(outside / "x.py", proj, extra_roots=[extra])


def test_extra_root_itself_is_allowed(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    extra = tmp_path / "extra"
    proj.mkdir()
    extra.mkdir()
    assert validate_path(extra, proj, extra_roots=[extra]) == extra.resolve()


def test_empty_extra_roots_is_identical_to_default(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    assert validate_path(proj / "a.py", proj, extra_roots=[]) == validate_path(proj / "a.py", proj)


# --- Registry-level integration: the read_file tool honors extra_roots --------

from autocode.agent.tools import create_default_registry  # noqa: E402


def _read_via_registry(proj: Path, target: Path, extra_roots: list[str]) -> str:
    reg = create_default_registry(project_root=str(proj), extra_roots=extra_roots)
    tool = reg.get("read_file")
    assert tool is not None
    try:
        return str(tool.handler(path=str(target)))
    except ValueError as exc:  # confinement may raise rather than return
        return f"Error: {exc}"


def test_read_tool_blocked_outside_root_without_add_dir(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    extra = tmp_path / "extra"
    proj.mkdir()
    extra.mkdir()
    (extra / "lib.txt").write_text("EXTRADATA")
    out = _read_via_registry(proj, extra / "lib.txt", extra_roots=[])
    assert "EXTRADATA" not in out  # access denied


def test_read_tool_allowed_with_add_dir(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    extra = tmp_path / "extra"
    proj.mkdir()
    extra.mkdir()
    (extra / "lib.txt").write_text("EXTRADATA")
    out = _read_via_registry(proj, extra / "lib.txt", extra_roots=[str(extra)])
    assert "EXTRADATA" in out  # access granted by --add-dir
