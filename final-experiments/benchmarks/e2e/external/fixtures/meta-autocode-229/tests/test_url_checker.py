import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from url_checker import is_absolute_url

# PASS (http:// URLs or clearly relative — both bug and fix agree)

def test_http():
    assert is_absolute_url('http://example.com') is True

def test_http_local():
    assert is_absolute_url('http://localhost:3000') is True

def test_relative_path():
    assert is_absolute_url('/api/users') is False

def test_relative_no_slash():
    assert is_absolute_url('relative/path') is False

# FAIL (https:// URLs — bug returns False, fix returns True)

def test_https_basic():
    assert is_absolute_url('https://example.com') is True  # bug: False

def test_https_api():
    assert is_absolute_url('https://api.github.com/v1') is True  # bug: False

def test_https_local():
    assert is_absolute_url('https://localhost:4000') is True  # bug: False
