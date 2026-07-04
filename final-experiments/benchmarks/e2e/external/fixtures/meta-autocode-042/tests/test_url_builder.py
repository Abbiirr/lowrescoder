import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from url_builder import build_url

def test_no_trailing_no_leading():
    assert build_url('http://api.example.com', 'users') == 'http://api.example.com/users'

def test_trailing_slash_no_leading():
    assert build_url('http://api.example.com/', 'users') == 'http://api.example.com/users'

def test_nested_path_no_leading():
    assert build_url('http://api.example.com/', 'v1/users') == 'http://api.example.com/v1/users'

def test_multiple_trailing_slashes():
    assert build_url('http://api.example.com///', 'items') == 'http://api.example.com/items'

def test_path_with_leading_slash():
    # BUG: 'http://api.example.com' + '/' + '/users' = '//users' segment
    assert build_url('http://api.example.com', '/users') == 'http://api.example.com/users'

def test_both_trailing_and_leading_slash():
    # BUG: 'http://api.example.com/' + '/' + '/v1/items' = '//v1/items' segment
    assert build_url('http://api.example.com/', '/v1/items') == 'http://api.example.com/v1/items'

def test_deep_path_with_leading_slash():
    # BUG: double slash in result
    assert build_url('http://api.example.com/', '/api/v2/search') == 'http://api.example.com/api/v2/search'
