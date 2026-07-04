#!/usr/bin/env bash
set -euo pipefail

# Create a simple Flask app
cat > app.py << 'PY'
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def hello():
    return jsonify({"message": "Hello, World!"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
PY

# Create requirements file
cat > requirements.txt << 'REQ'
flask==3.0.0
gunicorn==21.2.0
REQ

# Create the broken Dockerfile
cat > Dockerfile << 'DOCKER'
FROM python:3.11-ultraslim

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
DOCKER

echo "Setup complete. Dockerfile has 3 issues to fix."
