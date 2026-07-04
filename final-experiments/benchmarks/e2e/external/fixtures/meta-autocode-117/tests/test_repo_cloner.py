import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_cloner import build_clone_url

# PASS with bug (SSH protocol)

def test_ssh_url():
    result = build_clone_url('github.com', 'alice', 'myrepo', 'ssh')
    assert result == 'git@github.com:alice/myrepo.git'

def test_ssh_ends_with_git():
    assert build_clone_url('gitlab.com', 'user', 'repo', 'ssh').endswith('.git')

def test_ssh_has_colon():
    result = build_clone_url('github.com', 'org', 'proj', 'ssh')
    assert ':' in result

def test_returns_string():
    assert isinstance(build_clone_url('gh.com', 'u', 'r'), str)

# FAIL with bug (https protocol returns ssh URL)

def test_https_url():
    result = build_clone_url('github.com', 'alice', 'myrepo', 'https')
    assert result == 'https://github.com/alice/myrepo.git'  # bug: git@ URL

def test_default_protocol_is_https():
    result = build_clone_url('github.com', 'alice', 'myrepo')
    assert result.startswith('https://')  # bug: starts with 'git@'

def test_https_no_at_sign():
    result = build_clone_url('gitea.io', 'org', 'repo', 'https')
    assert '@' not in result  # bug: 'git@' contains @
