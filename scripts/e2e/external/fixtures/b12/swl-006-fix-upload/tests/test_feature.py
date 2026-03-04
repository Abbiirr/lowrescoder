"""Tests for file upload — large files must return a proper JSON error."""
import io
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestUpload:
    def setup_method(self):
        self.client = app.test_client()

    def _upload(self, data, filename="test.txt"):
        return self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(data), filename)},
            content_type="multipart/form-data",
        )

    # ---- normal upload ----
    def test_small_file_upload(self):
        resp = self._upload(b"hello world")
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["filename"] == "test.txt"
        assert data["size"] == 11

    def test_no_file_returns_400(self):
        resp = self.client.post("/api/upload")
        assert resp.status_code == 400

    # ---- large file handling (these fail on the buggy version) ----
    def test_large_file_returns_413(self):
        """Files over 5 MB should return HTTP 413."""
        big = b"x" * (6 * 1024 * 1024)  # 6 MB
        resp = self._upload(big, "bigfile.bin")
        assert resp.status_code == 413

    def test_large_file_returns_json(self):
        """The 413 response should be JSON, not an HTML error page."""
        big = b"x" * (6 * 1024 * 1024)
        resp = self._upload(big, "bigfile.bin")
        assert resp.status_code == 413
        data = json.loads(resp.data)
        assert "error" in data

    def test_large_file_error_message(self):
        """Error message should mention size limit."""
        big = b"x" * (6 * 1024 * 1024)
        resp = self._upload(big, "bigfile.bin")
        data = json.loads(resp.data)
        error_msg = data["error"].lower()
        assert "too large" in error_msg or "size" in error_msg or "limit" in error_msg or "large" in error_msg

    def test_exactly_5mb_is_allowed(self):
        """A file exactly at the limit should be accepted."""
        exact = b"x" * (5 * 1024 * 1024)
        resp = self._upload(exact, "exact.bin")
        # Should be accepted (not rejected)
        assert resp.status_code == 201
