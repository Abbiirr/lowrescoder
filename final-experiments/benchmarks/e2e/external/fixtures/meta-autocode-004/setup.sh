#!/usr/bin/env bash
set -e
pip install pytest --quiet 2>/dev/null || true
echo "Setup complete. Task: implement ProgressiveContextLoader to beat Codex (61.5% baseline)."
