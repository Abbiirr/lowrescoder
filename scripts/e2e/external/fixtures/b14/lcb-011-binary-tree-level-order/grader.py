#!/usr/bin/env python3
"""Grader for lcb-011-binary-tree-level-order."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
    capture_output=True, text=True, timeout=60,
)
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)
