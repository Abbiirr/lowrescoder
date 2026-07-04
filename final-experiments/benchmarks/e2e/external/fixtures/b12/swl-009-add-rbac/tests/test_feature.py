"""Tests for role-based access control on article endpoints."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestRBAC:
    def setup_method(self):
        self.client = app.test_client()
        # Reset articles to known state
        from app import ARTICLES
        ARTICLES.clear()
        ARTICLES.extend([
            {"id": 1, "title": "First Post", "content": "Hello world", "author": "admin"},
            {"id": 2, "title": "Second Post", "content": "Another article", "author": "editor1"},
        ])

    def _headers(self, user):
        return {"X-User": user, "Content-Type": "application/json"}

    # ---- viewer permissions ----
    def test_viewer_can_list(self):
        resp = self.client.get("/api/articles", headers=self._headers("viewer1"))
        assert resp.status_code == 200

    def test_viewer_can_read(self):
        resp = self.client.get("/api/articles/1", headers=self._headers("viewer1"))
        assert resp.status_code == 200

    def test_viewer_cannot_create(self):
        resp = self.client.post(
            "/api/articles",
            json={"title": "Nope", "content": "..."},
            headers=self._headers("viewer1"),
        )
        assert resp.status_code == 403

    def test_viewer_cannot_edit(self):
        resp = self.client.put(
            "/api/articles/1",
            json={"title": "Hacked"},
            headers=self._headers("viewer1"),
        )
        assert resp.status_code == 403

    def test_viewer_cannot_delete(self):
        resp = self.client.delete("/api/articles/1", headers=self._headers("viewer1"))
        assert resp.status_code == 403

    # ---- editor permissions ----
    def test_editor_can_list(self):
        resp = self.client.get("/api/articles", headers=self._headers("editor1"))
        assert resp.status_code == 200

    def test_editor_can_create(self):
        resp = self.client.post(
            "/api/articles",
            json={"title": "Editor Post", "content": "..."},
            headers=self._headers("editor1"),
        )
        assert resp.status_code == 201

    def test_editor_can_edit_own(self):
        resp = self.client.put(
            "/api/articles/2",  # authored by editor1
            json={"title": "Updated"},
            headers=self._headers("editor1"),
        )
        assert resp.status_code == 200

    def test_editor_cannot_edit_others(self):
        resp = self.client.put(
            "/api/articles/1",  # authored by admin
            json={"title": "Hacked"},
            headers=self._headers("editor1"),
        )
        assert resp.status_code == 403

    def test_editor_cannot_delete(self):
        resp = self.client.delete("/api/articles/1", headers=self._headers("editor1"))
        assert resp.status_code == 403

    # ---- admin permissions ----
    def test_admin_can_create(self):
        resp = self.client.post(
            "/api/articles",
            json={"title": "Admin Post", "content": "..."},
            headers=self._headers("admin"),
        )
        assert resp.status_code == 201

    def test_admin_can_edit_any(self):
        resp = self.client.put(
            "/api/articles/2",  # authored by editor1
            json={"title": "Admin Edit"},
            headers=self._headers("admin"),
        )
        assert resp.status_code == 200

    def test_admin_can_delete(self):
        resp = self.client.delete("/api/articles/1", headers=self._headers("admin"))
        assert resp.status_code == 200

    # ---- unknown user ----
    def test_unknown_user_cannot_write(self):
        resp = self.client.post(
            "/api/articles",
            json={"title": "Anon", "content": "..."},
            headers=self._headers("nobody"),
        )
        assert resp.status_code == 403
