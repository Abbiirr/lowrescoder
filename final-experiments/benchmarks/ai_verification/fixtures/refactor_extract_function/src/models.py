import re


def validate_user_record(record: dict) -> bool:
    email = record.get("email", "")
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
