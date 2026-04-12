# Task: Build a CLI File Organizer

## Objective

Build a CLI tool that organizes files in a directory by sorting them into subdirectories based on their file extension. The messy directory `project/inbox/` contains 20 files of different types.

## Requirements

1. Implement `project/organizer.py` — a script that organizes files in a given directory.
2. Create subdirectories named by extension (e.g., `txt/`, `py/`, `jpg/`).
3. Move each file into its corresponding extension subdirectory.
4. Files without extensions go into a `misc/` directory.
5. No files should be lost (all 20 files must be accounted for).
6. The original directory should contain only subdirectories after organizing.
7. The script should be runnable as: `python organizer.py <directory>`

## Files

- `project/inbox/` — messy directory with 20 files
- `project/organizer.py` — implement the organizer here
- `project/spec.md` — detailed specification
