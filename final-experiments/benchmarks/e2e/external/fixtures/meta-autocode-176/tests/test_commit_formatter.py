import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from commit_formatter import format_commit

# PASS (clean messages — no surrounding whitespace)

def test_fix_message():
    assert format_commit('fix', 'resolve login bug') == 'fix: resolve login bug'

def test_feat_message():
    assert format_commit('feat', 'add dark mode') == 'feat: add dark mode'

def test_docs_message():
    assert format_commit('docs', 'update readme') == 'docs: update readme'

def test_chore_message():
    assert format_commit('chore', 'bump version') == 'chore: bump version'

# FAIL (whitespace in message — bug leaks it through)

def test_leading_spaces():
    assert format_commit('fix', '  spaces before') == 'fix: spaces before'  # bug: 'fix:   spaces before'

def test_trailing_spaces():
    assert format_commit('feat', 'trailing spaces  ') == 'feat: trailing spaces'  # bug keeps '  '

def test_newline_in_message():
    assert format_commit('fix', '\nnewline\n') == 'fix: newline'  # bug keeps '\n'
