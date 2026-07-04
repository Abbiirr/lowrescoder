import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from plugin_registry import register_plugin, get_plugin, clear_registry

def setup_function():
    clear_registry()

# PASS with bug (exact case lookup)

def test_exact_case_lookup():
    register_plugin('MyPlugin', lambda: 'result')
    assert get_plugin('MyPlugin') is not None

def test_missing_plugin_returns_none():
    assert get_plugin('nonexistent') is None

def test_register_and_retrieve_lower():
    register_plugin('myplugin', lambda: 42)
    assert get_plugin('myplugin') is not None

def test_multiple_plugins():
    register_plugin('alpha', lambda: 1)
    register_plugin('beta', lambda: 2)
    assert get_plugin('alpha') is not None
    assert get_plugin('beta') is not None

# FAIL with bug (case-insensitive lookup required)

def test_lookup_different_case():
    register_plugin('MyPlugin', lambda: 'ok')
    assert get_plugin('myplugin') is not None  # bug: None

def test_lookup_upper_case():
    register_plugin('formatter', lambda: True)
    assert get_plugin('FORMATTER') is not None  # bug: None

def test_lookup_mixed_case():
    register_plugin('DataLoader', lambda: [])
    assert get_plugin('dataloader') is not None  # bug: None
