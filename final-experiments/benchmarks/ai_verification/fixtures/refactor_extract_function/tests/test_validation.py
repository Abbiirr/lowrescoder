from src.handlers import handle_signup
from src.models import validate_user_record
from src.cli import main


def test_signup_valid():
    result = handle_signup("alice@example.com", "Alice")
    assert result == {"user": "Alice", "email": "alice@example.com"}


def test_signup_invalid():
    try:
        handle_signup("not-an-email", "Bob")
        assert False, "should have raised"
    except ValueError:
        pass


def test_validate_record_good():
    assert validate_user_record({"email": "user@example.org"}) is True


def test_validate_record_bad():
    assert validate_user_record({"email": "bad"}) is False


def test_cli_valid(capsys):
    rc = main(["test@example.com"])
    assert rc == 0


def test_cli_invalid(capsys):
    rc = main(["notanemail"])
    assert rc == 2
