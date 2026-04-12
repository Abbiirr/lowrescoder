#!/usr/bin/env bash
# Setup for b27-minimal-config-change
set -euo pipefail

cat > config.yaml << 'YAML'
# Application configuration
service:
  host: localhost
  port: 9090
  timeout: 30
  retries: 3

logging:
  level: INFO
  file: app.log
YAML

cat > app.py << 'PY'
"""Application that connects to a backend service."""
import yaml


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def get_service_url(config: dict | None = None) -> str:
    """Build the service URL from config."""
    if config is None:
        config = load_config()
    host = config["service"]["host"]
    port = config["service"]["port"]
    return f"http://{host}:{port}"


def health_check(config: dict | None = None) -> bool:
    """Check if the service is reachable."""
    url = get_service_url(config)
    return url == "http://localhost:8080"
PY

cat > test_app.py << 'PY'
"""Tests for app configuration."""
import unittest
from app import load_config, get_service_url, health_check


class TestAppConfig(unittest.TestCase):
    def test_service_url(self):
        """Service URL should point to port 8080."""
        url = get_service_url()
        self.assertEqual(url, "http://localhost:8080")

    def test_health_check(self):
        """Health check should pass with correct port."""
        self.assertTrue(health_check())

    def test_config_port(self):
        """Config should specify port 8080."""
        config = load_config()
        self.assertEqual(config["service"]["port"], 8080)


if __name__ == "__main__":
    unittest.main()
PY

pip install pyyaml -q 2>/dev/null || true

echo "Setup complete. config.yaml has wrong port (9090 instead of 8080)."
