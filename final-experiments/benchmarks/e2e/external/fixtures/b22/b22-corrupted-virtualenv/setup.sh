#!/usr/bin/env bash
set -euo pipefail

# Create a virtualenv with pip installed
# Try multiple methods for portability
if command -v uv &> /dev/null; then
    uv venv venv --seed 2>/dev/null
elif python3 -c "import ensurepip" 2>/dev/null; then
    python3 -m venv venv
else
    python3 -m venv --without-pip venv
    curl -sS https://bootstrap.pypa.io/get-pip.py | venv/bin/python 2>/dev/null
fi

# Verify pip works before corrupting
if ! venv/bin/pip --version > /dev/null 2>&1; then
    echo "ERROR: Could not create a working venv with pip"
    exit 1
fi

# Corrupt pip by deleting its __init__.py
PIP_INIT=$(find venv -path "*/pip/__init__.py" -print -quit)
if [ -z "$PIP_INIT" ]; then
    echo "ERROR: Could not find pip's __init__.py in venv"
    exit 1
fi
rm "$PIP_INIT"

# Also remove pip dist-info so ensurepip can reinstall cleanly
# (without this, ensurepip says "already satisfied" and does nothing)
find venv -maxdepth 5 -type d -name "pip-*.dist-info" -exec rm -rf {} + 2>/dev/null || true

echo "Setup complete. Virtualenv pip is corrupted (pip package removed)."
