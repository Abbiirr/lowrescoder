import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from syntax_detector import should_highlight

# PASS (lowercase extensions and non-highlight files — bug and fix agree)

def test_python_file():
    assert should_highlight('script.py') == True

def test_js_file():
    assert should_highlight('app.js') == True

def test_csv_not_highlighted():
    assert should_highlight('data.csv') == False

def test_no_extension():
    assert should_highlight('Makefile') == False

# FAIL (uppercase extensions — bug returns False, fix returns True)

def test_uppercase_py():
    assert should_highlight('script.PY') == True  # bug: False (.PY not in set)

def test_uppercase_js():
    assert should_highlight('app.JS') == True  # bug: False

def test_uppercase_css():
    assert should_highlight('styles.CSS') == True  # bug: False
