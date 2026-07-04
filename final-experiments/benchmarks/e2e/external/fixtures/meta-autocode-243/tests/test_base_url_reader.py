import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from base_url_reader import get_base_url

# PASS with bug (no 'base' key present — both return default '/')
def test_empty_config():
    assert get_base_url({}) == '/'

def test_irrelevant_key():
    assert get_base_url({'root': './src'}) == '/'

def test_port_only():
    assert get_base_url({'port': 3000}) == '/'

def test_plugins_key():
    assert get_base_url({'plugins': []}) == '/'

# FAIL with bug (has 'base' key — bug reads 'base_url', returns default)
def test_base_app():
    assert get_base_url({'base': '/app'}) == '/app'

def test_base_subdir():
    assert get_base_url({'base': '/subdir', 'port': 3000}) == '/subdir'

def test_base_relative():
    assert get_base_url({'base': './'}) == './'
