#!/usr/bin/env bash
set -euo pipefail

mkdir -p app

# Create the backup (valid config)
cat > app/config.json.bak << 'JSON'
{
    "host": "localhost",
    "port": 8080,
    "database": {
        "url": "postgresql://localhost:5432/myapp",
        "pool_size": 5,
        "timeout": 30
    },
    "debug": false,
    "log_level": "info"
}
JSON

# Create the corrupted config (truncated mid-write)
cat > app/config.json << 'JSON'
{
    "host": "localhost",
    "port": 8080,
    "database": {
        "url": "postgresql://localhost:5432/myapp",
        "pool_size": 5
JSON

# Create the application that depends on config.json
cat > app/main.py << 'PYTHON'
import json
import sys
import os

config_path = os.path.join(os.path.dirname(__file__), "config.json")

try:
    with open(config_path) as f:
        config = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
    sys.exit(1)

required_keys = ["host", "port", "database", "debug"]
missing = [k for k in required_keys if k not in config]
if missing:
    print(f"ERROR: Missing required config keys: {missing}", file=sys.stderr)
    sys.exit(1)

print(f"App started on {config['host']}:{config['port']}")
sys.exit(0)
PYTHON

echo "Setup complete. config.json is corrupted (truncated). Backup exists at config.json.bak."
