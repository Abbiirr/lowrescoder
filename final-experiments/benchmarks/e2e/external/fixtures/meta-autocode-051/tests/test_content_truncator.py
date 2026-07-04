import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from content_truncator import truncate_content

# --- PASS with bug (no truncation occurs — bug and fix agree) ---

def test_short_content_unchanged():
    assert truncate_content('hello', 10) == 'hello'

def test_exact_max_length_unchanged():
    assert truncate_content('hello', 5) == 'hello'

def test_empty_content():
    assert truncate_content('', 10) == ''

def test_one_char_within_limit():
    assert truncate_content('x', 5) == 'x'

# --- FAIL with bug (truncation occurs but ellipsis is missing) ---

def test_long_content_gets_ellipsis():
    result = truncate_content('hello world this is long', 5)
    assert result == 'hello...'

def test_truncation_at_word_boundary():
    result = truncate_content('abcdefghij', 3)
    assert result == 'abc...'

def test_truncation_preserves_prefix_length():
    content = 'x' * 100
    result = truncate_content(content, 20)
    assert result == 'x' * 20 + '...'
