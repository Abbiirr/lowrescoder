#!/usr/bin/env bash
set -euo pipefail

pip install flask pytest werkzeug > /dev/null 2>&1

mkdir -p app/static/uploads
cd app

# Vulnerable Flask app with insecure file upload
cat > app.py << 'PY'
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"status": "error", "message": "No filename"}), 400

    # INSECURE: No file type check, no filename sanitization, public directory
    filepath = os.path.join(UPLOAD_DIR, f.filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    f.save(filepath)

    return jsonify({
        "status": "ok",
        "filename": f.filename,
        "path": filepath,
    }), 200

@app.route("/files", methods=["GET"])
def list_files():
    files = os.listdir(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else []
    return jsonify({"files": files})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True)
PY

# Test file
cat > test_app.py << 'PY'
import pytest
import os
import sys
import io
import shutil

sys.path.insert(0, os.path.dirname(__file__))
from app import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    # Patch whatever upload dir the app uses
    monkeypatch.setattr("app.UPLOAD_DIR", upload_dir)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_upload_valid_image(client):
    """A .png file should be accepted."""
    data = {"file": (io.BytesIO(b"fake png content"), "photo.png")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"

def test_upload_valid_txt(client):
    """A .txt file should be accepted."""
    data = {"file": (io.BytesIO(b"hello world"), "notes.txt")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200

def test_upload_no_file(client):
    """Missing file field should return 400."""
    resp = client.post("/upload", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "healthy"

def test_list_files(client, tmp_path):
    """List files endpoint should return a list."""
    resp = client.get("/files")
    assert resp.status_code == 200
    assert "files" in resp.get_json()
PY

echo "Setup complete. Flask app with insecure file upload is ready in app/."
