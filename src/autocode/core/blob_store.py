"""Content-addressed filesystem store for large payloads."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class BlobStore:
    """Content-addressed filesystem store. Large payloads keyed by SHA-256."""

    def __init__(self, blob_dir: str | Path) -> None:
        self._root = Path(blob_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, sha256_hex: str) -> Path:
        """Return 2-level prefix path: ab/cd/abcd1234...5678.blob"""
        return self._root / sha256_hex[:2] / sha256_hex[2:4] / f"{sha256_hex}.blob"

    def put(self, data: str) -> str:
        """Store data and return its SHA-256 hex digest. Deduplicates."""
        sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
        path = self._blob_path(sha)
        if path.exists():
            return sha
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(str(tmp), str(path))
        return sha

    def get(self, sha256_hex: str) -> str | None:
        """Return content for a given hash, or None if not found."""
        path = self._blob_path(sha256_hex)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def exists(self, sha256_hex: str) -> bool:
        """Check if a blob exists."""
        return self._blob_path(sha256_hex).exists()

    def maybe_externalize(self, data: str, min_size: int = 1024) -> dict:
        """Externalize data to blob if above min_size threshold.

        Returns {"inline": data} if small, or
        {"blob_sha256": hash, "preview": first_200_chars} if large.
        """
        if len(data) < min_size:
            return {"inline": data}
        sha = self.put(data)
        return {"blob_sha256": sha, "preview": data[:200]}
