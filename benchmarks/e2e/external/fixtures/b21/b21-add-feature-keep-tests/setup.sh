#!/usr/bin/env bash
set -euo pipefail

pip install flask pytest --quiet

cat > app.py << 'PY'
from flask import Flask, jsonify, request

app = Flask(__name__)

_users = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
]


@app.route("/")
def index():
    return jsonify({"message": "Welcome to the User API"})


@app.route("/users", methods=["GET"])
def get_users():
    return jsonify({"users": _users})


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    new_user = {"id": len(_users) + 1, "name": data["name"]}
    _users.append(new_user)
    return jsonify(new_user), 201


if __name__ == "__main__":
    app.run(debug=True)
PY

cat > test_app.py << 'PY'
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "message" in data
    assert "Welcome" in data["message"]


def test_get_users(client):
    resp = client.get("/users")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "users" in data
    assert len(data["users"]) >= 2


def test_create_user(client):
    resp = client.post("/users", json={"name": "Charlie"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Charlie"
    assert "id" in data
PY

# Verify baseline: existing tests pass
python -m pytest test_app.py -v

echo "Setup complete. Flask app with 3 endpoints and passing tests."
