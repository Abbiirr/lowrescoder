"""Tests for file_detector — inspired by sharkdp/bat file-type detection.

bat detects language from file extension. A common harness-bench v2 pattern:
split('.')[1] works for single-dot names but silently returns the wrong segment
for multi-dot names like 'app.test.ts' or 'webpack.config.js'.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_simple_python():
    from file_detector import detect_language
    assert detect_language("script.py") == "python"


def test_simple_json():
    from file_detector import detect_language
    assert detect_language("data.json") == "json"


def test_multi_dot_json():
    from file_detector import detect_language
    # split('.')[1] returns "test", not "json"
    result = detect_language("config.test.json")
    assert result == "json", f"expected 'json', got '{result}'"


def test_multi_dot_js():
    from file_detector import detect_language
    # split('.')[1] returns "min", not "javascript"
    result = detect_language("app.min.js")
    assert result == "javascript", f"expected 'javascript', got '{result}'"


def test_multi_dot_ts():
    from file_detector import detect_language
    result = detect_language("main.spec.ts")
    assert result == "typescript", f"expected 'typescript', got '{result}'"


def test_no_extension():
    from file_detector import detect_language
    assert detect_language("Makefile") == "text"
    assert detect_language("README") == "text"


def test_unknown_extension():
    from file_detector import detect_language
    assert detect_language("notes.txt") == "text"
