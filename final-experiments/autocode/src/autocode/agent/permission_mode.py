"""Permission-mode mapping — a clean-room copy of puku-cli's ``--permission-mode``.

puku-cli exposes a session permission *enum*
(``acceptEdits | bypassPermissions | default | dontAsk | plan | auto``). AutoCode
historically only had a boolean ``--auto-approve`` on headless ``exec``. This
module maps the enum onto AutoCode's existing :class:`ApprovalMode`, so the
headless runner gains the same expressive surface without vendoring any puku-cli
code. The mapping is the entire feature and is pure/deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

from autocode.agent.approval import ApprovalMode

# The advertised puku-cli permission modes (in puku's documented order).
PUKU_PERMISSION_MODES: tuple[str, ...] = (
    "acceptEdits",
    "bypassPermissions",
    "default",
    "dontAsk",
    "plan",
    "auto",
)


@dataclass(frozen=True)
class PermissionResolution:
    """How a requested permission mode maps onto AutoCode's runtime behavior."""

    mode: str
    approval_mode: ApprovalMode
    auto_approve: bool
    read_only: bool

    @property
    def label(self) -> str:
        return f"{self.mode} -> {self.approval_mode.value}"


# key (normalized) -> (ApprovalMode, auto_approve, read_only)
_MAP: dict[str, tuple[ApprovalMode, bool, bool]] = {
    "bypasspermissions": (ApprovalMode.AUTONOMOUS, True, False),
    "dontask": (ApprovalMode.AUTONOMOUS, True, False),
    "auto": (ApprovalMode.AUTO, True, False),
    "acceptedits": (ApprovalMode.AUTO, True, False),
    "default": (ApprovalMode.SUGGEST, False, False),
    "plan": (ApprovalMode.READ_ONLY, False, True),
}


def _normalize(mode: str) -> str:
    return mode.strip().replace("-", "").replace("_", "").lower()


def resolve_permission_mode(mode: str) -> PermissionResolution:
    """Resolve a puku-style permission mode to AutoCode behavior.

    Matching is case- and separator-insensitive (``bypass-permissions`` ==
    ``bypassPermissions`` == ``BYPASSPERMISSIONS``).
    """
    key = _normalize(mode)
    entry = _MAP.get(key)
    if entry is None:
        valid = ", ".join(PUKU_PERMISSION_MODES)
        raise ValueError(f"unknown permission mode '{mode}' (valid: {valid})")
    approval_mode, auto_approve, read_only = entry
    return PermissionResolution(
        mode=mode,
        approval_mode=approval_mode,
        auto_approve=auto_approve,
        read_only=read_only,
    )


def resolution_for(
    *,
    permission_mode: str | None,
    auto_approve: bool,
) -> PermissionResolution:
    """Resolve the effective permission for a run.

    An explicit ``permission_mode`` wins; otherwise the legacy ``auto_approve``
    boolean maps to ``auto`` (True) or ``default`` (False) — the exact
    ApprovalMode pairing (AUTO / SUGGEST) the headless runner used before this
    feature, so existing callers keep their precise behavior.
    """
    if permission_mode:
        return resolve_permission_mode(permission_mode)
    return resolve_permission_mode("auto" if auto_approve else "default")
