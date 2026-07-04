import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from arg_builder import build_git_args

# PASS with bug

def test_empty_args():
    assert build_git_args([], []) == ''

def test_single_base_arg():
    result = build_git_args(['log'], [])
    assert result == 'log'

def test_preserves_all_tokens():
    result = build_git_args(['log', '--oneline'], ['--author=alice'])
    parts = result.split() if ' ' in result else result.split(',')
    assert 'log' in parts
    assert '--oneline' in parts
    assert '--author=alice' in parts

def test_returns_string():
    assert isinstance(build_git_args(['status'], []), str)

# FAIL with bug (comma instead of space separator)

def test_single_extra_arg_space_separated():
    result = build_git_args(['git'], ['log'])
    assert result == 'git log'  # bug returns 'git,log'

def test_no_commas_in_output():
    result = build_git_args(['git', 'log'], ['--oneline'])
    assert ',' not in result  # bug returns 'git,log,--oneline'

def test_space_separated_multiple():
    result = build_git_args(['git', 'diff'], ['HEAD~1', 'HEAD'])
    assert result == 'git diff HEAD~1 HEAD'  # bug: 'git,diff,HEAD~1,HEAD'
