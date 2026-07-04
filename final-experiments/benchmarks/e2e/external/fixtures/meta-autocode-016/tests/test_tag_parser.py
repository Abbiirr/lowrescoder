"""Tests for tag_parser — inspired by usememos/memos hashtag extraction.

memos parses inline #tags from note content. Trailing punctuation after a tag
(e.g. "#bug." at end of a sentence) should not be part of the tag name.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_simple_tag():
    from tag_parser import extract_tags
    assert extract_tags("#hello world") == ["hello"]


def test_multiple_tags():
    from tag_parser import extract_tags
    assert extract_tags("#python #testing is fun") == ["python", "testing"]


def test_tag_trailing_period():
    from tag_parser import extract_tags
    result = extract_tags("Fixed #bug.")
    assert result == ["bug"], f"expected ['bug'], got {result}"


def test_tag_trailing_comma():
    from tag_parser import extract_tags
    result = extract_tags("Use #python, #go for this")
    assert result == ["python", "go"], f"got {result}"


def test_tag_trailing_exclamation():
    from tag_parser import extract_tags
    result = extract_tags("Great #feature!")
    assert result == ["feature"], f"got {result}"


def test_no_tags():
    from tag_parser import extract_tags
    assert extract_tags("no tags here") == []


def test_hash_only_ignored():
    from tag_parser import extract_tags
    assert extract_tags("# not a tag") == []
