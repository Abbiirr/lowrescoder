import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from version_checker import is_prerelease

# PASS (stable releases — neither '-' nor '+', bug and fix both False)

def test_stable_patch():
    assert is_prerelease('1.0.0') == False

def test_stable_minor():
    assert is_prerelease('2.3.4') == False

def test_stable_major():
    assert is_prerelease('10.20.30') == False

def test_two_part_version():
    assert is_prerelease('1.0') == False

# FAIL (pre-releases have '-' — bug: False, fix: True)

def test_alpha_prerelease():
    assert is_prerelease('1.0.0-alpha') == True  # bug: '+' not in → False

def test_beta_prerelease():
    assert is_prerelease('2.0.0-beta.1') == True  # bug: False

def test_rc_prerelease():
    assert is_prerelease('1.0.0-rc.1') == True  # bug: False
