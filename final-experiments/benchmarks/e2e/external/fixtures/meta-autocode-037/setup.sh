#!/usr/bin/env bash
set -e
python -m pip install --quiet pytest 2>/dev/null || true
echo "Setup complete."
