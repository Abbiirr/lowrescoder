"""Tests for the permission-mode mapping (clean-room copy of puku-cli's enum).

puku-cli exposes ``--permission-mode acceptEdits|bypassPermissions|default|
dontAsk|plan|auto``. AutoCode's headless ``exec`` only had a boolean
``--auto-approve``. This maps puku's enum onto AutoCode's existing ApprovalMode —
clean-room (no vendored code), pure logic, deterministically testable.
"""

from __future__ import annotations

import pytest

from autocode.agent.approval import ApprovalMode
from autocode.agent.permission_mode import (
    PUKU_PERMISSION_MODES,
    resolution_for,
    resolve_permission_mode,
)


def test_bypass_permissions_approves_everything() -> None:
    res = resolve_permission_mode("bypassPermissions")
    assert res.auto_approve is True
    assert res.read_only is False
    assert res.approval_mode == ApprovalMode.AUTONOMOUS


def test_plan_mode_is_read_only() -> None:
    res = resolve_permission_mode("plan")
    assert res.read_only is True
    assert res.auto_approve is False
    assert res.approval_mode == ApprovalMode.READ_ONLY


def test_default_mode_does_not_auto_approve() -> None:
    res = resolve_permission_mode("default")
    assert res.auto_approve is False
    assert res.read_only is False
    assert res.approval_mode == ApprovalMode.SUGGEST


def test_accept_edits_and_auto_approve_writes() -> None:
    for mode in ("acceptEdits", "auto", "dontAsk"):
        res = resolve_permission_mode(mode)
        assert res.auto_approve is True, mode
        assert res.read_only is False, mode


def test_mode_matching_is_case_and_separator_insensitive() -> None:
    assert resolve_permission_mode("bypass-permissions").auto_approve is True
    assert resolve_permission_mode("BYPASSPERMISSIONS").auto_approve is True
    assert resolve_permission_mode("accept_edits").auto_approve is True


def test_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="permission mode"):
        resolve_permission_mode("nonsense")


def test_all_advertised_modes_resolve() -> None:
    for mode in PUKU_PERMISSION_MODES:
        res = resolve_permission_mode(mode)
        assert res.approval_mode in set(ApprovalMode)


def test_resolution_for_prefers_explicit_mode_over_legacy_bool() -> None:
    # Explicit --permission-mode wins over the legacy --auto-approve boolean.
    res = resolution_for(permission_mode="plan", auto_approve=True)
    assert res.read_only is True
    assert res.auto_approve is False


def test_resolution_for_falls_back_to_legacy_bool() -> None:
    assert resolution_for(permission_mode=None, auto_approve=True).auto_approve is True
    assert resolution_for(permission_mode=None, auto_approve=False).auto_approve is False
