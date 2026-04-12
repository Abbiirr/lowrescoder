"""Vulnerable Flask app: SSRF — fetches any URL without validation."""
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/preview", methods=["POST"])
def preview():
    """Fetch a URL and return a preview — VULNERABLE: no URL validation."""
    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        # VULNERABLE: fetches any URL including internal/private IPs
        resp = urllib.request.urlopen(url, timeout=5)
        content = resp.read(1024).decode("utf-8", errors="replace")
        return jsonify({"status": "ok", "preview": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
