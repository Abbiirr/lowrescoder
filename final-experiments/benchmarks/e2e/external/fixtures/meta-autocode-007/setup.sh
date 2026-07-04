#!/usr/bin/env bash
set -e
pip install pytest --quiet 2>/dev/null || true
echo "Setup complete. Task: fix Pydantic v2 color encoder bug (harness-bench pattern)."
