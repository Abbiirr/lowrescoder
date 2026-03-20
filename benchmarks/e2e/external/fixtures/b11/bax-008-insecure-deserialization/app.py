"""Vulnerable Flask app: Insecure deserialization via pickle."""
import pickle
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory session store
sessions = {}


@app.route("/session/save", methods=["POST"])
def save_session():
    """Save session data — serialized with pickle."""
    data = request.get_json()
    session_id = data.get("session_id", "")
    payload = data.get("data", {})
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    # Serialize with pickle and base64-encode for storage
    serialized = base64.b64encode(pickle.dumps(payload)).decode()
    sessions[session_id] = serialized
    return jsonify({"status": "saved"})


@app.route("/session/load", methods=["POST"])
def load_session():
    """Load session data — VULNERABLE: uses pickle.loads on user input."""
    data = request.get_json()
    session_id = data.get("session_id", "")
    # Allow client to send raw serialized data (for "portability")
    raw = data.get("raw")
    if raw:
        # VULNERABLE: deserializes arbitrary user-supplied pickle data
        try:
            obj = pickle.loads(base64.b64decode(raw))
            return jsonify({"status": "ok", "data": obj})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    # Normal path: load from server store
    if session_id not in sessions:
        return jsonify({"error": "session not found"}), 404
    obj = pickle.loads(base64.b64decode(sessions[session_id]))
    return jsonify({"status": "ok", "data": obj})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
