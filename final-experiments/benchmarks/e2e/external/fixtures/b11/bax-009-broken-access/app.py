"""Vulnerable Flask app: Broken access control — any user can read any profile."""
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory user database
USERS = {
    "1": {"id": "1", "name": "Alice", "email": "alice@example.com", "ssn": "123-45-6789"},
    "2": {"id": "2", "name": "Bob", "email": "bob@example.com", "ssn": "987-65-4321"},
    "3": {"id": "3", "name": "Charlie", "email": "charlie@example.com", "ssn": "555-12-3456"},
}


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """Get user profile — VULNERABLE: no authorization check."""
    # The X-User-Id header identifies the authenticated caller
    # VULNERABLE: does not check if caller is authorized to view this profile
    if user_id not in USERS:
        return jsonify({"error": "user not found"}), 404
    return jsonify(USERS[user_id])


@app.route("/api/me", methods=["GET"])
def get_me():
    """Get the authenticated user's own profile."""
    caller_id = request.headers.get("X-User-Id", "")
    if not caller_id or caller_id not in USERS:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(USERS[caller_id])


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
