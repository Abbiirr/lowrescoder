"""Vulnerable Flask app: CSRF — no token validation on state-changing POST."""
from flask import Flask, request, jsonify, session
import secrets

app = Flask(__name__)
app.secret_key = "dev-secret-key-12345"

# In-memory user settings
user_settings = {"email": "user@example.com", "theme": "light"}


@app.route("/settings", methods=["GET"])
def get_settings():
    """Return current settings."""
    return jsonify(user_settings)


@app.route("/settings", methods=["POST"])
def update_settings():
    """Update user settings — VULNERABLE: no CSRF token check."""
    data = request.get_json()
    if "email" in data:
        user_settings["email"] = data["email"]
    if "theme" in data:
        user_settings["theme"] = data["theme"]
    return jsonify({"status": "updated", "settings": user_settings})


@app.route("/csrf-token", methods=["GET"])
def csrf_token():
    """Issue a CSRF token (stored in session)."""
    token = secrets.token_hex(32)
    session["csrf_token"] = token
    return jsonify({"csrf_token": token})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
