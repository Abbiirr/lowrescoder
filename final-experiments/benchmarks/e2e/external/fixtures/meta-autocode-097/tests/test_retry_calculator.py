import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from retry_calculator import get_retry_delay

# PASS with bug (capping behavior same, or close enough)

def test_large_attempt_capped():
    assert get_retry_delay(10) == 60.0  # 1 + 1024 > 60 → capped; fix: 1 * 1024 > 60 → capped

def test_max_delay_respected():
    assert get_retry_delay(20) == 60.0  # both exceed cap

def test_returns_float():
    assert isinstance(get_retry_delay(0), float)

def test_cap_at_max_delay_param():
    assert get_retry_delay(10, base_delay=2.0, max_delay=100.0) == 100.0  # 2+1024>100; 2*1024>100

# FAIL with bug (addition vs multiplication gives wrong early-stage values)

def test_attempt_zero_base_delay():
    # attempt=0: fix: 1.0 * 2^0 = 1.0; bug: 1.0 + 2^0 = 2.0
    assert get_retry_delay(0) == 1.0  # bug: 2.0

def test_attempt_one():
    # attempt=1: fix: 1.0 * 2 = 2.0; bug: 1.0 + 2 = 3.0
    assert get_retry_delay(1) == 2.0  # bug: 3.0

def test_attempt_two():
    # attempt=2: fix: 1.0 * 4 = 4.0; bug: 1.0 + 4 = 5.0
    assert get_retry_delay(2) == 4.0  # bug: 5.0
