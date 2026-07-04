import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from import_classifier import is_bare_import

# PASS (package names and './'-relative paths — bug and fix agree)

def test_npm_package():
    assert is_bare_import('lodash') == True

def test_scoped_package():
    assert is_bare_import('@scope/pkg') == True

def test_current_relative():
    assert is_bare_import('./utils') == False

def test_package_subpath():
    assert is_bare_import('react/hooks') == True

# FAIL ('../' relative paths — bug returns True, fix returns False)

def test_parent_relative():
    assert is_bare_import('../components/Button') == False  # bug: True

def test_parent_utils():
    assert is_bare_import('../utils') == False  # bug: True

def test_grandparent_relative():
    assert is_bare_import('../../shared') == False  # bug: True
