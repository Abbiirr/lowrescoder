"""Stable TUI v1 Slice 2 — tests for the upgraded RulesLoader.

Verifies Milestone B.1 migration contract: CLAUDE.local.md precedence, bounded
@imports (with circular-import guard + external-approval), directory walk,
HTML block-comment stripping, provenance tracking, and the backward-compatible
legacy `load()` API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.layer2.rules import LoadedSource, Provenance, RulesLoader, RulesResult


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_loads_claude_md(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "# Project\nhello from CLAUDE.md\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert "hello from CLAUDE.md" in result.text
    assert any(s.path == tmp_path / "CLAUDE.md" for s in result.sources)


def test_claude_local_md_loaded_after_claude_md(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "base rule\n")
    _write(tmp_path / "CLAUDE.local.md", "local override\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    base_idx = result.text.index("base rule")
    local_idx = result.text.index("local override")
    assert local_idx > base_idx, "CLAUDE.local.md must appear after CLAUDE.md"


def test_claude_local_md_respects_include_local_false(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "base\n")
    _write(tmp_path / "CLAUDE.local.md", "SECRET\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path, include_local=False)
    assert "SECRET" not in result.text


def test_directory_walk_picks_up_parent_claude_md(tmp_path: Path) -> None:
    parent = tmp_path
    child = tmp_path / "sub" / "deeper"
    _write(parent / "CLAUDE.md", "parent rule\n")
    _write(child / "CLAUDE.md", "child rule\n")
    loader = RulesLoader()
    result = loader.load_detailed(child, walk_up_to=parent)
    assert "parent rule" in result.text
    assert "child rule" in result.text
    # Parent content should come BEFORE child (broader → specific).
    assert result.text.index("parent rule") < result.text.index("child rule")


def test_at_import_expands_relative_path(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "before\n@docs/style.md\nafter\n")
    _write(tmp_path / "docs" / "style.md", "STYLE_BODY\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert "STYLE_BODY" in result.text


def test_at_import_external_without_approver_marked_skipped(tmp_path: Path) -> None:
    external = tmp_path / "external_rules.md"
    _write(external, "EXTERNAL_RULES\n")
    _write(tmp_path / "project" / "CLAUDE.md", f"@{external}\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path / "project")
    assert "EXTERNAL_RULES" not in result.text
    assert any(str(external) in entry for entry in result.skipped_imports)


def test_at_import_external_with_approver_loaded(tmp_path: Path) -> None:
    external = tmp_path / "external_rules.md"
    _write(external, "EXTERNAL_APPROVED\n")
    _write(tmp_path / "project" / "CLAUDE.md", f"@{external}\n")
    loader = RulesLoader()
    result = loader.load_detailed(
        tmp_path / "project",
        external_import_approver=lambda p: True,
    )
    assert "EXTERNAL_APPROVED" in result.text
    assert not result.skipped_imports


def test_at_import_bounded_depth(tmp_path: Path) -> None:
    # chain CLAUDE.md -> a.md -> b.md -> c.md -> d.md -> e.md -> f.md
    _write(tmp_path / "CLAUDE.md", "@a.md\n")
    for cur, nxt in zip("abcdef", "bcdefg"):
        _write(tmp_path / f"{cur}.md", f"START_{cur}\n@{nxt}.md\nEND_{cur}\n")
    _write(tmp_path / "g.md", "DEEPEST\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path, max_import_depth=3)
    assert "START_a" in result.text  # depth 1
    assert "START_b" in result.text  # depth 2
    assert "START_c" in result.text  # depth 3
    # depth 4 (d.md) must NOT be expanded
    assert "START_d" not in result.text
    # And the depth guard should be recorded
    assert any("depth" in s.lower() for s in result.skipped_imports)


def test_at_import_circular_detected(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "@a.md\n")
    _write(tmp_path / "a.md", "A_BODY\n@b.md\n")
    _write(tmp_path / "b.md", "B_BODY\n@a.md\n")  # cycle back to a.md
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    # Both a.md and b.md should appear once
    assert result.text.count("A_BODY") == 1
    assert result.text.count("B_BODY") == 1
    # Cycle should be recorded
    assert result.circular_detected, "expected circular import detection"


def test_html_block_comment_stripped(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "keep\n<!-- secret -->\nafter\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert "secret" not in result.text
    assert "keep" in result.text
    assert "after" in result.text


def test_html_block_comment_preserved_when_strip_disabled(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "keep\n<!-- secret -->\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path, strip_html_comments=False)
    assert "secret" in result.text


def test_agents_md_still_loaded(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "agents body\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert "agents body" in result.text


def test_cursorrules_still_loaded(tmp_path: Path) -> None:
    _write(tmp_path / ".cursorrules", "cursor body\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert "cursor body" in result.text


def test_provenance_tracked_per_source(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "main\n@extra.md\n")
    _write(tmp_path / "extra.md", "extra\n")
    _write(tmp_path / "AGENTS.md", "agents\n")
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    kinds = [s.kind for s in result.sources]
    assert Provenance.CLAUDE_MD in kinds
    assert Provenance.IMPORT in kinds
    assert Provenance.AGENTS_MD in kinds


def test_truncation_respects_max_file_bytes(tmp_path: Path) -> None:
    big = "X" * 100_000
    _write(tmp_path / "CLAUDE.md", big)
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path, max_file_bytes=1_000)
    assert "truncated" in result.text.lower()
    assert len(result.text) < 10_000


def test_legacy_load_returns_str(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "hello\n")
    loader = RulesLoader()
    text = loader.load(tmp_path)
    assert isinstance(text, str)
    assert "hello" in text


def test_loaded_source_dataclass_fields() -> None:
    src = LoadedSource(path=Path("/tmp/x.md"), kind=Provenance.CLAUDE_MD, length=123)
    assert src.length == 123
    assert src.kind == Provenance.CLAUDE_MD


def test_rules_result_dataclass_defaults() -> None:
    result = RulesResult(text="x")
    assert result.sources == []
    assert result.skipped_imports == []
    assert result.circular_detected == []


def test_empty_project_returns_empty_text(tmp_path: Path) -> None:
    loader = RulesLoader()
    result = loader.load_detailed(tmp_path)
    assert result.text == ""
    assert result.sources == []


@pytest.mark.parametrize(
    ("file_name", "body"),
    [
        ("CLAUDE.md", "CLAUDE_BODY"),
        ("CLAUDE.local.md", "LOCAL_BODY"),
        ("AGENTS.md", "AGENTS_BODY"),
        (".cursorrules", "CURSOR_BODY"),
    ],
)
def test_loaders_include_each_supported_filename(
    tmp_path: Path, file_name: str, body: str
) -> None:
    _write(tmp_path / file_name, body + "\n")
    loader = RulesLoader()
    text = loader.load(tmp_path)
    assert body in text
