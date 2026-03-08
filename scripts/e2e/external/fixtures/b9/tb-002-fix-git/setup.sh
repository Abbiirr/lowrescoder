#!/usr/bin/env bash
# Setup for tb-002-fix-git
# Creates a git repo in broken state: detached HEAD with uncommitted changes.
# The agent must get back to 'main' branch with the changes preserved.
set -euo pipefail

# Create a git repo
mkdir -p repo
cd repo
git init -b main
git config user.email "test@test.com"
git config user.name "Test User"

# Create initial commit
echo "version 1" > file.txt
git add file.txt
git commit -m "Initial commit"

# Create a second commit
echo "version 2" > file.txt
git add file.txt
git commit -m "Second commit"

# Detach HEAD at current commit (main tip) to keep this task focused on
# recovering branch state without merge conflicts.
git checkout HEAD

# Make uncommitted changes in detached HEAD state
echo "important new work" > newfile.txt
echo "version 1 modified" > file.txt

echo "Setup complete. Repo is in detached HEAD state with uncommitted changes."
