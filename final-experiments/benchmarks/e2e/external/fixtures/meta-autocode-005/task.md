# TASK-005: EnvironmentSetup

## Goal
Implement `src/meta_autocode/environment.py` — detects language/build system from a
dict of files and generates setup commands. This is Phase 5 of meta-autocode.

## Why this beats Codex (81.5% on harness-bench v2)
65% of harness failures come from environment setup issues (arxiv 2508.18993v1).
Codex xhigh still fails 18.5% of tasks on harness-bench v2 — many are env failures.
By detecting the build system upfront and generating correct setup commands,
meta-autocode avoids the most common failure class entirely.

## Real harness-bench v2 scores (target to beat):
- Codex gpt-5.5:xhigh   81.5% (22/27) ← BEST, our target
- Codex gpt-5.5:medium   77.8% (21/27)
- Cursor gpt-5.5:medium  77.8% (21/27)
- Claude Opus 4.7:high   74.1% (20/27)
- Claude Opus 4.8:xhigh  56.0% (14/25)
- Maxxing at 81.5%: 1-(1-0.815)^3 = 99.4%

## Deliverable: `src/meta_autocode/environment.py`

### `BuildSystem` (Enum)
Values: `PYTHON_PIP`, `PYTHON_UV`, `NODE_NPM`, `UNKNOWN`

Detection rules (check files dict keys):
- `PYTHON_UV` if `pyproject.toml` present AND content contains `[build-system]` or `[project]`
- `PYTHON_PIP` if `requirements.txt` present, OR `pyproject.toml` present
- `NODE_NPM` if `package.json` present
- `UNKNOWN` otherwise

### `SetupResult` (dataclass)
Fields:
- `success: bool`
- `build_system: str`
- `commands_run: list[str]`
- `error: str = ""`

### `EnvironmentSetup` (class)
- `__init__(self, files: dict[str, str])` — detect build system from file keys/contents
- `build_system: BuildSystem` attribute set during __init__
- `setup_commands(self) -> list[str]`
  - PYTHON_PIP: `["pip install -r requirements.txt"]` (only if requirements.txt in files)
  - PYTHON_UV: `["uv sync"]`
  - NODE_NPM: `["npm install"]`
  - UNKNOWN: `[]`
- `validate(self) -> SetupResult`
  - Returns `SetupResult(success=True, build_system=self.build_system.value, commands_run=self.setup_commands())`

## Constraints
- No external dependencies beyond stdlib
- Do not modify test files, task.md, or verify.sh

## All 9 tests must pass:
```
test_detect_python_pip
test_detect_python_uv
test_detect_node
test_detect_unknown
test_setup_commands_nonempty_for_python
test_setup_commands_empty_for_unknown
test_setup_result_fields
test_validate_python_has_test_runner
test_build_system_enum_has_required_values
```
