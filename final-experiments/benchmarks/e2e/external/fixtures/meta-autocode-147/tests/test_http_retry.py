import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from http_retry import should_retry

# PASS with bug (attempt limits hit, or status codes both agree shouldn't retry)

def test_max_attempts_reached():
    assert should_retry(500, 3, 3) is False

def test_max_attempts_exceeded():
    assert should_retry(500, 5, 3) is False

def test_max_attempts_with_success():
    assert should_retry(200, 3, 3) is False

def test_404_no_retry():
    # Bug: 404==200 → False; Fix: 404 not 5xx → False — both agree
    assert should_retry(404, 1, 3) is False

# FAIL with bug (correct: retry 5xx, not 2xx)

def test_500_should_retry():
    assert should_retry(500, 1, 3) is True  # bug: 500==200 → False

def test_503_should_retry():
    assert should_retry(503, 0, 5) is True  # bug: 503==200 → False

def test_200_should_not_retry():
    assert should_retry(200, 1, 3) is False  # bug: 200==200 → True → FAIL
