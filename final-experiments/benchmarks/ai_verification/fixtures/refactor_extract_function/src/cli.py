import re
import sys


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        print("Usage: cli <email>")
        return 1
    email = args[0]
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        print(f"Bad email: {email}")
        return 2
    print(f"Valid: {email}")
    return 0
