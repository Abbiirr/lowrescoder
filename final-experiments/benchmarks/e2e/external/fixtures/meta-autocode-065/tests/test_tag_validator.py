import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tag_validator import is_valid_release_tag

# --- PASS with bug (valid semver or empty — both agree) ---

def test_valid_v1_2_3():
    assert is_valid_release_tag('v1.2.3') is True

def test_empty_tag():
    assert is_valid_release_tag('') is False

def test_valid_v10_0_1():
    assert is_valid_release_tag('v10.0.1') is True

def test_valid_v0_0_0():
    assert is_valid_release_tag('v0.0.0') is True

# --- FAIL with bug (non-semver non-empty: bug True, fix False) ---

def test_no_v_prefix_rejected():
    assert is_valid_release_tag('1.2.3') is False

def test_plain_string_rejected():
    assert is_valid_release_tag('release') is False

def test_partial_semver_rejected():
    assert is_valid_release_tag('v1.2') is False
