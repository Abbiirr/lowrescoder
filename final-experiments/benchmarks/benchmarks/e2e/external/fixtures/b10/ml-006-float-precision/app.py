"""Financial calculations with precision requirements."""


def calculate_total(prices):
    """Sum a list of prices.

    Returns the total as a float.
    """
    total = 0.0
    for p in prices:
        total += p
    return total


def calculate_discount(price, discount_percent):
    """Apply a percentage discount to a price.

    Returns the discounted price.
    """
    return price * (1 - discount_percent / 100)


def split_bill(total, num_people):
    """Split a bill evenly among people.

    Returns (per_person_amount, remainder) where remainder is what's left
    after rounding each share to 2 decimal places.
    """
    per_person = round(total / num_people, 2)
    remainder = round(total - (per_person * num_people), 2)
    return per_person, remainder


def are_amounts_equal(a, b):
    """Check if two monetary amounts are equal.

    Bug: uses exact == comparison, which fails for floating point
    results like 0.1 + 0.2 != 0.3.
    Should use approximate comparison with tolerance (e.g., abs(a-b) < 1e-9)
    or round to 2 decimal places before comparing.
    """
    # Bug: exact float comparison
    return a == b


def validate_transaction(items):
    """Validate that item prices sum to the stated total.

    Each item is a dict with 'price' and the last item has 'expected_total'.
    Bug: relies on are_amounts_equal which uses exact float comparison.
    """
    prices = [item["price"] for item in items]
    computed_total = calculate_total(prices)
    expected = items[-1].get("expected_total", computed_total)
    return are_amounts_equal(computed_total, expected)
