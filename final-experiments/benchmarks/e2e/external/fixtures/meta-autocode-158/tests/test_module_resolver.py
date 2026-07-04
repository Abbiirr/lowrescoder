import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from module_resolver import is_relative_path

# PASS (both agree)

def test_current_dir_relative():
    assert is_relative_path('./foo') == True

def test_nested_relative():
    assert is_relative_path('./components/bar.js') == True

def test_absolute_path():
    assert is_relative_path('/absolute/path') == False

def test_bare_module():
    assert is_relative_path('react') == False

# FAIL (parent dir — bug: False, fix: True)

def test_parent_dir():
    assert is_relative_path('../parent') == True  # bug: False

def test_grandparent():
    assert is_relative_path('../../grandparent') == True  # bug: False

def test_sibling():
    assert is_relative_path('../sibling/file.js') == True  # bug: False
