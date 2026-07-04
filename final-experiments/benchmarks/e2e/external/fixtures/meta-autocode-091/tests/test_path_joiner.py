import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from path_joiner import join_url_path

# PASS with bug (path already has leading slash)

def test_leading_slash_path():
    assert join_url_path('http://example.com', '/api') == 'http://example.com/api'

def test_trailing_slash_base_with_slash_path():
    assert join_url_path('http://example.com/', '/api') == 'http://example.com/api'

def test_empty_path():
    assert join_url_path('http://example.com/', '') == 'http://example.com'

def test_root_slash_path():
    assert join_url_path('http://host', '/') == 'http://host/'

# FAIL with bug (path has no leading slash — missing separator)

def test_no_leading_slash_path():
    result = join_url_path('http://example.com', 'api')
    assert result == 'http://example.com/api'  # bug: 'http://example.comapi'

def test_no_leading_slash_with_trailing_base():
    result = join_url_path('http://example.com/', 'users')
    assert result == 'http://example.com/users'  # bug: 'http://example.comusers'

def test_deep_path_no_leading_slash():
    result = join_url_path('http://host', 'v1/items')
    assert result == 'http://host/v1/items'  # bug: 'http://hostv1/items'
