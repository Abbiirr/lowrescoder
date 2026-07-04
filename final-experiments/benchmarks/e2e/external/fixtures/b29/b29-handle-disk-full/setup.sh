#!/usr/bin/env bash
# Setup for b29-handle-disk-full
set -euo pipefail

cat > writer.py << 'PY'
"""File writer module."""
import json
import os


def write_report(path: str, data: dict) -> bool:
    """Write a report as JSON to the given path.

    BUG: No error handling for disk-full or I/O errors.
    Leaves partial files on failure.
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return True


def append_log(path: str, message: str) -> bool:
    """Append a log message to a file."""
    with open(path, "a") as f:
        f.write(message + "\n")
    return True
PY

cat > test_writer.py << 'PY'
"""Tests for file writer with disk-full handling."""
import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from writer import write_report


class TestWriteReportNormal(unittest.TestCase):
    def setUp(self):
        self.test_path = "test_output.json"

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_writes_json(self):
        """Should write valid JSON to file."""
        data = {"name": "test", "value": 42}
        result = write_report(self.test_path, data)
        self.assertTrue(result)
        with open(self.test_path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)


class TestWriteReportDiskFull(unittest.TestCase):
    def test_handles_oserror(self):
        """Should not crash on OSError (disk full)."""
        path = "should_not_exist.json"
        data = {"key": "value"}

        with patch("builtins.open", mock_open()) as mocked_file:
            mocked_file.return_value.write.side_effect = OSError(
                28, "No space left on device"
            )
            try:
                write_report(path, data)
                # If it returns without raising, that's acceptable
                # as long as it handled the error
            except OSError:
                self.fail("write_report did not handle OSError")
            except Exception:
                # A custom exception wrapping OSError is fine
                pass

    def test_cleans_up_partial_file(self):
        """Partial file should be removed on failure."""
        path = "partial_output.json"
        data = {"key": "value"}

        # Create a partial file to simulate what would be left behind
        with open(path, "w") as f:
            f.write("{partial")

        with patch("builtins.open", mock_open()) as mocked_file:
            mocked_file.return_value.write.side_effect = OSError(
                28, "No space left on device"
            )
            with patch("os.path.exists", return_value=True):
                with patch("os.remove") as mock_remove:
                    try:
                        write_report(path, data)
                    except Exception:
                        pass
                    # Verify cleanup was attempted
                    mock_remove.assert_called_with(path)

        # Clean up real file
        if os.path.exists(path):
            os.remove(path)

    def test_reports_error(self):
        """Should raise an exception with a descriptive message after cleanup."""
        path = "fail_output.json"
        data = {"key": "value"}

        with patch("builtins.open", mock_open()) as mocked_file:
            mocked_file.return_value.write.side_effect = OSError(
                28, "No space left on device"
            )
            with self.assertRaises(Exception) as ctx:
                write_report(path, data)

            # The error message should mention the problem
            error_msg = str(ctx.exception).lower()
            self.assertTrue(
                any(word in error_msg for word in ["disk", "space", "write", "failed", "error"]),
                f"Error message not descriptive enough: {ctx.exception}"
            )


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. writer.py has no disk-full error handling."
