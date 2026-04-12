#!/usr/bin/env bash
# Setup for b29-handle-missing-file
set -euo pipefail

cat > app.py << 'PY'
"""Application that loads config from a JSON file."""
import json


DEFAULT_CONFIG = {
    "debug": False,
    "port": 8080,
    "log_level": "INFO",
}


def load_config(path: str = "config.json") -> dict:
    """Load configuration from a JSON file.

    BUG: No error handling — crashes if file is missing.
    """
    with open(path) as f:
        return json.load(f)


def get_port(config: dict | None = None) -> int:
    """Get the configured port number."""
    if config is None:
        config = load_config()
    return config.get("port", 8080)


def is_debug(config: dict | None = None) -> bool:
    """Check if debug mode is enabled."""
    if config is None:
        config = load_config()
    return config.get("debug", False)
PY

cat > test_app.py << 'PY'
"""Tests for app config handling."""
import json
import os
import unittest
from app import load_config, get_port, is_debug, DEFAULT_CONFIG


class TestMissingConfig(unittest.TestCase):
    def setUp(self):
        """Ensure config.json does not exist before each test."""
        if os.path.exists("config.json"):
            os.remove("config.json")

    def tearDown(self):
        """Clean up config.json after tests."""
        if os.path.exists("config.json"):
            os.remove("config.json")

    def test_no_crash_when_missing(self):
        """load_config must not raise when config.json is missing."""
        try:
            config = load_config()
        except FileNotFoundError:
            self.fail("load_config() raised FileNotFoundError")

    def test_creates_default_config(self):
        """load_config must create config.json with defaults if missing."""
        load_config()
        self.assertTrue(os.path.exists("config.json"))
        with open("config.json") as f:
            data = json.load(f)
        self.assertFalse(data["debug"])
        self.assertEqual(data["port"], 8080)

    def test_returns_default_values(self):
        """load_config must return defaults when file was missing."""
        config = load_config()
        self.assertEqual(config["port"], 8080)
        self.assertFalse(config["debug"])

    def test_get_port_when_missing(self):
        """get_port must work even if config.json is missing."""
        port = get_port()
        self.assertEqual(port, 8080)


class TestExistingConfig(unittest.TestCase):
    def setUp(self):
        """Create a custom config.json."""
        self.custom = {"debug": True, "port": 3000, "log_level": "DEBUG"}
        with open("config.json", "w") as f:
            json.dump(self.custom, f)

    def tearDown(self):
        if os.path.exists("config.json"):
            os.remove("config.json")

    def test_loads_existing_config(self):
        """load_config must load existing config.json."""
        config = load_config()
        self.assertEqual(config["port"], 3000)
        self.assertTrue(config["debug"])

    def test_get_port_existing(self):
        port = get_port()
        self.assertEqual(port, 3000)

    def test_is_debug_existing(self):
        self.assertTrue(is_debug())


if __name__ == "__main__":
    unittest.main()
PY

# Delete config.json to simulate the fault
rm -f config.json

echo "Setup complete. config.json is missing, app.py will crash."
