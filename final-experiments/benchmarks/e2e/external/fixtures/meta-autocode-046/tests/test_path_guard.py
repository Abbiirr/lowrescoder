import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from path_guard import is_safe_path

def test_traversal_basic():
    assert is_safe_path('../etc/passwd') is False

def test_traversal_embedded():
    assert is_safe_path('a/../b') is False

def test_normal_path():
    assert is_safe_path('src/main.py') is True

def test_empty_path():
    assert is_safe_path('') is True

def test_double_dot_in_filename():
    # BUG: 'file..txt' contains '..' substring → incorrectly blocked
    assert is_safe_path('file..txt') is True

def test_double_dot_in_extension():
    # BUG: 'app..min.js' blocked despite having no traversal
    assert is_safe_path('app..min.js') is True

def test_ellipsis_in_dirname():
    # BUG: 'src/helpers..utils/main.py' has '..' but is NOT a traversal component
    assert is_safe_path('src/helpers..utils/main.py') is True
