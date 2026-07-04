import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from url_utils import is_secure_url

# PASS (both startswith('https') and startswith('https://') agree)

def test_valid_https():
    assert is_secure_url('https://example.com') == True

def test_valid_https_path():
    assert is_secure_url('https://api.github.com/repos') == True

def test_http_is_not_secure():
    assert is_secure_url('http://example.com') == False

def test_ftp_is_not_secure():
    assert is_secure_url('ftp://files.example.com') == False

# FAIL (starts with 'https' but not 'https://' — bug says True, correct is False)

def test_https_no_scheme_separator():
    assert is_secure_url('httpsexample.com') == False  # bug: True

def test_https_no_slashes():
    assert is_secure_url('httpsfoo') == False  # bug: True

def test_https_bare_prefix():
    assert is_secure_url('https') == False  # bug: True
