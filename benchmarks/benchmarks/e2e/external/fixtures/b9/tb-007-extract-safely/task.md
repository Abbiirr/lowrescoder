# Task: Safely Extract Tar Archive

## Objective

Write a Python script that safely extracts a tar archive, blocking path traversal attacks.

## Requirements

1. Edit `extract.py` to extract `archive.tar` into the `output/` directory.
2. The script must **block** the following dangerous entries:
   - Paths containing `..` (path traversal)
   - Absolute paths (starting with `/`)
   - Symbolic links
3. Safe regular files should be extracted into `output/`.
4. Write a log of blocked entries to `blocked.log` (one filename per line).
5. Run with `python extract.py`.

## Security Context

The archive has been crafted with malicious entries that attempt to:
- Write files outside the output directory using `../`
- Write to absolute paths like `/tmp/`
- Create symlinks to sensitive files

Your extractor must defend against all of these.

## Files

- `archive.tar` — the archive to extract (contains both safe and malicious entries)
- `extract.py` — the script you must edit
- `output/` — the target extraction directory
- `blocked.log` — log of blocked entries (created by your script)
