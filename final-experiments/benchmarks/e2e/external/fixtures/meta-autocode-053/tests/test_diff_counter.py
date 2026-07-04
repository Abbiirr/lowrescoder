import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from diff_counter import count_diff_lines

# --- PASS with bug (no +++ / --- headers in input) ---

def test_empty_diff():
    assert count_diff_lines('') == {'added': 0, 'removed': 0}

def test_only_context_lines():
    diff = ' context line\n another context'
    assert count_diff_lines(diff) == {'added': 0, 'removed': 0}

def test_simple_add_no_headers():
    diff = '+new line\n context\n-old line'
    assert count_diff_lines(diff) == {'added': 1, 'removed': 1}

def test_multiple_adds_no_headers():
    diff = '+line1\n+line2\n+line3\n context\n-removed'
    assert count_diff_lines(diff) == {'added': 3, 'removed': 1}

# --- FAIL with bug (+++ / --- header lines miscounted) ---

def test_headers_only_excluded():
    diff = '--- a/file.py\n+++ b/file.py'
    # Bug counts --- as removed (1) and +++ as added (1); fix returns 0/0
    assert count_diff_lines(diff) == {'added': 0, 'removed': 0}

def test_realistic_diff_with_headers():
    diff = '--- a/foo.py\n+++ b/foo.py\n@@ -1,3 +1,3 @@\n context\n-old line\n+new line'
    # Bug: added=2 ('+++ b/foo.py' and '+new line'), removed=2 ('--- a/foo.py' and '-old line')
    # Fix: added=1, removed=1
    assert count_diff_lines(diff) == {'added': 1, 'removed': 1}

def test_multi_file_diff_headers():
    diff = '--- a/x.py\n+++ b/x.py\n+actual add\n--- a/y.py\n+++ b/y.py\n-actual remove'
    # Bug: added=3, removed=3 (includes both sets of headers)
    # Fix: added=1, removed=1
    assert count_diff_lines(diff) == {'added': 1, 'removed': 1}
