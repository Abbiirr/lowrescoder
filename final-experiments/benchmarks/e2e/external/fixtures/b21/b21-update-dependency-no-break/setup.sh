#!/usr/bin/env bash
set -euo pipefail

pip install pytest --quiet

cat > configparser_app.py << 'PY'
"""Simple config parser — currently supports v1 (INI-style) format only."""


def parse_config(filepath):
    """Parse a config file and return dict of sections with key-value pairs.

    Args:
        filepath: Path to the config file.

    Returns:
        dict[str, dict[str, str]]: Sections mapped to their key-value pairs.
    """
    result = {}
    current_section = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                result[current_section] = {}
            elif "=" in line and current_section is not None:
                key, value = line.split("=", 1)
                result[current_section][key.strip()] = value.strip()

    return result
PY

cat > sample_v1.conf << 'CONF'
# Application config (v1 format)

[database]
host = localhost
port = 5432
name = mydb

[server]
host = 0.0.0.0
port = 8080
CONF

cat > sample_v2.conf << 'CONF'
# Application config (v2 format)
database:
  host: localhost
  port: 5432
  name: mydb
server:
  host: 0.0.0.0
  port: 8080
CONF

cat > test_configparser.py << 'PY'
import os
import pytest
import tempfile
from configparser_app import parse_config


@pytest.fixture
def v1_config_file():
    content = """
[database]
host = localhost
port = 5432
name = testdb

[server]
host = 127.0.0.1
port = 9090
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


def test_parse_v1_sections(v1_config_file):
    config = parse_config(v1_config_file)
    assert "database" in config
    assert "server" in config


def test_parse_v1_database_values(v1_config_file):
    config = parse_config(v1_config_file)
    db = config["database"]
    assert db["host"] == "localhost"
    assert db["port"] == "5432"
    assert db["name"] == "testdb"


def test_parse_v1_server_values(v1_config_file):
    config = parse_config(v1_config_file)
    srv = config["server"]
    assert srv["host"] == "127.0.0.1"
    assert srv["port"] == "9090"


def test_parse_sample_v1():
    config = parse_config("sample_v1.conf")
    assert config["database"]["host"] == "localhost"
    assert config["server"]["port"] == "8080"
PY

# Verify baseline
python -m pytest test_configparser.py -v

echo "Setup complete. Config parser with v1 support and passing tests."
