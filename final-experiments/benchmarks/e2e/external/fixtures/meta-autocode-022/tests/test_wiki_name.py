"""Tests for wiki_name — inspired by go-gitea/gitea wiki filename sanitization.

gitea converts wiki page titles to filenames. Multiple consecutive spaces in a
title should collapse to a single underscore, and leading/trailing whitespace
should be stripped. The bug uses str.replace(" ", "_") which doubles up on
consecutive spaces instead of collapsing them.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_simple_word():
    from wiki_name import sanitize_wiki_name
    assert sanitize_wiki_name("hello") == "hello"


def test_single_space():
    from wiki_name import sanitize_wiki_name
    assert sanitize_wiki_name("hello world") == "hello_world"


def test_numbers_and_letters():
    from wiki_name import sanitize_wiki_name
    assert sanitize_wiki_name("page123") == "page123"


def test_already_underscored():
    from wiki_name import sanitize_wiki_name
    assert sanitize_wiki_name("valid_name") == "valid_name"


def test_double_space_collapses():
    from wiki_name import sanitize_wiki_name
    # Bug: "my  page" → "my__page"; expected: "my_page"
    result = sanitize_wiki_name("my  page")
    assert result == "my_page", f"expected 'my_page', got '{result}'"


def test_leading_space_stripped():
    from wiki_name import sanitize_wiki_name
    # Bug: "  leading" → "__leading"; expected: "leading"
    result = sanitize_wiki_name("  leading")
    assert result == "leading", f"expected 'leading', got '{result}'"


def test_triple_space_collapses():
    from wiki_name import sanitize_wiki_name
    # Bug: "a   b" → "a___b"; expected: "a_b"
    result = sanitize_wiki_name("a   b")
    assert result == "a_b", f"expected 'a_b', got '{result}'"
