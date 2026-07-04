"""Tests for catastrophic backtracking bug in regex validation."""
import sys
import os
import signal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import validate_email, validate_url, extract_tags, sanitize_input


class TimeoutError(Exception):
    """Raised when a function takes too long."""
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Function took too long — likely catastrophic backtracking")


def _run_with_timeout(func, args, timeout_seconds=2):
    """Run a function with a timeout. Raises TimeoutError if it takes too long."""
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        result = func(*args)
        signal.alarm(0)
        return result
    finally:
        signal.signal(signal.SIGALRM, old_handler)


def test_valid_email():
    """Valid email should be accepted."""
    assert validate_email("user@example.com") is True


def test_valid_email_with_dots():
    """Email with dots in local part should be accepted."""
    assert validate_email("user.name@example.com") is True


def test_invalid_email():
    """Invalid email should be rejected."""
    assert validate_email("not-an-email") is False


def test_email_no_catastrophic_backtracking():
    """Email validation should complete quickly on adversarial input.

    Bug: the pattern (\\w+\\.?)+ causes exponential backtracking on
    inputs like 'aaa...aaa!' that almost-but-don't match. This input
    should be rejected quickly (< 2 seconds), not hang.
    """
    # This string triggers catastrophic backtracking in the buggy pattern
    adversarial = "a" * 30 + "!"
    result = _run_with_timeout(validate_email, (adversarial,), timeout_seconds=2)
    assert result is False, "Adversarial input should be rejected"


def test_email_long_valid():
    """Long but valid email should be handled quickly."""
    long_email = "a" * 50 + "@example.com"
    result = _run_with_timeout(validate_email, (long_email,), timeout_seconds=2)
    assert result is True


def test_url_no_catastrophic_backtracking():
    """URL validation should complete quickly on adversarial input.

    Bug: (\\w+/?)+ causes catastrophic backtracking on non-matching inputs.
    """
    adversarial = "http://" + "a" * 30 + "!"
    result = _run_with_timeout(validate_url, (adversarial,), timeout_seconds=2)
    assert result is False, "Adversarial URL input should be rejected"


def test_valid_url():
    """Valid URL should be accepted."""
    assert validate_url("https://example.com") is True


def test_extract_tags():
    """Tag extraction should work (no bug)."""
    tags = extract_tags("Hello #world this is #python")
    assert "world" in tags
    assert "python" in tags


def test_sanitize_input():
    """Input sanitization should work (no bug)."""
    result = sanitize_input("Hello, World! 123")
    assert result == "Hello World 123"
