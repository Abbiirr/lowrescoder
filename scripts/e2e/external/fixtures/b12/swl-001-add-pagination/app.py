"""Flask API with user listing — missing pagination."""
from flask import Flask, jsonify, request

app = Flask(__name__)

# 50 seed users
USERS = [{"id": i, "name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1, 51)]


@app.route("/api/users")
def list_users():
    """Return all users.

    TODO: support cursor-based pagination via ?cursor=<id>&limit=<n>.
    Response should include 'users', 'next_cursor', and 'prev_cursor' keys.
    """
    return jsonify({"users": USERS})


if __name__ == "__main__":
    app.run(debug=True)
