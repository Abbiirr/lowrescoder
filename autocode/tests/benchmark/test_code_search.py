"""Benchmark tests for code search accuracy and efficiency.

These tests measure how accurately and quickly the search_text tool
can find specific code patterns in a codebase. Inspired by SWE-bench's
localization metrics.

Metrics tracked:
- Accuracy: Does the search find the correct file and line?
- Precision: What fraction of results are relevant?
- Performance: How fast is the search?
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from autocode.agent.tools import _handle_search_text, _search_with_python


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    """Create a realistic multi-file project for search benchmarks."""
    # Models
    models = tmp_path / "src" / "models"
    models.mkdir(parents=True)
    (models / "__init__.py").write_text("from .user import User\nfrom .post import Post\n")
    (models / "user.py").write_text(
        "class User:\n"
        "    def __init__(self, name: str, email: str) -> None:\n"
        "        self.name = name\n"
        "        self.email = email\n"
        "        self.is_active = True\n"
        "\n"
        "    def deactivate(self) -> None:\n"
        "        self.is_active = False\n"
        "\n"
        "    def validate_email(self) -> bool:\n"
        "        return '@' in self.email\n"
    )
    (models / "post.py").write_text(
        "from datetime import datetime\n"
        "\n"
        "class Post:\n"
        "    def __init__(self, title: str, author: str) -> None:\n"
        "        self.title = title\n"
        "        self.author = author\n"
        "        self.created_at = datetime.now()\n"
        "\n"
        "    def publish(self) -> None:\n"
        "        self.is_published = True\n"
    )

    # Services
    services = tmp_path / "src" / "services"
    services.mkdir(parents=True)
    (services / "__init__.py").write_text("")
    (services / "auth.py").write_text(
        "import hashlib\n"
        "\n"
        "def hash_password(password: str) -> str:\n"
        "    return hashlib.sha256(password.encode()).hexdigest()\n"
        "\n"
        "def verify_password(password: str, hashed: str) -> bool:\n"
        "    return hash_password(password) == hashed\n"
        "\n"
        "def login(email: str, password: str) -> bool:\n"
        "    # BUG: does not check if user is active\n"
        "    user = lookup_user(email)\n"
        "    if user is None:\n"
        "        return False\n"
        "    return verify_password(password, user.password_hash)\n"
        "\n"
        "def lookup_user(email: str):\n"
        "    return None  # stub\n"
    )
    (services / "notification.py").write_text(
        "def send_email(to: str, subject: str, body: str) -> bool:\n"
        "    # TODO: implement actual email sending\n"
        "    print(f'Sending email to {to}: {subject}')\n"
        "    return True\n"
        "\n"
        "def send_push(user_id: str, message: str) -> bool:\n"
        "    return False  # not implemented\n"
    )

    # Utils
    utils = tmp_path / "src" / "utils"
    utils.mkdir(parents=True)
    (utils / "__init__.py").write_text("")
    (utils / "helpers.py").write_text(
        "def format_name(first: str, last: str) -> str:\n"
        "    return f'{first} {last}'\n"
        "\n"
        "def parse_config(path: str) -> dict:\n"
        "    import json\n"
        "    with open(path) as f:\n"
        "        return json.load(f)\n"
    )

    # Tests
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_auth.py").write_text(
        "from src.services.auth import hash_password, verify_password\n"
        "\n"
        "def test_hash_password():\n"
        "    h = hash_password('secret')\n"
        "    assert len(h) == 64\n"
        "\n"
        "def test_verify_password():\n"
        "    h = hash_password('secret')\n"
        "    assert verify_password('secret', h)\n"
        "    assert not verify_password('wrong', h)\n"
    )

    return tmp_path


class TestSearchAccuracy:
    """Does search_text find the correct file and line?"""

    def test_find_class_definition(self, sample_project: Path) -> None:
        """Can find a class definition by name."""
        result = _handle_search_text("class User", str(sample_project))
        assert "user.py" in result
        assert "class User" in result

    def test_find_function_definition(self, sample_project: Path) -> None:
        """Can find a function definition by name."""
        result = _handle_search_text("def login", str(sample_project))
        assert "auth.py" in result

    def test_find_bug_comment(self, sample_project: Path) -> None:
        """Can find a known bug by its comment."""
        result = _handle_search_text("BUG:", str(sample_project))
        assert "auth.py" in result
        assert "does not check" in result

    def test_find_todo_comment(self, sample_project: Path) -> None:
        """Can find TODO comments across the project."""
        result = _handle_search_text("TODO:", str(sample_project))
        assert "notification.py" in result

    def test_find_import_usage(self, sample_project: Path) -> None:
        """Can find where a module is imported."""
        result = _handle_search_text("from.*auth.*import", str(sample_project))
        assert "test_auth.py" in result

    def test_find_method_call(self, sample_project: Path) -> None:
        """Can find where a method is called."""
        result = _handle_search_text("hash_password", str(sample_project))
        # Should appear in both auth.py and test_auth.py
        assert "auth.py" in result

    def test_find_with_glob_filter(self, sample_project: Path) -> None:
        """Glob filter restricts search to matching files."""
        result = _handle_search_text(
            "hash_password", str(sample_project), glob_pattern="**/*.py",
        )
        assert "hash_password" in result


class TestSearchPrecision:
    """What fraction of results are relevant?"""

    def test_exact_class_match_precision(self, sample_project: Path) -> None:
        """Searching for 'class Post' should not return 'class User'."""
        result = _handle_search_text("class Post", str(sample_project))
        lines = result.strip().splitlines()
        for line in lines:
            assert "class Post" in line or "No matches" in line

    def test_specific_method_precision(self, sample_project: Path) -> None:
        """Searching 'def deactivate' finds only the one method."""
        result = _handle_search_text("def deactivate", str(sample_project))
        lines = [ln for ln in result.strip().splitlines() if "def deactivate" in ln]
        assert len(lines) == 1

    def test_no_false_positives(self, sample_project: Path) -> None:
        """Searching for a nonexistent pattern returns no matches."""
        result = _handle_search_text(
            "class NonExistentWidget", str(sample_project),
        )
        assert "No matches" in result


class TestSearchPerformance:
    """How fast does search complete?"""

    def _create_large_project(self, tmp_path: Path, num_files: int) -> Path:
        """Create a large project with many files."""
        for i in range(num_files):
            pkg = tmp_path / f"pkg{i % 10}"
            pkg.mkdir(exist_ok=True)
            (pkg / f"module_{i}.py").write_text(
                f"class Class{i}:\n"
                f"    def method_{i}(self):\n"
                f"        return {i}\n"
                f"\n"
                f"def helper_{i}():\n"
                f"    return Class{i}().method_{i}()\n"
            )
        # Plant a needle
        (tmp_path / "pkg0" / "needle.py").write_text(
            "def find_this_unique_function():\n"
            "    return 'found it'\n"
        )
        return tmp_path

    def test_search_100_files_under_5s(self, tmp_path: Path) -> None:
        """Search across 100 files completes in under 5 seconds."""
        project = self._create_large_project(tmp_path, 100)
        start = time.monotonic()
        result = _search_with_python(
            "find_this_unique_function", str(project), "**/*.py", 50,
        )
        duration = time.monotonic() - start
        assert "needle.py" in result
        assert duration < 5.0

    def test_search_250_files_under_5s(self, tmp_path: Path) -> None:
        """Search across 250 files completes in under 5 seconds."""
        project = self._create_large_project(tmp_path, 250)
        start = time.monotonic()
        result = _search_with_python(
            "find_this_unique_function", str(project), "**/*.py", 50,
        )
        duration = time.monotonic() - start
        assert "needle.py" in result
        assert duration < 5.0

    def test_fallback_chain_returns_correct_result(self, tmp_path: Path) -> None:
        """Full fallback chain (rg > grep > python) returns correct result."""
        project = self._create_large_project(tmp_path, 50)
        result = _handle_search_text(
            "find_this_unique_function", str(project),
        )
        assert "needle.py" in result
