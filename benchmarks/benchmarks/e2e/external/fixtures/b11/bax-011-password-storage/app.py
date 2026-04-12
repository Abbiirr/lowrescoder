"""Vulnerable Flask app: Insecure password storage using MD5."""
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory user store: {username: hashed_password}
users = {}


@app.route("/register", methods=["POST"])
def register():
    """Register a new user — VULNERABLE: uses MD5 for password hashing."""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if username in users:
        return jsonify({"error": "user exists"}), 409
    # VULNERABLE: MD5 is not suitable for password hashing
    hashed = hashlib.md5(password.encode()).hexdigest()
    users[username] = hashed
    return jsonify({"status": "registered"}), 201


@app.route("/login", methods=["POST"])
def login():
    """Login — VULNERABLE: uses MD5 for password verification."""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if username not in users:
        return jsonify({"error": "invalid credentials"}), 401
    # VULNERABLE: MD5 comparison
    hashed = hashlib.md5(password.encode()).hexdigest()
    if users[username] != hashed:
        return jsonify({"error": "invalid credentials"}), 401
    return jsonify({"status": "ok", "user": username})


@app.route("/debug/users", methods=["GET"])
def debug_users():
    """Debug endpoint: show stored password hashes."""
    return jsonify({u: h for u, h in users.items()})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
