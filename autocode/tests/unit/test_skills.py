"""Stable TUI v1 Slice 3 — tests for SkillCatalog (Milestone B.2).

Progressive disclosure: frontmatter is always scanned for the catalog; the
body of each skill is loaded only when explicitly requested. Claude-Code-
style discovery order: project `.claude/skills/*/SKILL.md` wins over user
`~/.claude/skills/*/SKILL.md` on name collisions.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from autocode.agent.skills import (
    SkillCatalog,
    SkillCatalogEntry,
    SkillSource,
    skill_catalog_section,
)


def _write_skill(
    root: Path,
    name: str,
    description: str = "Demo skill",
    body: str = "Skill body\n",
    extra_frontmatter: dict[str, str] | None = None,
) -> Path:
    """Create a SKILL.md file and return its path."""
    skill_dir = root / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = [f"name: {name}", f"description: {description}"]
    for k, v in (extra_frontmatter or {}).items():
        fm_lines.append(f"{k}: {v}")
    frontmatter = "\n".join(fm_lines)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
    return path


# ---------- discovery ----------


def test_scan_empty_project_returns_empty(tmp_path: Path) -> None:
    user_dir = tmp_path / "home" / ".claude" / "skills"
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=user_dir)
    assert catalog.scan() == []


def test_scan_picks_up_project_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="Alpha desc")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=tmp_path / "nohome")
    entries = catalog.scan()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.name == "alpha"
    assert entry.description == "Alpha desc"
    assert entry.source == SkillSource.PROJECT


def test_scan_picks_up_user_skills(tmp_path: Path) -> None:
    user_dir = tmp_path / "xdg_home" / ".claude" / "skills"
    user_dir.mkdir(parents=True)
    skill_dir = user_dir / "userskill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: userskill\ndescription: From user\n---\nBody\n",
        encoding="utf-8",
    )

    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=user_dir)
    entries = catalog.scan()
    names = {e.name for e in entries}
    assert "userskill" in names
    entry = next(e for e in entries if e.name == "userskill")
    assert entry.source == SkillSource.USER


def test_scan_project_wins_on_name_conflict(tmp_path: Path) -> None:
    # project-scope
    _write_skill(tmp_path, "shared", description="Project one", body="PROJECT_BODY")
    # user-scope with same name
    user_dir = tmp_path / "home" / ".claude" / "skills"
    user_skill_dir = user_dir / "shared"
    user_skill_dir.mkdir(parents=True)
    (user_skill_dir / "SKILL.md").write_text(
        "---\nname: shared\ndescription: User one\n---\nUSER_BODY",
        encoding="utf-8",
    )

    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=user_dir)
    entries = catalog.scan()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.source == SkillSource.PROJECT
    assert entry.description == "Project one"


def test_scan_parses_allowed_tools(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "restricted",
        extra_frontmatter={"allowed-tools": "[Read, Grep]"},
    )
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entry = catalog.scan()[0]
    assert entry.allowed_tools == ["Read", "Grep"]


def test_scan_parses_disable_model_invocation(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "manual",
        extra_frontmatter={"disable-model-invocation": "true"},
    )
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entry = catalog.scan()[0]
    assert entry.disable_model_invocation is True


def test_scan_skips_malformed_yaml(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "broken"
    skill_dir.mkdir(parents=True)
    # Not valid frontmatter — missing closing fence
    (skill_dir / "SKILL.md").write_text(
        "---\nname: broken\ndescription: no closing fence\nBody\n",
        encoding="utf-8",
    )

    _write_skill(tmp_path, "ok", description="OK skill")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entries = catalog.scan()
    names = {e.name for e in entries}
    # 'broken' must not appear; 'ok' must appear
    assert "broken" not in names
    assert "ok" in names


def test_scan_skips_missing_name_field(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "nameless"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: no name field\n---\nBody\n",
        encoding="utf-8",
    )
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    assert catalog.scan() == []


# ---------- progressive disclosure ----------


def test_load_body_returns_markdown_minus_frontmatter(tmp_path: Path) -> None:
    _write_skill(tmp_path, "body-test", body="HEAD BODY\nmore\n")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    body = catalog.load_body("body-test")
    assert "HEAD BODY" in body
    assert "more" in body
    # Frontmatter must NOT leak into body
    assert "---" not in body
    assert "name:" not in body


def test_load_body_unknown_skill_returns_empty(tmp_path: Path) -> None:
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    assert catalog.load_body("nonexistent") == ""


def test_load_body_caches(tmp_path: Path) -> None:
    p = _write_skill(tmp_path, "cacheable", body="ORIGINAL\n")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    first = catalog.load_body("cacheable")
    # Overwrite disk without refreshing mtime much — cache should hold
    os.utime(p, (time.time(), time.time()))
    # Rewrite with different content but keep mtime stable by utime (above)
    p.write_text(
        "---\nname: cacheable\ndescription: x\n---\nNEW\n", encoding="utf-8"
    )
    # Without a reload_if_changed() call, the cached body should still be
    # the ORIGINAL since the catalog's stored mtime is stale by design.
    cached = catalog.load_body("cacheable")
    assert cached == first


def test_reload_if_changed_detects_mtime(tmp_path: Path) -> None:
    p = _write_skill(tmp_path, "reloadable", body="V1\n")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    catalog.load_body("reloadable")

    time.sleep(0.02)
    p.write_text(
        "---\nname: reloadable\ndescription: x\n---\nV2\n", encoding="utf-8"
    )
    # Force mtime bump
    future = time.time() + 1
    os.utime(p, (future, future))

    assert catalog.reload_if_changed("reloadable") is True
    assert "V2" in catalog.load_body("reloadable")


def test_reload_if_changed_stable_when_unchanged(tmp_path: Path) -> None:
    _write_skill(tmp_path, "stable", body="stable body")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    catalog.load_body("stable")
    assert catalog.reload_if_changed("stable") is False


def test_progressive_disclosure_scan_does_not_read_body(tmp_path: Path) -> None:
    # A sentinel body large enough to matter; scan() should not read it.
    huge_body = "X" * 1_000_000
    _write_skill(tmp_path, "huge", body=huge_body)
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entries = catalog.scan()
    assert len(entries) == 1
    # Scan must record a reasonable frontmatter snapshot, not the body
    # (we can't introspect internal state easily, but we can confirm the
    # public API never exposes the huge body without load_body())
    # If body were read eagerly, the cache would be populated; assert
    # the catalog advertises zero-cached-bodies right after scan.
    assert catalog._cached_body_count() == 0


# ---------- system prompt section ----------


def test_skill_catalog_section_lists_names_descriptions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="Alpha desc")
    _write_skill(tmp_path, "beta", description="Beta desc")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entries = catalog.scan()
    section = skill_catalog_section(entries)
    assert "alpha" in section
    assert "Alpha desc" in section
    assert "beta" in section
    assert "Beta desc" in section


def test_skill_catalog_section_empty_returns_empty_string() -> None:
    assert skill_catalog_section([]) == ""


def test_skill_catalog_section_excludes_disable_model_invocation(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "visible", description="Visible")
    _write_skill(
        tmp_path,
        "hidden",
        description="Hidden",
        extra_frontmatter={"disable-model-invocation": "true"},
    )
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    section = skill_catalog_section(catalog.scan())
    assert "visible" in section
    assert "hidden" not in section


def test_scan_is_idempotent(tmp_path: Path) -> None:
    _write_skill(tmp_path, "repeat", description="repeatable")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    first = catalog.scan()
    second = catalog.scan()
    # Same content — comparing names + descriptions rather than identity
    assert [(e.name, e.description) for e in first] == [
        (e.name, e.description) for e in second
    ]


# ---------- dataclass ----------


def test_skill_catalog_entry_defaults() -> None:
    entry = SkillCatalogEntry(
        name="demo",
        description="desc",
        path=Path("/tmp/SKILL.md"),
        source=SkillSource.PROJECT,
        mtime=0.0,
    )
    assert entry.allowed_tools is None
    assert entry.disable_model_invocation is False


def test_user_skills_dir_none_still_works(tmp_path: Path) -> None:
    # None user_skills_dir → project-only scan
    _write_skill(tmp_path, "only-project", description="P")
    catalog = SkillCatalog(project_root=tmp_path, user_skills_dir=None)
    entries = catalog.scan()
    assert len(entries) == 1
    assert entries[0].source == SkillSource.PROJECT
