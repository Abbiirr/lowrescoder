import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from import_resolver import resolve_import

# PASS with bug (short paths that ARE substrings of module names)

def test_no_paths():
    assert resolve_import('mymodule', []) is None

def test_path_found_as_substring():
    # 'src' is in 'src/mymodule' — bug and fix both find it
    result = resolve_import('src/mymodule', ['src', 'lib'])
    assert result == 'src'

def test_first_matching_path():
    result = resolve_import('lib/utils', ['src', 'lib'])
    assert result == 'lib'  # bug: 'lib' in 'lib/utils' → True ✓

def test_no_match_returns_none():
    result = resolve_import('vendor/pkg', ['src', 'lib'])
    assert result is None  # bug: neither 'src' nor 'lib' in 'vendor/pkg' → None ✓

# FAIL with bug (module_name should be searched in path, not path in module_name)

def test_module_in_path():
    # Correct: module_name 'utils' in path '/home/user/src/utils' → True
    # Bug: path '/home/user/src/utils' in module_name 'utils' → False
    result = resolve_import('utils', ['/home/user/src/utils', '/home/user/lib'])
    assert result == '/home/user/src/utils'

def test_exact_module_match():
    # path='/packages/lodash', module_name='lodash'
    # Bug: '/packages/lodash' in 'lodash' → False
    # Fix: 'lodash' in '/packages/lodash' → True
    result = resolve_import('lodash', ['/packages/lodash'])
    assert result == '/packages/lodash'

def test_multiple_paths_correct_one():
    result = resolve_import('react', ['/node_modules/react', '/node_modules/vue'])
    assert result == '/node_modules/react'  # bug: '/node_modules/react' in 'react' → False
