#!/usr/bin/env bash
# Setup for b16-implement-config-parser
# Creates a spec and test file for a simple config parser.
set -euo pipefail

# Specification document
cat > spec.md << 'SPEC'
# Simple Config Parser Specification

## Overview

Implement a `ConfigParser` class that parses a simple INI/TOML-like
configuration format with sections, typed values, and comments.

## Format

```ini
# This is a comment
; This is also a comment

[section_name]
key = value
number = 42
pi = 3.14
enabled = true
name = hello world
```

## Class: `ConfigParser`

### Constructor

```python
ConfigParser()
```

Creates an empty config parser.

### Methods

#### `parse(text: str) -> None`

Parse a config string. Clears any previous state.

#### `parse_file(filepath: str) -> None`

Read and parse a config file. Clears any previous state.

#### `get(section: str, key: str, default=None) -> any`

Get a value from a section. Returns `default` if section or key doesn't exist.

#### `sections() -> list[str]`

Return a list of all section names.

#### `items(section: str) -> dict`

Return all key-value pairs in a section as a dict.
Returns empty dict if section doesn't exist.

#### `has_section(section: str) -> bool`

Return True if the section exists.

#### `has_key(section: str, key: str) -> bool`

Return True if the key exists in the given section.

## Type Coercion Rules

Values are automatically coerced to the appropriate Python type:

1. **Integer**: String of digits, optionally with leading `-`
   - `42` -> `int(42)`, `-10` -> `int(-10)`
2. **Float**: Contains a decimal point with digits
   - `3.14` -> `float(3.14)`, `-0.5` -> `float(-0.5)`
3. **Boolean**: Case-insensitive `true`/`false`
   - `true`, `True`, `TRUE` -> `bool(True)`
   - `false`, `False`, `FALSE` -> `bool(False)`
4. **String**: Everything else (no quotes needed)
   - `hello world` -> `str("hello world")`
   - `"quoted"` -> `str("quoted")` (quotes are stripped if both present)

## Edge Cases

- Blank lines are ignored
- Lines starting with `#` or `;` are comments (ignored)
- Inline comments after values are NOT supported (the `#` is part of the value)
- Keys and values are stripped of leading/trailing whitespace
- Keys before any section header go into a `DEFAULT` section
- Duplicate keys in the same section: last value wins

## Module

The class must be importable as:
```python
from config_parser import ConfigParser
```
SPEC

# Test file
cat > test_config_parser.py << 'PYTHON'
"""Tests for config parser."""
import os
import pytest
from config_parser import ConfigParser


SAMPLE_CONFIG = """
# Application config
[database]
host = localhost
port = 5432
name = myapp_db
debug = false

[server]
host = 0.0.0.0
port = 8080
workers = 4
debug = true
timeout = 30.5

[app]
name = My Application
version = 1.2.3
max_retries = 3
enabled = True
"""


class TestConfigParserBasic:
    def test_parse_sections(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        sections = cp.sections()
        assert "database" in sections
        assert "server" in sections
        assert "app" in sections

    def test_get_string(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.get("database", "host") == "localhost"
        assert cp.get("app", "name") == "My Application"

    def test_get_integer(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.get("database", "port") == 5432
        assert isinstance(cp.get("database", "port"), int)

    def test_get_float(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.get("server", "timeout") == 30.5
        assert isinstance(cp.get("server", "timeout"), float)

    def test_get_boolean(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.get("database", "debug") is False
        assert cp.get("server", "debug") is True
        assert cp.get("app", "enabled") is True

    def test_get_default(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.get("database", "missing") is None
        assert cp.get("database", "missing", "fallback") == "fallback"
        assert cp.get("nonexistent", "key") is None

    def test_has_section(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.has_section("database") is True
        assert cp.has_section("nonexistent") is False

    def test_has_key(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.has_key("database", "host") is True
        assert cp.has_key("database", "missing") is False

    def test_items(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        items = cp.items("database")
        assert items["host"] == "localhost"
        assert items["port"] == 5432
        assert items["debug"] is False

    def test_items_missing_section(self):
        cp = ConfigParser()
        cp.parse(SAMPLE_CONFIG)
        assert cp.items("nonexistent") == {}


class TestConfigParserEdgeCases:
    def test_comments_ignored(self):
        cp = ConfigParser()
        cp.parse("# comment\n; also comment\n[s]\nk = v\n")
        assert cp.get("s", "k") == "v"
        assert len(cp.sections()) == 1

    def test_blank_lines_ignored(self):
        cp = ConfigParser()
        cp.parse("\n\n[s]\n\nk = v\n\n")
        assert cp.get("s", "k") == "v"

    def test_whitespace_stripped(self):
        cp = ConfigParser()
        cp.parse("[s]\n  key  =  value  \n")
        assert cp.get("s", "key") == "value"

    def test_duplicate_key_last_wins(self):
        cp = ConfigParser()
        cp.parse("[s]\nk = first\nk = second\n")
        assert cp.get("s", "k") == "second"

    def test_default_section(self):
        cp = ConfigParser()
        cp.parse("key = value\n[s]\nother = 1\n")
        assert cp.get("DEFAULT", "key") == "value"

    def test_negative_integer(self):
        cp = ConfigParser()
        cp.parse("[s]\nval = -10\n")
        assert cp.get("s", "val") == -10

    def test_negative_float(self):
        cp = ConfigParser()
        cp.parse("[s]\nval = -0.5\n")
        assert cp.get("s", "val") == -0.5

    def test_quoted_string(self):
        cp = ConfigParser()
        cp.parse('[s]\nval = "hello"\n')
        assert cp.get("s", "val") == "hello"

    def test_parse_clears_state(self):
        cp = ConfigParser()
        cp.parse("[a]\nk = 1\n")
        cp.parse("[b]\nk = 2\n")
        assert cp.has_section("b") is True
        assert cp.has_section("a") is False


class TestConfigParserFile:
    def test_parse_file(self, tmp_path):
        config_file = tmp_path / "test.conf"
        config_file.write_text("[s]\nk = 42\n")
        cp = ConfigParser()
        cp.parse_file(str(config_file))
        assert cp.get("s", "k") == 42
PYTHON

# Empty implementation
cat > config_parser.py << 'PYTHON'
"""Simple config file parser.

Implement according to spec.md.
"""

# TODO: Implement ConfigParser class
PYTHON

echo "Setup complete. Config parser spec and tests created."
