"""Tests for cursor-based pagination on /api/users."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


def get_json(client, url):
    resp = client.get(url)
    assert resp.status_code == 200
    return json.loads(resp.data)


class TestPagination:
    def setup_method(self):
        self.client = app.test_client()

    # ---- basic pagination ----
    def test_default_limit(self):
        """Without params, should return at most 10 users (default limit)."""
        data = get_json(self.client, "/api/users")
        assert "users" in data
        assert len(data["users"]) <= 10

    def test_explicit_limit(self):
        data = get_json(self.client, "/api/users?limit=5")
        assert len(data["users"]) == 5

    def test_next_cursor_present(self):
        """First page should include a next_cursor when more data exists."""
        data = get_json(self.client, "/api/users?limit=10")
        assert "next_cursor" in data
        assert data["next_cursor"] is not None

    def test_prev_cursor_absent_on_first_page(self):
        data = get_json(self.client, "/api/users?limit=10")
        assert data.get("prev_cursor") is None

    # ---- walk forward ----
    def test_cursor_walks_forward(self):
        """Fetching with next_cursor should return the next page."""
        page1 = get_json(self.client, "/api/users?limit=10")
        cursor = page1["next_cursor"]
        page2 = get_json(self.client, f"/api/users?cursor={cursor}&limit=10")
        assert page2["users"][0]["id"] != page1["users"][0]["id"]
        assert len(page2["users"]) == 10

    def test_full_traversal(self):
        """Walking all pages collects exactly 50 users."""
        seen = []
        url = "/api/users?limit=10"
        while True:
            data = get_json(self.client, url)
            seen.extend(data["users"])
            if data.get("next_cursor") is None:
                break
            url = f"/api/users?cursor={data['next_cursor']}&limit=10"
        assert len(seen) == 50

    # ---- walk backward ----
    def test_prev_cursor_on_second_page(self):
        page1 = get_json(self.client, "/api/users?limit=10")
        page2 = get_json(
            self.client,
            f"/api/users?cursor={page1['next_cursor']}&limit=10",
        )
        assert "prev_cursor" in page2
        assert page2["prev_cursor"] is not None

    # ---- edge cases ----
    def test_last_page_has_no_next(self):
        """The very last page should have next_cursor = None."""
        url = "/api/users?limit=10"
        data = None
        while True:
            data = get_json(self.client, url)
            if data.get("next_cursor") is None:
                break
            url = f"/api/users?cursor={data['next_cursor']}&limit=10"
        assert data["next_cursor"] is None

    def test_limit_larger_than_dataset(self):
        data = get_json(self.client, "/api/users?limit=100")
        assert len(data["users"]) == 50
        assert data.get("next_cursor") is None
