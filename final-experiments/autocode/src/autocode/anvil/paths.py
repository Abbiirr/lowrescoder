"""Filesystem layout for the Anvil copycat data root.

Default layout (under the AutoCode repo root)::

    anvil/
      copycat/
        registry.yaml          # the authorization registry (index)
        census/<target>.yaml   # census output
      patch_bundles/pb_NNN/    # propose output
      audit_log.jsonl          # immutable promotion log

The root is resolved from (in order): an explicit argument, the
``AUTOCODE_ANVIL_ROOT`` environment variable, an upward search for an existing
``anvil/copycat/registry.yaml``, then the packaged default ``<repo>/anvil``.
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[3]  # autocode/ repo root
_DEFAULT_ROOT = _PACKAGE_ROOT / "anvil"


def _search_upward(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        candidate = parent / "anvil" / "copycat" / "registry.yaml"
        if candidate.is_file():
            return parent / "anvil"
    return None


def anvil_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("AUTOCODE_ANVIL_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    found = _search_upward(Path.cwd())
    if found is not None:
        return found.resolve()
    return _DEFAULT_ROOT


def copycat_dir(root: Path) -> Path:
    return root / "copycat"


def registry_path(root: Path) -> Path:
    return root / "copycat" / "registry.yaml"


def census_dir(root: Path) -> Path:
    return root / "copycat" / "census"


def census_path(root: Path, target: str) -> Path:
    return census_dir(root) / f"{target}.yaml"


def patch_bundles_dir(root: Path) -> Path:
    return root / "patch_bundles"


def audit_log_path(root: Path) -> Path:
    return root / "audit_log.jsonl"


def next_bundle_id(root: Path) -> str:
    """Allocate the next ``pb_NNN`` id by scanning existing bundles."""
    bundles = patch_bundles_dir(root)
    existing = 0
    if bundles.is_dir():
        for child in bundles.iterdir():
            name = child.name
            if child.is_dir() and name.startswith("pb_") and name[3:].isdigit():
                existing = max(existing, int(name[3:]))
    return f"pb_{existing + 1:03d}"
