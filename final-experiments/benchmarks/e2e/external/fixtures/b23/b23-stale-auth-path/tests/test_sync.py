import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_bearer_token_opens_session():
    client = app.test_client()
    resp = client.get("/api/session", headers=_bearer("token-viewer"))
    assert resp.status_code == 200
    assert resp.get_json()["user"] == "viewer"


def test_admin_report_requires_admin_role():
    client = app.test_client()
    viewer_resp = client.get("/api/admin/report", headers=_bearer("token-viewer"))
    assert viewer_resp.status_code == 403

    admin_resp = client.get("/api/admin/report", headers=_bearer("token-admin"))
    assert admin_resp.status_code == 200
    assert admin_resp.get_json()["report"] == "green"


def test_old_header_is_not_the_contract_anymore():
    client = app.test_client()
    resp = client.get("/api/session", headers={"X-Auth-Token": "token-viewer"})
    assert resp.status_code == 401
