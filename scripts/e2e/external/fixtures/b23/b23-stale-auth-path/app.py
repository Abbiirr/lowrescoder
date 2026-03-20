"""Auth app with a stale collaborator handoff baked into the repo."""

from __future__ import annotations

from flask import Flask, jsonify, request

app = Flask(__name__)

TOKENS = {
    "token-admin": {"user": "admin", "role": "admin"},
    "token-viewer": {"user": "viewer", "role": "viewer"},
}


def get_current_user() -> dict[str, str] | None:
    """Return the current user.

    Broken on purpose: the app still trusts the old X-Auth-Token header even
    though the current contract uses Authorization: Bearer <token>.
    """
    token = request.headers.get("X-Auth-Token", "")
    return TOKENS.get(token)


@app.route("/api/session")
def session_view():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"user": user["user"], "role": user["role"]})


@app.route("/api/admin/report")
def admin_report():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    if user["role"] != "admin":
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"status": "ok", "report": "green"})
