import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from search_highlighter import highlight_matches

# --- PASS with bug (exact case match — both produce same result) ---

def test_exact_case_single():
    assert highlight_matches('hello world', 'hello') == '<mark>hello</mark> world'

def test_exact_case_multiple():
    assert highlight_matches('bat cat bat', 'bat') == '<mark>bat</mark> cat <mark>bat</mark>'

def test_no_match():
    assert highlight_matches('hello world', 'xyz') == 'hello world'

def test_exact_case_at_end():
    assert highlight_matches('search query', 'query') == 'search <mark>query</mark>'

# --- FAIL with bug (case mismatch — bug returns unhighlighted) ---

def test_uppercase_query_lowercase_text():
    result = highlight_matches('hello world', 'HELLO')
    assert '<mark>' in result

def test_mixed_case_query():
    result = highlight_matches('bat is great', 'Bat')
    assert '<mark>' in result

def test_all_caps_text():
    result = highlight_matches('SEARCH THIS TEXT', 'search')
    assert '<mark>' in result
