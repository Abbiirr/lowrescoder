import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from release_namer import generate_release_name

# PASS with bug (dash vs dot doesn't affect these checks)

def test_starts_with_v():
    assert generate_release_name((1, 0, 0)).startswith('v')

def test_contains_major_version():
    assert '1' in generate_release_name((1, 2, 3))

def test_pre_release_suffix():
    tag = generate_release_name((1, 0, 0), pre_release=True)
    assert tag.endswith('-pre')

def test_stable_no_pre_suffix():
    tag = generate_release_name((2, 0, 0), pre_release=False)
    assert not tag.endswith('-pre')

# FAIL with bug (dot separator required)

def test_dot_separated_version():
    assert generate_release_name((1, 2, 3)) == 'v1.2.3'  # bug: 'v1-2-3'

def test_single_digit_version():
    assert generate_release_name((0, 1, 0)) == 'v0.1.0'  # bug: 'v0-1-0'

def test_pre_release_format():
    assert generate_release_name((1, 0, 0), pre_release=True) == 'v1.0.0-pre'  # bug: 'v1-0-0-pre'
