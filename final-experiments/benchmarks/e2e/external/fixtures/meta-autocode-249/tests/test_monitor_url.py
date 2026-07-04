import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from monitor_url import get_monitor_url

# PASS with bug (no 'url' key or 'url': '' — both return '')
def test_empty():
    assert get_monitor_url({}) == ''

def test_name_only():
    assert get_monitor_url({'name': 'API check'}) == ''

def test_type_only():
    assert get_monitor_url({'type': 'http'}) == ''

def test_url_empty():
    assert get_monitor_url({'url': ''}) == ''

# FAIL with bug (has non-empty 'url' — bug reads 'endpoint', returns '')
def test_https_url():
    assert get_monitor_url({'url': 'https://example.com'}) == 'https://example.com'

def test_http_url_with_type():
    assert get_monitor_url({'url': 'http://api.local', 'type': 'http'}) == 'http://api.local'

def test_another_https():
    assert get_monitor_url({'url': 'https://test.org'}) == 'https://test.org'
