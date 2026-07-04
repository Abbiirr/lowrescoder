#!/usr/bin/env bash
set -euo pipefail

pip install flask pytest > /dev/null 2>&1

mkdir -p app
cd app

# Vulnerable Flask app with open redirect
cat > app.py << 'PY'
from flask import Flask, request, redirect, jsonify, session
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "myapp.example.com"]

@app.route("/")
def index():
    return jsonify({"page": "home"})

@app.route("/dashboard")
def dashboard():
    return jsonify({"page": "dashboard", "user": session.get("user", "anonymous")})

@app.route("/profile")
def profile():
    return jsonify({"page": "profile"})

@app.route("/settings")
def settings():
    return jsonify({"page": "settings"})

@app.route("/login")
def login():
    return jsonify({"page": "login"})

@app.route("/callback")
def oauth_callback():
    """OAuth callback — processes auth code and redirects user."""
    code = request.args.get("code", "")

    # Simulate processing the OAuth code
    if code:
        session["user"] = "authenticated_user"

    # VULNERABLE: Open redirect — no validation of redirect_url
    redirect_url = request.args.get("redirect_url", "/dashboard")
    return redirect(redirect_url)

if __name__ == "__main__":
    app.run(debug=True)
PY

# Test file
cat > test_app.py << 'PY'
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["page"] == "home"

def test_dashboard(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert resp.get_json()["page"] == "dashboard"

def test_callback_default_redirect(client):
    """Callback with no redirect_url should go to /dashboard."""
    resp = client.get("/callback?code=abc123")
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert "/dashboard" in resp.headers["Location"]

def test_callback_internal_redirect(client):
    """Callback with internal redirect_url should work."""
    resp = client.get("/callback?code=abc123&redirect_url=/profile")
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert "/profile" in resp.headers["Location"]

def test_callback_settings_redirect(client):
    """Callback redirecting to /settings should work."""
    resp = client.get("/callback?code=abc123&redirect_url=/settings")
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert "/settings" in resp.headers["Location"]

def test_callback_sets_session(client):
    """Callback with code should set session user."""
    with client.session_transaction() as sess:
        sess.clear()
    client.get("/callback?code=abc123")
    resp = client.get("/dashboard")
    data = resp.get_json()
    assert data["user"] == "authenticated_user"
PY

echo "Setup complete. Flask app with open redirect vulnerability is ready in app/."
