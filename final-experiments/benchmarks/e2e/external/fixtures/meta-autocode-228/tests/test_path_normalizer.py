import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from path_normalizer import normalize_path

# PASS (path doesn't start with '/' — both bug and fix prepend one '/')

def test_bare_path():
    assert normalize_path('users') == '/users'

def test_nested_path():
    assert normalize_path('api/v1') == '/api/v1'

def test_empty():
    assert normalize_path('') == '/'

def test_deep_path():
    assert normalize_path('a/b/c') == '/a/b/c'

# FAIL (path already starts with '/' — bug creates '//', fix preserves single '/')

def test_already_slash():
    assert normalize_path('/users') == '/users'  # bug: '//users'

def test_already_nested():
    assert normalize_path('/api/v1') == '/api/v1'  # bug: '//api/v1'

def test_just_slash():
    assert normalize_path('/') == '/'  # bug: '//'
