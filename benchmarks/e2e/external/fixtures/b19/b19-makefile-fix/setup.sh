#!/usr/bin/env bash
set -euo pipefail

# Create Python package
mkdir -p src/mylib tests
cat > src/mylib/__init__.py << 'PY'
"""My library."""
__version__ = "0.1.0"

def add(a: int, b: int) -> int:
    return a + b
PY

cat > tests/test_mylib.py << 'PY'
from mylib import add

def test_add():
    assert add(1, 2) == 3

def test_add_negative():
    assert add(-1, 1) == 0
PY

cat > pyproject.toml << 'TOML'
[project]
name = "mylib"
version = "0.1.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mylib"]

[tool.pytest.ini_options]
testpaths = ["tests"]
TOML

# Create broken Makefile (spaces instead of tabs, missing .PHONY, etc.)
# NOTE: Deliberately using spaces to create the bug
python3 -c "
content = '''.PHONY: build

build:
    python3 -m build --wheel wrong_package

test:
    python3 -m pytest tests/ -v

clean:
    rm dist/ build/ __pycache__/

lint:
    python3 -m ruff check src/
'''
# Replace leading 4-space indentation with actual spaces (the bug)
with open('Makefile', 'w') as f:
    f.write(content)
"

pip install build ruff pytest hatchling 2>/dev/null || true

echo "Setup complete. Makefile has several bugs to fix."
