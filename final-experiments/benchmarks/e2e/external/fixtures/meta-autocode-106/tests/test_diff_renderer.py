import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from diff_renderer import render_diff_line

# PASS with bug

def test_added_line_prefix():
    assert render_diff_line('hello', 'added') == '+hello'

def test_removed_line_prefix():
    assert render_diff_line('world', 'removed') == '-world'

def test_result_is_string():
    assert isinstance(render_diff_line('x', 'context'), str)

def test_added_starts_with_plus():
    assert render_diff_line('foo', 'added').startswith('+')

# FAIL with bug (context lines need space prefix)

def test_context_line_has_space_prefix():
    assert render_diff_line('context', 'context') == ' context'  # bug: 'context'

def test_context_line_length():
    result = render_diff_line('abc', 'context')
    assert len(result) == 4  # bug: 3 (no space added)

def test_unchanged_line_prefix():
    result = render_diff_line('foo bar', 'unchanged')
    assert result == ' foo bar'  # bug: 'foo bar'
