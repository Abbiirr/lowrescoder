import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from module_checker import is_js_file

# PASS (.js files and non-JS files — bug and fix agree)

def test_js_extension():
    assert is_js_file('app.js') == True

def test_js_utils():
    assert is_js_file('utils.js') == True

def test_css_not_js():
    assert is_js_file('style.css') == False

def test_ts_not_js():
    assert is_js_file('index.ts') == False

# FAIL (.mjs and .cjs — bug returns False, fix returns True)

def test_mjs_extension():
    assert is_js_file('module.mjs') == True  # bug: False

def test_cjs_extension():
    assert is_js_file('common.cjs') == True  # bug: False

def test_vendor_mjs():
    assert is_js_file('vendor.mjs') == True  # bug: False
