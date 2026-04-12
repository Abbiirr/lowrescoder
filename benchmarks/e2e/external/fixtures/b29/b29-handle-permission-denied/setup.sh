#!/usr/bin/env bash
# Setup for b29-handle-permission-denied
set -euo pipefail

cat > file_reader.py << 'PY'
"""File reader module that processes multiple files."""


def read_all(filepaths: list[str]) -> list[dict]:
    """Read and process a list of files.

    Returns a list of dicts with 'path', 'lines', and 'size' for each file.

    BUG: No error handling — crashes on PermissionError.
    """
    results = []
    for path in filepaths:
        with open(path) as f:
            content = f.read()
        results.append({
            "path": path,
            "lines": len(content.splitlines()),
            "size": len(content),
        })
    return results


def summarize(filepaths: list[str]) -> str:
    """Produce a summary of all files."""
    data = read_all(filepaths)
    total_lines = sum(d["lines"] for d in data)
    total_size = sum(d["size"] for d in data)
    return f"{len(data)} files, {total_lines} lines, {total_size} bytes"
PY

cat > test_reader.py << 'PY'
"""Tests for file reader with permission handling."""
import os
import stat
import unittest
from file_reader import read_all


class TestReadAllNormal(unittest.TestCase):
    def setUp(self):
        with open("readable1.txt", "w") as f:
            f.write("hello\\nworld\\n")
        with open("readable2.txt", "w") as f:
            f.write("foo\\nbar\\nbaz\\n")

    def tearDown(self):
        for f in ["readable1.txt", "readable2.txt"]:
            if os.path.exists(f):
                os.remove(f)

    def test_reads_all_files(self):
        """Should read all accessible files."""
        results = read_all(["readable1.txt", "readable2.txt"])
        # read_all may return (results, errors) tuple or just results
        if isinstance(results, tuple):
            results, errors = results
            self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 2)

    def test_correct_line_count(self):
        """Should count lines correctly."""
        results = read_all(["readable1.txt"])
        if isinstance(results, tuple):
            results, _ = results
        self.assertEqual(results[0]["lines"], 2)


class TestReadAllPermissionDenied(unittest.TestCase):
    def setUp(self):
        with open("allowed.txt", "w") as f:
            f.write("accessible content\\n")
        with open("denied.txt", "w") as f:
            f.write("secret content\\n")
        os.chmod("denied.txt", 0o000)

    def tearDown(self):
        # Restore permissions for cleanup
        if os.path.exists("denied.txt"):
            os.chmod("denied.txt", 0o644)
            os.remove("denied.txt")
        if os.path.exists("allowed.txt"):
            os.remove("allowed.txt")

    def test_no_crash(self):
        """Should not crash on permission denied."""
        try:
            read_all(["allowed.txt", "denied.txt"])
        except PermissionError:
            self.fail("read_all raised PermissionError")

    def test_processes_readable_files(self):
        """Should still process files that are readable."""
        result = read_all(["allowed.txt", "denied.txt"])
        if isinstance(result, tuple):
            results, errors = result
        else:
            results = result
            errors = []
        readable_paths = [r["path"] for r in results]
        self.assertIn("allowed.txt", readable_paths)

    def test_reports_failed_files(self):
        """Should report which files couldn't be read."""
        result = read_all(["allowed.txt", "denied.txt"])
        if isinstance(result, tuple):
            results, errors = result
            self.assertTrue(len(errors) > 0)
            failed_paths = [e if isinstance(e, str) else e.get("path", "") for e in errors]
            self.assertTrue(any("denied" in p for p in failed_paths))
        else:
            # If not returning tuple, at least it didn't crash
            # and skipped the bad file
            paths = [r["path"] for r in result]
            self.assertNotIn("denied.txt", paths)

    def test_mixed_files_count(self):
        """With 1 readable and 1 denied, should get 1 result."""
        result = read_all(["allowed.txt", "denied.txt"])
        if isinstance(result, tuple):
            results, errors = result
        else:
            results = result
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
PY

echo "Setup complete. Permission-denied test files are created by tests/verifier."
