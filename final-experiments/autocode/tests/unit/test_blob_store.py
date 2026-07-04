"""Tests for BlobStore — content-addressed filesystem storage."""

from __future__ import annotations

import hashlib

import pytest

from autocode.core.blob_store import BlobStore


@pytest.fixture()
def blob_store(tmp_path):
    return BlobStore(tmp_path / "blobs")


class TestBlobStore:
    def test_put_and_get(self, blob_store):
        """Store a string and retrieve it by its hash."""
        data = "Hello, world!"
        sha = blob_store.put(data)
        expected_sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
        assert sha == expected_sha
        assert blob_store.get(sha) == data

    def test_deduplication(self, blob_store, tmp_path):
        """Same content stored twice produces the same hash and only one file."""
        data = "duplicate content"
        sha1 = blob_store.put(data)
        sha2 = blob_store.put(data)
        assert sha1 == sha2

        # Verify only one blob file exists
        blob_files = list((tmp_path / "blobs").rglob("*.blob"))
        assert len(blob_files) == 1

    def test_maybe_externalize_small(self, blob_store):
        """Below threshold returns inline."""
        data = "short"
        result = blob_store.maybe_externalize(data, min_size=1024)
        assert result == {"inline": data}

    def test_maybe_externalize_large(self, blob_store):
        """Above threshold returns blob reference with preview."""
        data = "x" * 2000
        result = blob_store.maybe_externalize(data, min_size=1024)
        assert "blob_sha256" in result
        assert "preview" in result
        assert len(result["preview"]) == 200
        # Verify the blob is actually stored
        assert blob_store.get(result["blob_sha256"]) == data

    def test_get_nonexistent(self, blob_store):
        """Getting a nonexistent hash returns None."""
        result = blob_store.get("0000000000000000000000000000000000000000000000000000000000000000")
        assert result is None
