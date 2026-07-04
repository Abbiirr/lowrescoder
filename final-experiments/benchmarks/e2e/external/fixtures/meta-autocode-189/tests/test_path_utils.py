import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from path_utils import remove_extension

# PASS (single dot or no dot — bug and fix agree)

def test_js_file():
    assert remove_extension('app.js') == 'app'

def test_css_file():
    assert remove_extension('style.css') == 'style'

def test_no_extension():
    assert remove_extension('README') == 'README'

def test_ts_file():
    assert remove_extension('index.ts') == 'index'

# FAIL (multiple dots — bug removes too much)

def test_test_file():
    assert remove_extension('app.test.js') == 'app.test'  # bug: 'app'

def test_spec_file():
    assert remove_extension('component.spec.ts') == 'component.spec'  # bug: 'component'

def test_config_file():
    assert remove_extension('my.vite.config.js') == 'my.vite.config'  # bug: 'my'
