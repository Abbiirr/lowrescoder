#!/usr/bin/env bash
# Setup for b29-handle-network-timeout
set -euo pipefail

python -m pip install requests -q >/dev/null

cat > client.py << 'PY'
"""HTTP client module."""
import requests


def fetch_data(url: str) -> dict:
    """Fetch JSON data from a URL.

    BUG: No timeout — can hang forever.
    BUG: No retry — fails on transient errors.
    """
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_status(url: str) -> int:
    """Fetch just the HTTP status code."""
    data = fetch_data(url)
    return data.get("status", 200)
PY

cat > test_client.py << 'PY'
"""Tests for HTTP client with timeout and retry."""
import unittest
from unittest.mock import patch, MagicMock
import requests
from client import fetch_data


class TestFetchDataTimeout(unittest.TestCase):
    @patch("client.requests.get")
    def test_timeout_parameter_set(self, mock_get):
        """requests.get must be called with a timeout parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetch_data("http://example.com/api")

        # Verify timeout was passed
        _, kwargs = mock_get.call_args
        self.assertIn("timeout", kwargs)
        self.assertGreater(kwargs["timeout"], 0)

    @patch("client.requests.get")
    def test_retry_on_timeout(self, mock_get):
        """Should retry on Timeout, then succeed."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = MagicMock()

        # Fail twice with timeout, succeed on third try
        mock_get.side_effect = [
            requests.exceptions.Timeout("timeout"),
            requests.exceptions.Timeout("timeout"),
            mock_response,
        ]

        result = fetch_data("http://example.com/api")
        self.assertEqual(result, {"result": "ok"})
        self.assertEqual(mock_get.call_count, 3)

    @patch("client.requests.get")
    def test_retry_on_connection_error(self, mock_get):
        """Should retry on ConnectionError."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": 1}
        mock_response.raise_for_status = MagicMock()

        mock_get.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            mock_response,
        ]

        result = fetch_data("http://example.com/api")
        self.assertEqual(result, {"data": 1})
        self.assertEqual(mock_get.call_count, 2)

    @patch("client.requests.get")
    def test_raises_after_max_retries(self, mock_get):
        """Should raise after exhausting retries."""
        mock_get.side_effect = requests.exceptions.Timeout("timeout")

        with self.assertRaises((requests.exceptions.Timeout, Exception)):
            fetch_data("http://example.com/api")

        # Should have tried at least 3 times
        self.assertGreaterEqual(mock_get.call_count, 3)

    @patch("client.requests.get")
    def test_success_on_first_try(self, mock_get):
        """Should work normally when no errors occur."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_data("http://example.com/health")
        self.assertEqual(result, {"status": "healthy"})
        self.assertEqual(mock_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. client.py has no timeout or retry logic."
