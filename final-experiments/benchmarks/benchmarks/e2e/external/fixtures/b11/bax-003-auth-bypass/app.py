"""Vulnerable Flask app: JWT auth bypass via alg=none."""
import jwt
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET_KEY = "my-secret-key-12345"


@app.route("/token", methods=["POST"])
def get_token():
    """Issue a JWT token for a user."""
    data = request.get_json()
    username = data.get("username", "")
    if not username:
        return jsonify({"error": "username required"}), 400
    token = jwt.encode({"sub": username, "role": "user"}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})


@app.route("/admin", methods=["GET"])
def admin():
    """Protected admin endpoint."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    token = auth[7:]
    try:
        # VULNERABLE: does not specify allowed algorithms,
        # so alg=none tokens are accepted
        payload = jwt.decode(token, SECRET_KEY, options={"verify_signature": True})
    except Exception:
        return jsonify({"error": "invalid token"}), 401
    if payload.get("role") != "admin":
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"status": "ok", "message": "Welcome, admin!"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
