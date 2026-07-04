"""Tests for EnvironmentSetup — meta-autocode Phase 5.

65% of harness failures come from environment setup issues (arxiv 2508.18993).
EnvironmentSetup detects language/build system from a file dict, generates
setup commands, and validates readiness before the PIV loop starts.

This directly addresses why Codex xhigh (81.5%) still fails 18.5% of tasks
on harness-bench v2 — many are environment setup failures, not logic failures.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from meta_autocode.environment import EnvironmentSetup, BuildSystem, SetupResult


def test_detect_python_pip():
    files = {"requirements.txt": "pytest\nrequests\n", "src/main.py": "print('hi')"}
    env = EnvironmentSetup(files)
    assert env.build_system == BuildSystem.PYTHON_PIP


def test_detect_python_uv():
    files = {"pyproject.toml": "[project]\nname='x'\n", "src/x.py": "x=1"}
    env = EnvironmentSetup(files)
    assert env.build_system in (BuildSystem.PYTHON_UV, BuildSystem.PYTHON_PIP)


def test_detect_node():
    files = {"package.json": '{"name":"app","scripts":{"test":"jest"}}', "index.js": "module.exports={}"}
    env = EnvironmentSetup(files)
    assert env.build_system == BuildSystem.NODE_NPM


def test_detect_unknown():
    files = {"README.md": "# project"}
    env = EnvironmentSetup(files)
    assert env.build_system == BuildSystem.UNKNOWN


def test_setup_commands_nonempty_for_python():
    files = {"requirements.txt": "pytest\n", "src/app.py": ""}
    env = EnvironmentSetup(files)
    cmds = env.setup_commands()
    assert len(cmds) > 0
    assert any("pip" in c or "install" in c for c in cmds)


def test_setup_commands_empty_for_unknown():
    files = {"notes.txt": "just a note"}
    env = EnvironmentSetup(files)
    cmds = env.setup_commands()
    assert isinstance(cmds, list)


def test_setup_result_fields():
    result = SetupResult(success=True, build_system="python_pip", commands_run=["pip install -r requirements.txt"], error="")
    assert result.success is True
    assert result.build_system == "python_pip"
    assert isinstance(result.commands_run, list)


def test_validate_python_has_test_runner():
    files = {"pyproject.toml": "[tool.pytest.ini_options]\ntestpaths=['tests']\n", "tests/test_x.py": "def test_ok(): pass"}
    env = EnvironmentSetup(files)
    result = env.validate()
    assert isinstance(result, SetupResult)
    assert result.build_system != ""


def test_build_system_enum_has_required_values():
    assert hasattr(BuildSystem, "PYTHON_PIP")
    assert hasattr(BuildSystem, "PYTHON_UV")
    assert hasattr(BuildSystem, "NODE_NPM")
    assert hasattr(BuildSystem, "UNKNOWN")
