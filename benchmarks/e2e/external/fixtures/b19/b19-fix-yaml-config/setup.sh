#!/usr/bin/env bash
set -euo pipefail

# Create the broken config.yaml
# BUG 1: database section has wrong indentation (3 spaces instead of 2)
# BUG 2: server.port is a string "8080" instead of integer 8080
# BUG 3: database.name key is missing
cat > config.yaml << 'YAML'
server:
  host: "0.0.0.0"
  port: "8080"

database:
  host: "localhost"
   port: 5432

logging:
  level: "INFO"
  file: "/var/log/app.log"
YAML

# Create the Python app that loads and validates config
cat > app.py << 'PY'
"""Application that loads and validates config.yaml."""
import sys
import yaml


REQUIRED_KEYS = {
    "server": ["host", "port"],
    "database": ["host", "port", "name"],
    "logging": ["level", "file"],
}

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def load_config(path: str) -> dict:
    """Load and validate configuration from YAML file."""
    with open(path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML mapping")

    # Check required sections and keys
    for section, keys in REQUIRED_KEYS.items():
        if section not in config:
            raise ValueError(f"Missing required section: {section}")
        if not isinstance(config[section], dict):
            raise ValueError(f"Section '{section}' must be a mapping")
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"Missing required key: {section}.{key}")

    # Type checks
    if not isinstance(config["server"]["port"], int):
        raise TypeError(
            f"server.port must be int, got {type(config['server']['port']).__name__}"
        )
    if not isinstance(config["database"]["port"], int):
        raise TypeError(
            f"database.port must be int, got {type(config['database']['port']).__name__}"
        )

    # Validate log level
    level = config["logging"]["level"]
    if level not in VALID_LOG_LEVELS:
        raise ValueError(
            f"logging.level must be one of {VALID_LOG_LEVELS}, got '{level}'"
        )

    return config


if __name__ == "__main__":
    try:
        config = load_config("config.yaml")
        print(f"Config loaded successfully.")
        print(f"  Server: {config['server']['host']}:{config['server']['port']}")
        print(f"  Database: {config['database']['host']}:{config['database']['port']}/{config['database']['name']}")
        print(f"  Logging: {config['logging']['level']} -> {config['logging']['file']}")
        sys.exit(0)
    except Exception as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)
PY

echo "Setup complete. config.yaml has 3 bugs to fix."
