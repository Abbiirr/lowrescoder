import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from semver_comparator import compare_versions

# PASS with bug (single-digit parts, string comparison == integer comparison)

def test_equal_versions():
    assert compare_versions('1.2.3', '1.2.3') == 0

def test_major_greater():
    assert compare_versions('2.0.0', '1.9.9') == 1

def test_major_less():
    assert compare_versions('1.0.0', '2.0.0') == -1

def test_minor_difference():
    assert compare_versions('1.3.0', '1.2.0') == 1

# FAIL with bug (multi-digit parts: '9' > '10' lexicographically)

def test_minor_multidigit():
    # 1.10.0 > 1.9.0 numerically, but '10' < '9' as string
    assert compare_versions('1.10.0', '1.9.0') == 1

def test_patch_multidigit():
    # 2.0.10 > 2.0.9 numerically, but '10' < '9' as string
    assert compare_versions('2.0.10', '2.0.9') == 1

def test_major_multidigit():
    # 10.0.0 > 9.0.0 numerically, but '10' < '9' as string
    assert compare_versions('10.0.0', '9.0.0') == 1
