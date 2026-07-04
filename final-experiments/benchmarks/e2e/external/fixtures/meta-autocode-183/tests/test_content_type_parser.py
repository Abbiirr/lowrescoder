import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from content_type_parser import parse_content_type

# PASS (no trailing space before ';' — bug and fix agree)

def test_plain_type():
    assert parse_content_type('application/json') == 'application/json'

def test_type_with_param():
    assert parse_content_type('text/html; charset=utf-8') == 'text/html'

def test_leading_space():
    assert parse_content_type(' application/json') == 'application/json'

def test_no_space_before_param():
    assert parse_content_type('image/png;quality=80') == 'image/png'

# FAIL (space before ';' — lstrip leaves trailing space, strip removes it)

def test_trailing_space_no_params():
    assert parse_content_type('application/json ') == 'application/json'  # bug: 'application/json '

def test_space_before_semicolon():
    assert parse_content_type('text/html ;charset=utf-8') == 'text/html'  # bug: 'text/html '

def test_multipart_space_before_semicolon():
    assert parse_content_type('multipart/form-data ;boundary=abc') == 'multipart/form-data'  # bug: '...-data '
