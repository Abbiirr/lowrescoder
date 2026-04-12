#!/usr/bin/env bash
# Setup for b17-migrate-config-format
# Creates a project with config.ini referenced in 4 files.
set -euo pipefail

pip install --quiet pyyaml 2>/dev/null || true

# config.ini
cat > config.ini << 'INI'
[database]
host = localhost
port = 5432
name = myapp_db
user = admin
password = secret123

[server]
host = 0.0.0.0
port = 8080
workers = 4
debug = false

[logging]
level = INFO
file = app.log
max_size_mb = 10
backup_count = 5

[app]
name = MyApplication
version = 2.1.0
secret_key = abc123def456
max_upload_mb = 50
INI

# app.py — reads config.ini
cat > app.py << 'PYTHON'
"""Main application module."""
import configparser


def load_app_config(config_path="config.ini"):
    """Load application configuration."""
    config = configparser.ConfigParser()
    config.read(config_path)

    return {
        "name": config.get("app", "name"),
        "version": config.get("app", "version"),
        "secret_key": config.get("app", "secret_key"),
        "max_upload_mb": config.getint("app", "max_upload_mb"),
        "debug": config.getboolean("server", "debug"),
    }


def get_app_name(config_path="config.ini"):
    """Get just the application name."""
    config = configparser.ConfigParser()
    config.read(config_path)
    return config.get("app", "name")
PYTHON

# database.py — reads config.ini
cat > database.py << 'PYTHON'
"""Database configuration module."""
import configparser


def load_db_config(config_path="config.ini"):
    """Load database configuration."""
    config = configparser.ConfigParser()
    config.read(config_path)

    return {
        "host": config.get("database", "host"),
        "port": config.getint("database", "port"),
        "name": config.get("database", "name"),
        "user": config.get("database", "user"),
        "password": config.get("database", "password"),
    }


def get_connection_string(config_path="config.ini"):
    """Generate a database connection string."""
    cfg = load_db_config(config_path)
    return f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['name']}"
PYTHON

# logging_config.py — reads config.ini
cat > logging_config.py << 'PYTHON'
"""Logging configuration module."""
import configparser


def load_logging_config(config_path="config.ini"):
    """Load logging configuration."""
    config = configparser.ConfigParser()
    config.read(config_path)

    return {
        "level": config.get("logging", "level"),
        "file": config.get("logging", "file"),
        "max_size_mb": config.getint("logging", "max_size_mb"),
        "backup_count": config.getint("logging", "backup_count"),
    }
PYTHON

# server.py — reads config.ini
cat > server.py << 'PYTHON'
"""Server configuration module."""
import configparser


def load_server_config(config_path="config.ini"):
    """Load server configuration."""
    config = configparser.ConfigParser()
    config.read(config_path)

    return {
        "host": config.get("server", "host"),
        "port": config.getint("server", "port"),
        "workers": config.getint("server", "workers"),
        "debug": config.getboolean("server", "debug"),
    }
PYTHON

# Tests
cat > test_config.py << 'PYTHON'
"""Tests for configuration loading."""
import pytest
from app import load_app_config, get_app_name
from database import load_db_config, get_connection_string
from logging_config import load_logging_config
from server import load_server_config


class TestAppConfig:
    def test_load_app_config(self):
        cfg = load_app_config()
        assert cfg["name"] == "MyApplication"
        assert cfg["version"] == "2.1.0"
        assert cfg["secret_key"] == "abc123def456"
        assert cfg["max_upload_mb"] == 50
        assert cfg["debug"] is False

    def test_get_app_name(self):
        assert get_app_name() == "MyApplication"


class TestDatabaseConfig:
    def test_load_db_config(self):
        cfg = load_db_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 5432
        assert cfg["name"] == "myapp_db"
        assert cfg["user"] == "admin"

    def test_connection_string(self):
        cs = get_connection_string()
        assert "postgresql://" in cs
        assert "admin" in cs
        assert "5432" in cs
        assert "myapp_db" in cs


class TestLoggingConfig:
    def test_load_logging_config(self):
        cfg = load_logging_config()
        assert cfg["level"] == "INFO"
        assert cfg["file"] == "app.log"
        assert cfg["max_size_mb"] == 10
        assert cfg["backup_count"] == 5


class TestServerConfig:
    def test_load_server_config(self):
        cfg = load_server_config()
        assert cfg["host"] == "0.0.0.0"
        assert cfg["port"] == 8080
        assert cfg["workers"] == 4
        assert cfg["debug"] is False
PYTHON

echo "Setup complete. Project with config.ini referenced in 4 files."
