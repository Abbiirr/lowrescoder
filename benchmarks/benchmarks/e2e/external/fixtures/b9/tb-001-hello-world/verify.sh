#!/usr/bin/env bash
# Grading script for tb-001-hello-world
set -euo pipefail

EXPECTED="Hello, World!"
ACTUAL=$(bash solution.sh 2>/dev/null)

if [ "$ACTUAL" = "$EXPECTED" ]; then
    echo "PASS: Output matches expected string."
    exit 0
else
    echo "FAIL: Expected '$EXPECTED', got '$ACTUAL'"
    exit 1
fi
