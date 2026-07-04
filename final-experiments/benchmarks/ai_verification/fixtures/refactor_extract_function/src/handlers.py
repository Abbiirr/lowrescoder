import re


def handle_signup(email: str, name: str) -> dict:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError(f"Invalid email: {email}")
    return {"user": name, "email": email}
