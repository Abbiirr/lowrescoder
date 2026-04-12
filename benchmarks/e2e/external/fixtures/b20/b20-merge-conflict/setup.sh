#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo && cd repo
git init -b main
git config user.email "test@test.com"
git config user.name "Test User"

# Initial commit
cat > config.py << 'PY'
# Application configuration
APP_NAME = "myapp"
DEBUG = False
PY
cat > app.py << 'PY'
# Main application
from config import APP_NAME
print(f"Starting {APP_NAME}")
PY
git add . && git commit -m "Initial commit"

# Main branch adds database config
cat > config.py << 'PY'
# Application configuration
APP_NAME = "myapp"
DEBUG = False
DATABASE_URL = "postgresql://localhost/myapp"
PY
cat > app.py << 'PY'
# Main application
from config import APP_NAME
from database import connect
print(f"Starting {APP_NAME}")
PY
git add . && git commit -m "Add database config"

# Feature branch adds cache config
git checkout -b feature/cache HEAD~1
cat > config.py << 'PY'
# Application configuration
APP_NAME = "myapp"
DEBUG = False
CACHE_TTL = 300
PY
cat > app.py << 'PY'
# Main application
from config import APP_NAME
from cache import init_cache
print(f"Starting {APP_NAME}")
PY
git add . && git commit -m "Add cache config"

# Start merge (will conflict)
git checkout main
git merge feature/cache --no-commit || true

echo "Setup complete. Repo has unresolved merge conflicts."
