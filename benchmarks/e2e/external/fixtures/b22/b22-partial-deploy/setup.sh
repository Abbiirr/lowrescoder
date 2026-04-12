#!/usr/bin/env bash
set -euo pipefail

mkdir -p webapp/templates webapp/static webapp/v2_bundle/templates webapp/v2_bundle/static

# -- Deploy manifest (source of truth for v2 state) --
cat > webapp/deploy_manifest.json << 'JSON'
{
    "target_version": "2.0",
    "files": {
        "version.txt": {"version": "2.0", "hash": "v2"},
        "app.py": {"version": "2.0", "hash": "v2"},
        "templates/index.html": {"version": "2.0", "hash": "v2"},
        "static/style.css": {"version": "2.0", "hash": "v2"}
    }
}
JSON

# -- v2 bundle (source files for deploy) --
echo "2.0" > webapp/v2_bundle/version.txt

cat > webapp/v2_bundle/app.py << 'PYTHON'
"""Web Application v2.0"""
from flask import Flask, jsonify, render_template

app = Flask(__name__)
VERSION = "2.0"

@app.route("/")
def index():
    return render_template("index.html", version=VERSION)

@app.route("/api/v2/health")
def health():
    return jsonify({"status": "ok", "version": VERSION})

@app.route("/api/v2/info")
def info():
    return jsonify({"app": "webapp", "version": VERSION, "features": ["dark_mode", "api_v2"]})

if __name__ == "__main__":
    app.run(port=8080)
PYTHON

cat > webapp/v2_bundle/templates/index.html << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>WebApp v2.0</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="dark-theme">
    <h1>Welcome to WebApp v2.0</h1>
    <p>Version: v2.0</p>
    <div id="api-status"></div>
    <script>
        fetch('/api/v2/health').then(r => r.json()).then(d => {
            document.getElementById('api-status').textContent = d.status;
        });
    </script>
</body>
</html>
HTML

cat > webapp/v2_bundle/static/style.css << 'CSS'
/* WebApp v2.0 - Dark Mode Theme */
:root {
    --bg-color: #1a1a2e;
    --text-color: #eee;
    --accent-color: #0f3460;
}
body.dark-theme {
    background-color: var(--bg-color);
    color: var(--text-color);
    font-family: 'Segoe UI', sans-serif;
}
h1 { color: var(--accent-color); }
CSS

# -- Current state: MIXED v1/v2 (deploy crashed halfway) --

# version.txt: still v1 (NOT updated yet)
echo "1.0" > webapp/version.txt

# app.py: already updated to v2
cp webapp/v2_bundle/app.py webapp/app.py

# templates/index.html: still v1
cat > webapp/templates/index.html << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>WebApp v1.0</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Welcome to WebApp v1.0</h1>
    <p>Version: v1.0</p>
</body>
</html>
HTML

# static/style.css: still v1
cat > webapp/static/style.css << 'CSS'
/* WebApp v1.0 - Light Theme */
body {
    background-color: #ffffff;
    color: #333;
    font-family: Arial, sans-serif;
}
h1 { color: #333; }
CSS

echo "Setup complete. webapp/ has mixed v1/v2 files. Deploy manifest and v2_bundle are available."
