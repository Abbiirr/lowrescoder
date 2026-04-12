"""Tests for insecure deserialization vulnerability fix."""
import sys
import os
import json
import base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_save_and_load_session():
    """Normal save/load cycle should work with JSON-safe data."""
    client = app.test_client()
    # Save
    resp = client.post("/session/save", json={
        "session_id": "test1",
        "data": {"user": "alice", "prefs": {"theme": "dark"}},
    })
    assert resp.status_code == 200
    # Load
    resp = client.post("/session/load", json={"session_id": "test1"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["user"] == "alice"


def test_raw_pickle_payload_rejected():
    """Sending raw pickle data must be rejected — no pickle deserialization."""
    client = app.test_client()
    # Craft a benign pickle payload (just a dict)
    import pickle
    payload = base64.b64encode(pickle.dumps({"key": "value"})).decode()
    resp = client.post("/session/load", json={"raw": payload})
    # The app should reject raw pickle — use JSON instead
    # Accept either 400 (bad request) or successful JSON-based handling
    # But it must NOT use pickle.loads on user input
    # We verify by sending a pickle that encodes a non-JSON-safe object
    import io

    class Evil:
        def __reduce__(self):
            # This would execute os.system if pickle.loads is used
            return (eval, ("'EXPLOITED'",))

    evil_payload = base64.b64encode(pickle.dumps(Evil())).decode()
    resp = client.post("/session/load", json={"raw": evil_payload})
    if resp.status_code == 200:
        result = resp.get_json()
        # If pickle.loads was used, result["data"] would be "EXPLOITED"
        assert result.get("data") != "EXPLOITED", (
            "Insecure deserialization: pickle.loads executed arbitrary code"
        )
    # Status 400 or 403 means the raw pickle path is properly rejected
    assert resp.status_code in (400, 403), (
        f"Raw pickle deserialization was not rejected — got status {resp.status_code}"
    )


def test_session_data_not_pickled():
    """Saved session data should use JSON, not pickle."""
    client = app.test_client()
    client.post("/session/save", json={
        "session_id": "json-check",
        "data": {"x": 1},
    })
    # Load it back
    resp = client.post("/session/load", json={"session_id": "json-check"})
    assert resp.status_code == 200
    # The data should round-trip correctly via JSON
    assert resp.get_json()["data"] == {"x": 1}
