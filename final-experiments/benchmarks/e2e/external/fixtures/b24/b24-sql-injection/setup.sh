#!/usr/bin/env bash
set -euo pipefail

pip install flask pytest > /dev/null 2>&1

mkdir -p app
cd app

# Database initialization script
cat > init_db.py << 'PY'
import sqlite3
import hashlib

def init_database(db_path="users.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT
        )
    """)
    # Seed a test user: alice / secretpass
    pw_hash = hashlib.sha256("secretpass".encode()).hexdigest()
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, email) VALUES (?, ?, ?)",
        ("alice", pw_hash, "alice@example.com"),
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()
PY

# Vulnerable Flask app
cat > app.py << 'PY'
import sqlite3
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "users.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    db = get_db()
    # VULNERABLE: SQL injection via string formatting
    query = f"SELECT * FROM users WHERE username = '{username}' AND password_hash = '{pw_hash}'"
    user = db.execute(query).fetchone()
    db.close()

    if user:
        return jsonify({"status": "ok", "user": user["username"]}), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True)
PY

# Test file
cat > test_app.py << 'PY'
import pytest
import os
import sys

# Ensure app directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from init_db import init_database
from app import app

DB_PATH = "test_users.db"

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_users.db")
    monkeypatch.setattr("app.DB_PATH", db_file)
    init_database(db_file)
    yield

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_valid_login(client):
    resp = client.post("/login", json={"username": "alice", "password": "secretpass"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    assert resp.get_json()["user"] == "alice"

def test_invalid_password(client):
    resp = client.post("/login", json={"username": "alice", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.get_json()["status"] == "error"

def test_unknown_user(client):
    resp = client.post("/login", json={"username": "nobody", "password": "whatever"})
    assert resp.status_code == 401
    assert resp.get_json()["status"] == "error"

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "healthy"
PY

# Initialize the database
python init_db.py

echo "Setup complete. Flask app with SQL injection vulnerability is ready in app/."
