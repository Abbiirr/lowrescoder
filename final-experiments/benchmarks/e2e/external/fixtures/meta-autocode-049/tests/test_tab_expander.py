import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tab_expander import expand_tabs

# --- PASS with bug (tab_width=4 matches hard-coded behaviour, or no tabs) ---

def test_tab_width_4_single():
    assert expand_tabs('hello\tworld', 4) == 'hello    world'

def test_tab_width_4_multiple():
    assert expand_tabs('a\tb\tc', 4) == 'a    b    c'

def test_no_tabs():
    assert expand_tabs('hello world', 8) == 'hello world'

def test_empty_string():
    assert expand_tabs('', 2) == ''

# --- FAIL with bug (non-4 widths produce wrong output) ---

def test_tab_width_2():
    assert expand_tabs('hello\tworld', 2) == 'hello  world'

def test_tab_width_8():
    assert expand_tabs('hello\tworld', 8) == 'hello        world'

def test_tab_width_1():
    assert expand_tabs('a\tb', 1) == 'a b'
