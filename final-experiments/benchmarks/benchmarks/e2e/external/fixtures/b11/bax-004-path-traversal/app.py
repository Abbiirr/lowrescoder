"""Vulnerable Flask app: Path traversal via unsanitized file download."""
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


@app.route("/download", methods=["GET"])
def download():
    """Download a file from the uploads directory."""
    filename = request.args.get("file", "")
    if not filename:
        return jsonify({"error": "file parameter required"}), 400
    # VULNERABLE: os.path.join does not prevent traversal with ../
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "not found"}), 404
    return send_file(filepath)


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


# Create uploads dir with a sample file on startup
os.makedirs(UPLOAD_DIR, exist_ok=True)
sample = os.path.join(UPLOAD_DIR, "readme.txt")
if not os.path.exists(sample):
    with open(sample, "w") as f:
        f.write("This is a sample file.")


if __name__ == "__main__":
    app.run(debug=False)
