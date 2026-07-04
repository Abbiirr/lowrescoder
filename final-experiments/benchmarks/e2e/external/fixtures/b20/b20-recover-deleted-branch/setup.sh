#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo && cd repo
git init -b main
git config user.email "test@test.com"
git config user.name "Test User"

echo "# My Project" > README.md
git add . && git commit -m "Initial commit"

echo "version = '1.0'" > version.py
git add . && git commit -m "Add version"

# Create feature branch with 2 commits
git checkout -b feature/important-work
cat > feature.py << 'PY'
def do_important_work():
    """Critical business logic."""
    return "important result"
PY
git add . && git commit -m "Add important work function"

echo "FEATURE_FLAG = True" >> feature.py
git add . && git commit -m "Add feature flag"

# Go back to main and delete the branch
git checkout main
git branch -D feature/important-work

echo "Setup complete. Branch feature/important-work has been deleted."
