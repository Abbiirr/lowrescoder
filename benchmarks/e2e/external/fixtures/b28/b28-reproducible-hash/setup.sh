#!/usr/bin/env bash
set -euo pipefail

mkdir -p project/test_files

# Create test files with known content (no trailing newline variations)
printf 'Hello, World!' > project/test_files/hello.txt
printf '{"key": "value"}' > project/test_files/data.json
printf 'line1\nline2\nline3\n' > project/test_files/lines.txt
printf '' > project/test_files/empty.txt
printf 'The quick brown fox jumps over the lazy dog' > project/test_files/pangram.txt

# Pre-compute expected hashes
cd project
python3 -c "
import hashlib
import json
import os

hashes = {}
for fname in sorted(os.listdir('test_files')):
    path = os.path.join('test_files', fname)
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            hashes[fname] = hashlib.sha256(f.read()).hexdigest()

with open('expected_hashes.json', 'w') as f:
    json.dump(hashes, f, indent=2)
"
cd ..

cat > project/hasher.py << 'PYEOF'
"""Reproducible file hasher — produces consistent SHA-256 hashes."""
import hashlib
import os
import json


def hash_file(path):
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to the file.

    Returns:
        Hex digest string of the SHA-256 hash.
    """
    # TODO: Implement file hashing
    pass


def hash_directory(dir_path):
    """Compute SHA-256 hashes for all files in a directory.

    Args:
        dir_path: Path to the directory.

    Returns:
        Dict mapping filename to hex digest.
    """
    # TODO: Implement directory hashing
    pass
PYEOF

cat > project/test_hasher.py << 'PYEOF'
"""Tests for the reproducible file hasher."""
import unittest
import json
import os
from hasher import hash_file, hash_directory


class TestHashFile(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_files")
        with open(os.path.join(os.path.dirname(__file__), "expected_hashes.json")) as f:
            self.expected = json.load(f)

    def test_hello_hash(self):
        h = hash_file(os.path.join(self.test_dir, "hello.txt"))
        self.assertEqual(h, self.expected["hello.txt"])

    def test_data_hash(self):
        h = hash_file(os.path.join(self.test_dir, "data.json"))
        self.assertEqual(h, self.expected["data.json"])

    def test_lines_hash(self):
        h = hash_file(os.path.join(self.test_dir, "lines.txt"))
        self.assertEqual(h, self.expected["lines.txt"])

    def test_empty_hash(self):
        h = hash_file(os.path.join(self.test_dir, "empty.txt"))
        self.assertEqual(h, self.expected["empty.txt"])

    def test_pangram_hash(self):
        h = hash_file(os.path.join(self.test_dir, "pangram.txt"))
        self.assertEqual(h, self.expected["pangram.txt"])

    def test_returns_string(self):
        h = hash_file(os.path.join(self.test_dir, "hello.txt"))
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)  # SHA-256 hex digest is 64 chars

    def test_reproducible(self):
        """Same file hashed 5 times gives same result."""
        path = os.path.join(self.test_dir, "hello.txt")
        hashes = set(hash_file(path) for _ in range(5))
        self.assertEqual(len(hashes), 1)


class TestHashDirectory(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_files")
        with open(os.path.join(os.path.dirname(__file__), "expected_hashes.json")) as f:
            self.expected = json.load(f)

    def test_all_files_hashed(self):
        result = hash_directory(self.test_dir)
        self.assertEqual(set(result.keys()), set(self.expected.keys()))

    def test_all_hashes_correct(self):
        result = hash_directory(self.test_dir)
        self.assertEqual(result, self.expected)

    def test_returns_dict(self):
        result = hash_directory(self.test_dir)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. hasher.py needs hash_file() and hash_directory() implemented."
