import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from path_normalizer import normalize_path

# PASS with bug (forward-slash paths work correctly)

def test_simple_path():
    assert normalize_path('/usr/local/bin') == '/usr/local/bin'

def test_trailing_slash_removed():
    assert normalize_path('/home/user/') == '/home/user'

def test_multiple_slashes_collapsed():
    assert normalize_path('/usr//local///bin') == '/usr/local/bin'

def test_root_path():
    assert normalize_path('/') == ''

# FAIL with bug (backslash paths not converted)

def test_backslash_converted():
    assert normalize_path('src\\utils\\helpers') == 'src/utils/helpers'

def test_mixed_slashes():
    assert normalize_path('/home\\user/docs') == '/home/user/docs'

def test_windows_absolute():
    assert normalize_path('C:\\Users\\admin\\file.txt') == 'C:/Users/admin/file.txt'
