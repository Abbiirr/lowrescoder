#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/atomic.py << 'PYEOF'
"""Atomic file writer — ensures no partial writes are visible."""
import os
import tempfile


def atomic_write(path, content):
    """Atomically write content to a file.

    Uses write-to-temp-then-rename pattern to ensure readers never see
    partial content. If the write fails, the original file is unchanged.

    Args:
        path: Target file path.
        content: String content to write.
    """
    # TODO: Implement atomic write using temp file + rename
    pass


def atomic_write_bytes(path, data):
    """Atomically write binary data to a file.

    Args:
        path: Target file path.
        data: Bytes to write.
    """
    # TODO: Implement atomic binary write
    pass
PYEOF

cat > project/test_atomic.py << 'PYEOF'
"""Tests for atomic file write."""
import unittest
import os
import tempfile
import threading
import time
from atomic import atomic_write, atomic_write_bytes


class TestAtomicWrite(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()
        os.close(self.fd)
        # Write initial content
        with open(self.path, 'w') as f:
            f.write("original content")

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_basic_write(self):
        atomic_write(self.path, "new content")
        with open(self.path) as f:
            self.assertEqual(f.read(), "new content")

    def test_overwrites_existing(self):
        atomic_write(self.path, "updated")
        with open(self.path) as f:
            self.assertEqual(f.read(), "updated")

    def test_creates_new_file(self):
        new_path = self.path + ".new"
        try:
            atomic_write(new_path, "brand new")
            with open(new_path) as f:
                self.assertEqual(f.read(), "brand new")
        finally:
            if os.path.exists(new_path):
                os.unlink(new_path)

    def test_no_temp_files_left(self):
        """No temporary files should remain after write."""
        dirname = os.path.dirname(self.path)
        before = set(os.listdir(dirname))
        atomic_write(self.path, "content")
        after = set(os.listdir(dirname))
        new_files = after - before
        # Only the target file should exist (no leftover temp files)
        self.assertEqual(len(new_files), 0,
                         f"Leftover temp files: {new_files}")

    def test_uses_rename_pattern(self):
        """Verify that the implementation uses os.replace or os.rename."""
        import inspect
        source = inspect.getsource(atomic_write)
        has_replace = "os.replace" in source or "os.rename" in source or "shutil.move" in source
        self.assertTrue(has_replace,
                        "atomic_write must use os.replace/os.rename for atomicity")

    def test_content_never_partial(self):
        """Concurrent reader should see either old or new content, never partial."""
        results = []

        def reader():
            for _ in range(100):
                try:
                    with open(self.path) as f:
                        content = f.read()
                    results.append(content)
                except FileNotFoundError:
                    pass
                time.sleep(0.001)

        def writer():
            for _ in range(50):
                atomic_write(self.path, "A" * 1000)
                atomic_write(self.path, "B" * 1000)

        t1 = threading.Thread(target=reader)
        t2 = threading.Thread(target=writer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Every read should be complete content, never mixed A's and B's
        for content in results:
            is_valid = (
                content == "original content" or
                content == "A" * 1000 or
                content == "B" * 1000
            )
            self.assertTrue(is_valid,
                            f"Partial content detected: {content[:50]}...")


class TestAtomicWriteBytes(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()
        os.close(self.fd)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_binary_write(self):
        atomic_write_bytes(self.path, b"\x00\x01\x02\x03")
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), b"\x00\x01\x02\x03")

    def test_large_binary(self):
        data = os.urandom(1024 * 1024)  # 1MB
        atomic_write_bytes(self.path, data)
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), data)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. atomic.py needs atomic write functions implemented."
