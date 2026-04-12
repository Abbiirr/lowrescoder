#!/usr/bin/env bash
set -euo pipefail

mkdir -p project/inbox

cat > project/spec.md << 'EOF'
# File Organizer Specification

## Usage
```
python organizer.py <directory>
```

## Behavior
1. Scan all files in the given directory (not recursive).
2. For each file, determine its extension (e.g., `.txt` → `txt`).
3. Create a subdirectory named after the extension if it doesn't exist.
4. Move the file into that subdirectory.
5. Files with no extension go into a `misc/` subdirectory.
6. Print a summary of how many files were moved.

## Rules
- Only organize files, not directories.
- Extension detection is case-insensitive: `.TXT` and `.txt` go to `txt/`.
- If a file with the same name already exists in the target dir, skip it.
EOF

# Create 20 files of various types
echo "Report Q1 2024" > project/inbox/report.txt
echo "Meeting notes" > project/inbox/notes.txt
echo "TODO list" > project/inbox/todo.txt
echo "print('hello')" > project/inbox/hello.py
echo "import os" > project/inbox/utils.py
echo "def main(): pass" > project/inbox/main.py
echo "<html></html>" > project/inbox/index.html
echo "<div>content</div>" > project/inbox/about.html
echo "body { color: red; }" > project/inbox/style.css
echo ".header { margin: 0; }" > project/inbox/layout.css
echo '{"key": "value"}' > project/inbox/config.json
echo '{"data": [1,2,3]}' > project/inbox/data.json
echo "name,age" > project/inbox/users.csv
echo "id,product" > project/inbox/products.csv
echo "# README" > project/inbox/readme.md
echo "# Changes" > project/inbox/changelog.md
# Binary-like files (just text content for testing)
printf '\x89PNG fake image' > project/inbox/logo.png
printf '\xFF\xD8 fake jpeg' > project/inbox/photo.jpg
echo "fake pdf content" > project/inbox/document.pdf
# File without extension
echo "license text" > project/inbox/LICENSE

cat > project/organizer.py << 'PYEOF'
"""File organizer — sorts files into subdirectories by extension.

Usage: python organizer.py <directory>
"""
import sys
import os


def organize(directory):
    """Organize files in the given directory by extension.

    Args:
        directory: Path to the directory to organize.

    Returns:
        dict: Summary of files moved per extension.
    """
    # TODO: Implement file organization
    pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python organizer.py <directory>")
        sys.exit(1)
    organize(sys.argv[1])
PYEOF

echo "Setup complete. inbox/ has 20 files to organize."
