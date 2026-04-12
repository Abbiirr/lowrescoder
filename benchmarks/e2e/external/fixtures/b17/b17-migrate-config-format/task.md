# Task: Migrate Config from INI to YAML

## Objective

Migrate the project's configuration from INI format (`config.ini`) to YAML
format (`config.yaml`), and update all files that read the config.

## Files

- `config.ini` — current configuration file (INI format)
- `app.py` — main app (reads config.ini)
- `database.py` — database module (reads config.ini)
- `logging_config.py` — logging setup (reads config.ini)
- `server.py` — server module (reads config.ini)
- `test_config.py` — tests for configuration loading

## Requirements

- Create `config.yaml` with the same data as `config.ini`
- Update all 4 Python files to read from `config.yaml` instead of `config.ini`
- Delete `config.ini` (or at minimum, it must not be read anymore)
- All tests must pass
- The PyYAML package is available (`pip install pyyaml`)
