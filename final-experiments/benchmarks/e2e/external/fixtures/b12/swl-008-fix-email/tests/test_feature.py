"""Tests for email template rendering — user name must appear correctly."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestEmailRender:
    def setup_method(self):
        self.client = app.test_client()

    def _render(self, template, variables):
        return self.client.post(
            "/api/render",
            json={"template": template, "variables": variables},
            content_type="application/json",
        )

    # ---- basic rendering ----
    def test_list_templates(self):
        resp = self.client.get("/api/templates")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "welcome" in data["templates"]

    def test_unknown_template(self):
        resp = self._render("nonexistent", {})
        assert resp.status_code == 404

    # ---- the actual bug: sending "username" key ----
    def test_welcome_with_username(self):
        """Frontend sends 'username' — the rendered output must contain the actual name."""
        resp = self._render("welcome", {"username": "Alice"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "Alice" in data["subject"]
        assert "Alice" in data["body"]
        # Should NOT contain un-rendered placeholder
        assert "{name}" not in data["subject"]
        assert "{name}" not in data["body"]

    def test_reset_with_username(self):
        resp = self._render("reset", {"username": "Bob"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "Bob" in data["subject"]
        assert "Bob" in data["body"]

    def test_invoice_with_username_and_amount(self):
        resp = self._render("invoice", {"username": "Charlie", "amount": "$99.00"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "Charlie" in data["subject"]
        assert "Charlie" in data["body"]
        assert "$99.00" in data["body"]

    def test_no_leftover_placeholders(self):
        """Rendered output must not contain any {name} or {username} placeholders."""
        resp = self._render("welcome", {"username": "Dana"})
        data = json.loads(resp.data)
        assert "{" not in data["subject"]
        assert "{" not in data["body"]

    def test_name_key_also_works(self):
        """If someone sends 'name' directly, it should still work."""
        resp = self._render("welcome", {"name": "Eve"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "Eve" in data["subject"]
