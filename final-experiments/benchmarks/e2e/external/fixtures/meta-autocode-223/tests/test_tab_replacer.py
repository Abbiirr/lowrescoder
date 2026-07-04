import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tab_replacer import replace_tabs

# PASS (no tabs present — both bug and fix return the same string)

def test_no_tabs():
    assert replace_tabs('hello world') == 'hello world'

def test_empty():
    assert replace_tabs('') == ''

def test_newline_no_tab():
    assert replace_tabs('line1\nline2') == 'line1\nline2'

def test_spaces_untouched():
    assert replace_tabs('a  b') == 'a  b'

# FAIL (tabs present with default width=4 — bug gives 1 space, fix gives 4)

def test_tab_at_start():
    assert replace_tabs('\thello') == '    hello'  # bug: ' hello'

def test_tab_between_words():
    assert replace_tabs('a\tb') == 'a    b'  # bug: 'a b'

def test_two_tabs():
    assert replace_tabs('\t\t') == '        '  # bug: '  ' (2 spaces)
