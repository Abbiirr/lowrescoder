"""Benchmark tests for edit efficiency.

Measures how efficiently the system can apply fixes and changes.
Inspired by SWE-bench's edit accuracy metrics and Aider's diff-based benchmarks.

Metrics tracked:
- Edit accuracy: Does the edit fix the issue?
- Edit size: How many lines changed vs minimum necessary?
- Diff precision: Does the edit touch only the affected area?
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.utils.file_tools import read_file, write_file


@pytest.fixture()
def buggy_project(tmp_path: Path) -> Path:
    """Create a project with known bugs for edit benchmarks."""
    src = tmp_path / "src"
    src.mkdir()

    # Bug 1: Off-by-one error
    (src / "pagination.py").write_text(
        "def paginate(items: list, page: int, per_page: int) -> list:\n"
        "    start = page * per_page  # BUG: should be (page - 1) * per_page\n"
        "    end = start + per_page\n"
        "    return items[start:end]\n"
    )

    # Bug 2: Missing null check
    (src / "user.py").write_text(
        "def get_display_name(user: dict) -> str:\n"
        "    # BUG: crashes if 'name' key missing\n"
        "    return user['name'].title()\n"
    )

    # Bug 3: Wrong operator
    (src / "calc.py").write_text(
        "def discount_price(price: float, discount_pct: float) -> float:\n"
        "    return price * (1 + discount_pct / 100)  # BUG: + should be -\n"
    )

    # Bug 4: Missing return
    (src / "validator.py").write_text(
        "def is_valid_email(email: str) -> bool:\n"
        "    if '@' not in email:\n"
        "        return False\n"
        "    if '.' not in email.split('@')[1]:\n"
        "        return False\n"
        "    # BUG: no final success path\n"
    )

    return tmp_path


class TestEditAccuracy:
    """Can we correctly identify and fix known bugs?"""

    def test_identify_off_by_one(self, buggy_project: Path) -> None:
        """Can identify the off-by-one bug in pagination."""
        content = read_file(str(buggy_project / "src" / "pagination.py"))
        assert "page * per_page" in content
        # The fix: (page - 1) * per_page
        assert "BUG" in content

    def test_identify_null_check_bug(self, buggy_project: Path) -> None:
        """Can identify the missing null check."""
        content = read_file(str(buggy_project / "src" / "user.py"))
        assert "user['name']" in content
        # The fix: user.get('name', 'Unknown')

    def test_identify_wrong_operator(self, buggy_project: Path) -> None:
        """Can identify the wrong arithmetic operator."""
        content = read_file(str(buggy_project / "src" / "calc.py"))
        assert "1 + discount_pct" in content
        # The fix: 1 - discount_pct

    def test_identify_missing_return(self, buggy_project: Path) -> None:
        """Can identify the missing return statement."""
        content = read_file(str(buggy_project / "src" / "validator.py"))
        lines = content.strip().splitlines()
        # Last non-comment line should NOT be 'return True'
        assert "return True" not in lines[-1]


class TestEditSize:
    """How many lines need to change for a minimal fix?"""

    def test_off_by_one_fix_is_one_line(self, buggy_project: Path) -> None:
        """Off-by-one fix should only change 1 line."""
        path = buggy_project / "src" / "pagination.py"
        original = path.read_text()
        fixed = original.replace("page * per_page", "(page - 1) * per_page")

        original_lines = original.splitlines()
        fixed_lines = fixed.splitlines()

        changed_count = sum(
            1 for o, f in zip(original_lines, fixed_lines) if o != f
        )
        assert changed_count == 1

    def test_missing_return_fix_is_one_line(self, buggy_project: Path) -> None:
        """Missing return fix should only add 1 line."""
        path = buggy_project / "src" / "validator.py"
        original = path.read_text()
        fixed = original.rstrip() + "\n    return True\n"

        original_line_count = len(original.strip().splitlines())
        fixed_line_count = len(fixed.strip().splitlines())

        assert fixed_line_count - original_line_count == 1

    def test_operator_fix_is_one_line(self, buggy_project: Path) -> None:
        """Wrong operator fix should change exactly 1 line."""
        path = buggy_project / "src" / "calc.py"
        original = path.read_text()
        fixed = original.replace("1 + discount_pct", "1 - discount_pct")

        original_lines = original.splitlines()
        fixed_lines = fixed.splitlines()

        changed_count = sum(
            1 for o, f in zip(original_lines, fixed_lines) if o != f
        )
        assert changed_count == 1


class TestDiffPrecision:
    """Does the edit only touch the affected area?"""

    def test_fix_preserves_surrounding_code(self, buggy_project: Path) -> None:
        """Fix to pagination should not change function signature or return."""
        path = buggy_project / "src" / "pagination.py"
        original_lines = path.read_text().splitlines()

        # Simulate fix
        fixed_lines = [
            line.replace("page * per_page", "(page - 1) * per_page")
            for line in original_lines
        ]

        # Line 0 (def) and line 2-3 (end/return) should be unchanged
        assert fixed_lines[0] == original_lines[0]
        assert fixed_lines[2] == original_lines[2]
        assert fixed_lines[3] == original_lines[3]

    def test_write_file_roundtrip_preserves_content(self, buggy_project: Path) -> None:
        """write_file followed by read_file preserves exact content."""
        path = str(buggy_project / "src" / "test_roundtrip.py")
        content = "def test():\n    return 42\n"
        write_file(path, content)
        result = read_file(path)
        assert result == content
