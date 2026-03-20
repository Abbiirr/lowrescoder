#!/usr/bin/env bash
# Setup for tb-007-extract-safely
# Creates a tar archive containing both safe and malicious entries.
# The agent must write an extractor that blocks path traversal attacks.
set -euo pipefail

# Create a temporary directory for building the archive
TMPDIR=$(mktemp -d)

# Create safe files
mkdir -p "$TMPDIR/docs"
echo "README content" > "$TMPDIR/docs/readme.txt"
echo "Config data" > "$TMPDIR/docs/config.json"
echo "Hello from data" > "$TMPDIR/data.txt"

# Create the "safe" tar first
tar cf safe_part.tar -C "$TMPDIR" docs/readme.txt docs/config.json data.txt

# Now create a malicious tar with path traversal entries
# We'll use Python to craft it since GNU tar won't let us add ../
python3 << 'PYTAR'
import tarfile
import io
import os

with tarfile.open("archive.tar", "w") as tf:
    # Add safe files
    safe_tar = tarfile.open("safe_part.tar", "r")
    for member in safe_tar:
        tf.addfile(member, safe_tar.extractfile(member))
    safe_tar.close()

    # Add malicious path traversal entry: ../../../etc/evil.txt
    evil_content = b"EVIL FILE - should not be extracted"
    info = tarfile.TarInfo(name="../../../tmp/evil_traversal.txt")
    info.size = len(evil_content)
    tf.addfile(info, io.BytesIO(evil_content))

    # Add another traversal: absolute path
    abs_content = b"ABSOLUTE PATH FILE - should not be extracted"
    info2 = tarfile.TarInfo(name="/tmp/abs_evil.txt")
    info2.size = len(abs_content)
    tf.addfile(info2, io.BytesIO(abs_content))

    # Add symlink traversal
    info3 = tarfile.TarInfo(name="sneaky_link")
    info3.type = tarfile.SYMTYPE
    info3.linkname = "/etc/passwd"
    tf.addfile(info3)
PYTAR

rm -f safe_part.tar
rm -rf "$TMPDIR"

# Create output directory
mkdir -p output

# Create stub extractor
cat > extract.py << 'STUB'
#!/usr/bin/env python3
"""Safely extract archive.tar into the output/ directory.

Requirements:
- Extract all SAFE files from archive.tar into output/
- BLOCK any entries with path traversal (../ in path)
- BLOCK any entries with absolute paths (starting with /)
- BLOCK any symbolic links
- Only regular files with safe relative paths should be extracted
- Write a log of blocked entries to blocked.log (one entry per line)
"""
# TODO: Implement safe extraction
STUB

chmod +x extract.py

echo "Setup complete. archive.tar created with safe and malicious entries."
