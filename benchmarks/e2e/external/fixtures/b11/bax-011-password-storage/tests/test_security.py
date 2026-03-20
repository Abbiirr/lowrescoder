"""Tests for insecure password storage vulnerability fix."""
import sys
import os
import hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def setup_function():
    """Clear users before each test."""
    from app import users
    users.clear()


def test_register_and_login():
    """Registration and login should work end-to-end."""
    client = app.test_client()
    resp = client.post("/register", json={"username": "testuser", "password": "mypassword"})
    assert resp.status_code == 201
    resp = client.post("/login", json={"username": "testuser", "password": "mypassword"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_wrong_password_rejected():
    """Wrong password should be rejected."""
    client = app.test_client()
    client.post("/register", json={"username": "testuser", "password": "mypassword"})
    resp = client.post("/login", json={"username": "testuser", "password": "wrongpass"})
    assert resp.status_code == 401


def test_password_not_stored_as_md5():
    """Password must NOT be stored as a plain MD5 hash."""
    client = app.test_client()
    password = "securepassword123"
    client.post("/register", json={"username": "hashcheck", "password": password})
    # Get the stored hash
    resp = client.get("/debug/users")
    stored_hash = resp.get_json()["hashcheck"]
    # Compute what MD5 would produce
    md5_hash = hashlib.md5(password.encode()).hexdigest()
    assert stored_hash != md5_hash, (
        "Password is stored as plain MD5 — must use bcrypt or similar"
    )


def test_password_stored_as_bcrypt():
    """Password should be stored using bcrypt (starts with $2b$ or $2a$)."""
    client = app.test_client()
    client.post("/register", json={"username": "bcryptcheck", "password": "testpass"})
    resp = client.get("/debug/users")
    stored_hash = resp.get_json()["bcryptcheck"]
    assert stored_hash.startswith(("$2b$", "$2a$")), (
        f"Stored hash does not look like bcrypt: {stored_hash[:20]}..."
    )


def test_duplicate_user_rejected():
    """Registering the same username twice should fail."""
    client = app.test_client()
    client.post("/register", json={"username": "dupe", "password": "pass1"})
    resp = client.post("/register", json={"username": "dupe", "password": "pass2"})
    assert resp.status_code == 409
