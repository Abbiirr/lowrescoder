import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from file_sizer import format_file_size

# PASS with bug (units only matter for the suffix, not the value here)

def test_bytes_under_1024():
    assert format_file_size(500) == '500 B'

def test_zero_bytes():
    assert format_file_size(0) == '0 B'

def test_result_is_string():
    assert isinstance(format_file_size(1024), str)

def test_large_file_has_gb():
    assert 'GB' in format_file_size(2 * 1024 ** 3)

# FAIL with bug (1024 boundary vs 1000 boundary)

def test_one_kibibyte_is_kb():
    # 1024 bytes = 1.0 KB in binary; bug: 1024 / 1000 = 1.0 KB — same!
    # Actually 1024 / 1000 = 1.024 KB. Let's use exactly 1000 bytes.
    # 1000 bytes: fix → 1000 < 1024, so '1000 B'. Bug → 1000 / 1000 = '1.0 KB'.
    assert format_file_size(1000) == '1000 B'  # bug: '1.0 KB'

def test_1023_bytes_is_b():
    assert format_file_size(1023) == '1023 B'  # bug: '1.0 KB'

def test_one_mb_boundary():
    # 1024*1024 = 1048576 bytes = 1.0 MB in binary
    # Bug: 1048576 / 1000^2 = 1.0 MB (rounded) — actually 1048576/1000000 = 1.0 MB
    # Hmm, that's also 1.0 MB. Let me use 1000000:
    # 1000000 bytes: fix → 1000000 / 1024^2 = 0.95 MB → '0.95 MB'? Actually fix threshold is 1024^2.
    # Let me use 512000: fix → 512000 < 1048576 → 512000/1024 = 500.0 KB; bug → 512000 < 1e6 → 512000/1000 = 512.0 KB
    assert format_file_size(512000) == '500.0 KB'  # bug: '512.0 KB'
