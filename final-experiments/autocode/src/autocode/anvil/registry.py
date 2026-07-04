"""The Anvil copycat authorization registry — the hard gate (PLAN_05 §1).

No channel may run against a target not listed in the registry, nor a channel
not enabled for that target. The ``reuse_scope`` field decides what is allowed;
``weights`` is the most ToS-sensitive scope and is refused unless an explicit,
recorded per-provider ToS check is present.

Enforcement is an *assertion that fails the run* — :class:`RegistryError` — not a
soft warning. The registry is intentionally **outside Anvil's action space**: the
loop must never be able to weaken its own authorization gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# The four channel values (PLAN_05 §1.2).
VALID_CHANNELS: frozenset[str] = frozenset({"structural", "outcome", "self_distill", "deny"})

# The four reuse_scope values (PLAN_05 §1.1), ordered by privilege.
VALID_SCOPES: frozenset[str] = frozenset({"deny", "structure_only", "outcomes", "weights"})
_SCOPE_RANK: dict[str, int] = {"deny": 0, "structure_only": 1, "outcomes": 2, "weights": 3}

# The gate components — the eval suite, the verifier, the manifest's
# prediction_metrics, the registry itself, and the kill switches — are OUTSIDE
# Anvil's action space (07 §7.2, "the single most important rule"). A patch that
# targets any of these must fail the run: the loop must never be able to weaken
# its own oracle. These are matched as substrings against a bundle's
# ``manifest_entry`` / ``target`` (case-insensitive), so both bare component
# names ("verifier") and dotted/path targets ("anvil.gate.py", "teacher/verifier")
# are caught.
GATE_COMPONENTS: frozenset[str] = frozenset(
    {
        "verifier",
        "eval",
        "metrics",
        "prediction_metrics",
        "registry",
        "kill_switch",
        "kill_switches",
        "killswitch",
        "promote",
        "gate",
    }
)


class RegistryError(Exception):
    """A copycat run was refused by the authorization registry."""


class GateComponentError(Exception):
    """A patch bundle targeted a gate component — refused (07 §7.2)."""


def gate_component_hit(target: str | None) -> str | None:
    """Return the gate-component token a ``target`` names, or ``None``.

    A ``target`` "names" a gate component if any :data:`GATE_COMPONENTS` token
    appears as a whole word inside it — i.e. delimited by start/end of string or a
    non-alphanumeric boundary (``.`` ``/`` ``_`` ``-`` whitespace). This catches
    ``verifier``, ``anvil.gate``, ``teacher/verifier.py`` and ``eval_suite`` while
    not flagging unrelated names that merely contain a token as a fragment
    (e.g. ``evaluate``, ``aggregate``, ``delegate``).
    """
    if not target:
        return None
    low = target.lower()
    for token in GATE_COMPONENTS:
        idx = low.find(token)
        while idx != -1:
            before = low[idx - 1] if idx > 0 else ""
            after_pos = idx + len(token)
            after = low[after_pos] if after_pos < len(low) else ""
            if not before.isalnum() and not after.isalnum():
                return token
            idx = low.find(token, idx + 1)
    return None


def assert_not_gate_component(*targets: str | None) -> None:
    """Refuse the run if any ``target`` names a gate component (07 §7.2).

    This is the structural fix for the highest risk in the program — a
    self-modifying system editing its own evaluation gate. It is an assertion
    that *fails the run*, not a warning.
    """
    for target in targets:
        token = gate_component_hit(target)
        if token is not None:
            raise GateComponentError(
                f"patch target '{target}' names the gate component '{token}', which is "
                f"outside Anvil's action space (07 §7.2): the eval suite, verifier, "
                f"metric definitions, registry, and kill switches may never be edited "
                f"by a patch bundle. Refusing the run."
            )


@dataclass(frozen=True)
class Target:
    """One authorized copycat target."""

    id: str
    channel: tuple[str, ...]
    source: str
    license: str
    reuse_scope: str
    notes: str = ""
    rate_limit: dict[str, Any] | None = None
    tos_check: dict[str, Any] | None = None

    def permits_channel(self, channel: str) -> bool:
        return channel in self.channel

    def has_tos_check(self) -> bool:
        """A ToS check is 'recorded' iff it names a provider and a review date."""
        if not isinstance(self.tos_check, dict):
            return False
        return bool(self.tos_check.get("provider")) and bool(self.tos_check.get("reviewed_on"))


@dataclass(frozen=True)
class Registry:
    """The parsed registry: a mapping of target id -> :class:`Target`."""

    targets: dict[str, Target] = field(default_factory=dict)

    def get(self, target_id: str) -> Target:
        target = self.targets.get(target_id)
        if target is None:
            known = ", ".join(sorted(self.targets)) or "(none)"
            raise RegistryError(
                f"target '{target_id}' is not in the registry "
                f"(known targets: {known}). Add it to registry.yaml first."
            )
        return target

    def assert_channel_allowed(self, target_id: str, channel: str) -> None:
        """Refuse a channel not enabled for the target (PLAN_05 §1.3)."""
        if channel not in VALID_CHANNELS:
            raise RegistryError(f"invalid channel '{channel}'")
        target = self.get(target_id)
        if not target.permits_channel(channel):
            enabled = ", ".join(target.channel) or "(none)"
            raise RegistryError(
                f"channel '{channel}' is not enabled for target '{target_id}' "
                f"(enabled: {enabled})."
            )

    def assert_reuse_scope(self, target_id: str, required_scope: str) -> None:
        """Refuse a run whose required scope exceeds the target's grant.

        ``weights`` is refused unless the grant is ``weights`` *and* a per-provider
        ToS check is recorded.
        """
        if required_scope not in VALID_SCOPES:
            raise RegistryError(f"invalid reuse_scope '{required_scope}'")
        target = self.get(target_id)
        granted = target.reuse_scope
        if _SCOPE_RANK[granted] < _SCOPE_RANK[required_scope]:
            raise RegistryError(
                f"target '{target_id}' grants reuse_scope '{granted}', "
                f"which does not permit '{required_scope}'."
            )
        if required_scope == "weights" and not target.has_tos_check():
            raise RegistryError(
                f"target '{target_id}' requires a recorded per-provider ToS check "
                f"before the 'weights' scope may run (none found or it is stale)."
            )


def _parse_target(raw: dict[str, Any]) -> Target:
    target_id = str(raw.get("id", "")).strip()
    if not target_id:
        raise RegistryError("registry entry is missing an 'id'")

    channel_raw = raw.get("channel", [])
    if not isinstance(channel_raw, list) or not channel_raw:
        raise RegistryError(f"target '{target_id}' must list at least one channel")
    channel: tuple[str, ...] = tuple(str(c).strip() for c in channel_raw)
    for c in channel:
        if c not in VALID_CHANNELS:
            raise RegistryError(
                f"target '{target_id}' has invalid channel '{c}' "
                f"(valid: {', '.join(sorted(VALID_CHANNELS))})"
            )

    reuse_scope = str(raw.get("reuse_scope", "")).strip()
    if reuse_scope not in VALID_SCOPES:
        raise RegistryError(
            f"target '{target_id}' has invalid reuse_scope '{reuse_scope}' "
            f"(valid: {', '.join(sorted(VALID_SCOPES))})"
        )

    return Target(
        id=target_id,
        channel=channel,
        source=str(raw.get("source", "")),
        license=str(raw.get("license", "")),
        reuse_scope=reuse_scope,
        notes=str(raw.get("notes", "")),
        rate_limit=raw.get("rate_limit") if isinstance(raw.get("rate_limit"), dict) else None,
        tos_check=raw.get("tos_check") if isinstance(raw.get("tos_check"), dict) else None,
    )


def load_registry(path: str | Path) -> Registry:
    """Load and validate the registry YAML at ``path``."""
    p = Path(path)
    if not p.is_file():
        raise RegistryError(f"registry file not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RegistryError(f"registry at {p} is not a mapping")
    raw_targets = data.get("targets", [])
    if not isinstance(raw_targets, list):
        raise RegistryError(f"registry at {p}: 'targets' must be a list")

    targets: dict[str, Target] = {}
    for raw in raw_targets:
        if not isinstance(raw, dict):
            raise RegistryError(f"registry at {p}: each target must be a mapping")
        target = _parse_target(raw)
        if target.id in targets:
            raise RegistryError(f"registry at {p}: duplicate target id '{target.id}'")
        targets[target.id] = target
    return Registry(targets=targets)
