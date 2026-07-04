#!/usr/bin/env bash
# Setup for b27-targeted-import-fix
set -euo pipefail

mkdir -p utils

cat > utils/__init__.py << 'PY'
"""Utils package."""
PY

cat > utils/data_parser.py << 'PY'
"""Data parser module (moved from utils.parser)."""


def parse_data(raw: str) -> dict:
    """Parse a key=value string into a dictionary."""
    result = {}
    for line in raw.strip().split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def validate_data(data: dict) -> bool:
    """Check that all values are non-empty."""
    return all(v for v in data.values())
PY

cat > main.py << 'PY'
"""Main application module."""
from utils.parser import parse_data  # BUG: module was moved to utils.data_parser


RAW_INPUT = """
name = Alice
role = engineer
team = platform
"""


def run():
    """Parse and display the data."""
    data = parse_data(RAW_INPUT)
    for key, value in data.items():
        print(f"{key}: {value}")
    return data


if __name__ == "__main__":
    run()
PY

cat > test_main.py << 'PY'
"""Tests for main module."""
import unittest
from main import run


class TestMain(unittest.TestCase):
    def test_run_parses_data(self):
        """run() should return parsed key-value pairs."""
        data = run()
        self.assertEqual(data["name"], "Alice")
        self.assertEqual(data["role"], "engineer")
        self.assertEqual(data["team"], "platform")

    def test_run_returns_dict(self):
        """run() should return a dict."""
        result = run()
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. main.py imports from a moved module."
