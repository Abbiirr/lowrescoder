import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from asset_resolver import get_extension

# PASS (bug and fix agree)

def test_js_extension():
    assert get_extension('app.js') == 'js'

def test_css_extension():
    assert get_extension('styles.min.css') == 'css'  # rsplit maxsplit=1 → 'css'

def test_ts_extension():
    assert get_extension('index.ts') == 'ts'

def test_dotfile():
    assert get_extension('.hidden') == 'hidden'  # both: rsplit('.', 1) = ['', 'hidden']

# FAIL (no-extension files)

def test_no_extension_makefile():
    assert get_extension('Makefile') == ''  # bug: returns 'Makefile'

def test_no_extension_in_path():
    assert get_extension('dist/bundle') == ''  # bug: returns 'dist/bundle'

def test_no_extension_nested():
    assert get_extension('src/utils/helpers') == ''  # bug: returns 'src/utils/helpers'
