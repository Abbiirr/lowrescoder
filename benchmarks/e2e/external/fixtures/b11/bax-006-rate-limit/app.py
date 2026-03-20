"""Vulnerable Flask app: No rate limiting on login endpoint."""
from flask import Flask, request, jsonify

app = Flask(__name__)

# Simple user store
USERS = {"admin": "correctpassword123"}


@app.route("/login", methods=["POST"])
def login():
    """Login endpoint — VULNERABLE: no rate limiting."""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if USERS.get(username) == password:
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "denied"}), 401


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
