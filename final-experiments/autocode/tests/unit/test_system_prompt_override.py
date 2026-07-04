"""Tests for system-prompt override/append (clean-room copy of puku-cli flags).

puku-cli exposes ``--system-prompt`` (replace the default) and
``--append-system-prompt`` (append to the default). The pure ``finalize_system_prompt``
helper applies them on top of AutoCode's assembled prompt; both default to no-op so
existing behavior is byte-identical.
"""

from __future__ import annotations

from autocode.agent.prompts import assemble_system_prompt, finalize_system_prompt


def test_no_overrides_is_identical_to_assemble() -> None:
    base = assemble_system_prompt(stable="STABLE", dynamic="DYNAMIC")
    out = finalize_system_prompt(stable="STABLE", dynamic="DYNAMIC")
    assert out == base


def test_override_replaces_stable_region() -> None:
    out = finalize_system_prompt(stable="DEFAULT PERSONA", dynamic="DYN", override="CUSTOM")
    assert "DEFAULT PERSONA" not in out
    assert out.startswith("CUSTOM")
    # Dynamic runtime state is preserved (approval mode, tasks, etc.).
    assert "DYN" in out


def test_append_adds_after_assembled_prompt() -> None:
    out = finalize_system_prompt(stable="STABLE", dynamic="DYN", append="EXTRA RULES")
    assert out.endswith("EXTRA RULES")
    assert "STABLE" in out
    assert "DYN" in out


def test_override_and_append_compose() -> None:
    out = finalize_system_prompt(
        stable="STABLE", dynamic="DYN", override="CUSTOM", append="EXTRA"
    )
    assert out.startswith("CUSTOM")
    assert out.endswith("EXTRA")
    assert "STABLE" not in out


def test_empty_append_is_noop() -> None:
    base = assemble_system_prompt(stable="S", dynamic="D")
    assert finalize_system_prompt(stable="S", dynamic="D", append="") == base
    assert finalize_system_prompt(stable="S", dynamic="D", append=None) == base


# --- AgentLoop-level wiring -------------------------------------------------

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from autocode.agent.approval import ApprovalManager, ApprovalMode  # noqa: E402
from autocode.agent.loop import AgentLoop  # noqa: E402
from autocode.agent.tools import ToolRegistry  # noqa: E402
from autocode.session.store import SessionStore  # noqa: E402


@pytest.fixture()
def _loop_store(tmp_path: Path):
    s = SessionStore(tmp_path / "sp.db")
    yield s
    s.close()


def _make_loop(store: SessionStore, tmp_path: Path, **kwargs: object) -> AgentLoop:
    sid = store.create_session(title="t", model="m", provider="mock", project_dir=str(tmp_path))
    return AgentLoop(
        None,  # provider unused by _build_system_prompt
        ToolRegistry(),
        ApprovalManager(ApprovalMode.SUGGEST),
        store,
        sid,
        **kwargs,
    )


def test_loop_default_system_prompt_is_unchanged(_loop_store: SessionStore, tmp_path: Path) -> None:
    loop = _make_loop(_loop_store, tmp_path)
    prompt = loop._build_system_prompt()
    assert not prompt.startswith("CUSTOM PERSONA XYZ")
    assert prompt  # builds successfully


def test_loop_system_prompt_override(_loop_store: SessionStore, tmp_path: Path) -> None:
    loop = _make_loop(_loop_store, tmp_path, system_prompt_override="CUSTOM PERSONA XYZ")
    assert loop._build_system_prompt().startswith("CUSTOM PERSONA XYZ")


def test_loop_system_prompt_append(_loop_store: SessionStore, tmp_path: Path) -> None:
    loop = _make_loop(_loop_store, tmp_path, system_prompt_append="EXTRA RULE ABC")
    prompt = loop._build_system_prompt()
    assert prompt.rstrip().endswith("EXTRA RULE ABC")
