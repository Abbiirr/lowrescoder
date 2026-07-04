import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from retry_policy import should_retry

def test_retry_on_500():
    assert should_retry(500, 3, 0) is True

def test_no_retry_on_200():
    assert should_retry(200, 3, 0) is False

def test_no_retry_when_max_reached():
    assert should_retry(500, 3, 3) is False

def test_no_retry_on_404():
    assert should_retry(404, 3, 0) is False

def test_retry_on_502():
    # BUG: 502 != 500 → returns False, should be True (Bad Gateway)
    assert should_retry(502, 3, 0) is True

def test_retry_on_503():
    # BUG: 503 != 500 → returns False, should be True (Service Unavailable)
    assert should_retry(503, 3, 0) is True

def test_retry_on_504():
    # BUG: 504 != 500 → returns False, should be True (Gateway Timeout)
    assert should_retry(504, 3, 0) is True
