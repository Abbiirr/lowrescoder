import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_language import get_repo_language

# PASS with bug (no 'language' key or language='Unknown' — both return 'Unknown')
def test_empty():
    assert get_repo_language({}) == 'Unknown'

def test_name_only():
    assert get_repo_language({'name': 'myrepo'}) == 'Unknown'

def test_stars_only():
    assert get_repo_language({'stars': 5}) == 'Unknown'

def test_language_unknown():
    assert get_repo_language({'language': 'Unknown'}) == 'Unknown'

# FAIL with bug (has 'language' != 'Unknown' — bug reads 'lang', returns 'Unknown')
def test_python():
    assert get_repo_language({'language': 'Python'}) == 'Python'

def test_go_with_stars():
    assert get_repo_language({'language': 'Go', 'stars': 10}) == 'Go'

def test_typescript():
    assert get_repo_language({'language': 'TypeScript'}) == 'TypeScript'
