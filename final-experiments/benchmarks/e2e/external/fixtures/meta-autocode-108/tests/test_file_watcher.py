import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from file_watcher import get_watched_extensions

# PASS with bug (no dot stripping needed for these tests)

def test_empty_config():
    assert get_watched_extensions({}) == set()

def test_returns_set():
    assert isinstance(get_watched_extensions({'watch_extensions': ['py']}), set)

def test_no_duplicates():
    result = get_watched_extensions({'watch_extensions': ['py', 'py', 'js']})
    assert len(result) == 2

def test_multiple_extensions():
    result = get_watched_extensions({'watch_extensions': ['py', 'js', 'ts']})
    assert 'py' in result

# FAIL with bug (dot-prefixed extensions not normalized)

def test_dot_prefix_stripped():
    result = get_watched_extensions({'watch_extensions': ['.py', '.js']})
    assert 'py' in result  # bug: '.py' in result, not 'py'

def test_mixed_dot_no_dot_normalized():
    result = get_watched_extensions({'watch_extensions': ['.py', 'js']})
    assert result == {'py', 'js'}  # bug: {'.py', 'js'}

def test_dot_extension_not_in_result():
    result = get_watched_extensions({'watch_extensions': ['.ts']})
    assert '.ts' not in result  # bug: '.ts' IS in result
