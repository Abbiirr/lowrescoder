import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from url_builder import build_url

# PASS (no trailing slash on base — bug and fix produce same result)

def test_simple():
    assert build_url('http://api.com', '/users') == 'http://api.com/users'

def test_with_path():
    assert build_url('http://api.com', '/users/1') == 'http://api.com/users/1'

def test_versioned_base():
    assert build_url('http://api.com/v1', '/items') == 'http://api.com/v1/items'

def test_slash_path():
    assert build_url('http://api.com/v2', '/') == 'http://api.com/v2/'

# FAIL (trailing slash on base + leading slash on path — bug creates double slash)

def test_trailing_slash_base():
    assert build_url('http://api.com/', '/users') == 'http://api.com/users'  # bug: '//users'

def test_versioned_trailing():
    assert build_url('http://api.com/v1/', '/items') == 'http://api.com/v1/items'  # bug: '//items'

def test_cdn_trailing():
    assert build_url('https://cdn.example.com/', '/assets/logo.png') == 'https://cdn.example.com/assets/logo.png'
