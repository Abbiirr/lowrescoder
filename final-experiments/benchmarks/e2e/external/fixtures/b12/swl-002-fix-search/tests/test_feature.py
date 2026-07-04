"""Tests for search endpoint — special characters must not crash."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestSearch:
    def setup_method(self):
        self.client = app.test_client()

    def _search(self, query):
        resp = self.client.get(f"/api/search?q={query}")
        return resp

    # ---- basic functionality ----
    def test_normal_search(self):
        resp = self._search("Widget")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["results"]) >= 1

    def test_empty_query_returns_all(self):
        resp = self._search("")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["results"]) == 5

    # ---- special character queries (these crash the buggy version) ----
    def test_percent_char(self):
        resp = self._search("50%25")  # URL-encoded %
        assert resp.status_code == 200

    def test_bracket_char(self):
        resp = self._search("%5Bv2%5D")  # URL-encoded [v2]
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert any("[v2]" in r["name"] for r in data["results"])

    def test_parenthesis_char(self):
        resp = self._search("%28Pro%29")  # URL-encoded (Pro)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert any("(Pro)" in r["name"] for r in data["results"])

    def test_dollar_sign(self):
        resp = self._search("%249.99")  # URL-encoded $9.99
        assert resp.status_code == 200

    def test_plus_char(self):
        resp = self._search("%2B")  # URL-encoded +
        assert resp.status_code == 200

    def test_dot_char(self):
        """A dot in regex is a wildcard — search for literal dot should be safe."""
        resp = self._search("9.99")
        assert resp.status_code == 200

    def test_backslash_char(self):
        resp = self._search("%5C")  # URL-encoded backslash
        assert resp.status_code == 200
