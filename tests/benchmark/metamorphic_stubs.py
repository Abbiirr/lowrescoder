"""Metamorphic test stubs for calculator benchmark invariants.

DEFERRED: These invariants define mathematical properties that should hold
regardless of the specific implementation. Currently data-only — no
execution logic. Will be wired into the benchmark when browser-based
functional testing (Playwright) is added.

Each invariant is a dict with:
    - name: str — invariant name
    - description: str — what property is being tested
    - check: str — pseudo-code or expression template for the invariant
    - examples: list[dict] — concrete test cases
"""

from __future__ import annotations

ARITHMETIC_INVARIANTS: list[dict] = [
    {
        "name": "commutativity_addition",
        "description": "a + b == b + a for all a, b",
        "check": "calc(a + b) == calc(b + a)",
        "examples": [
            {"a": 3, "b": 7, "expected": 10},
            {"a": -5, "b": 12, "expected": 7},
            {"a": 0.1, "b": 0.2, "expected": 0.3},
            {"a": 999, "b": 1, "expected": 1000},
        ],
    },
    {
        "name": "commutativity_multiplication",
        "description": "a * b == b * a for all a, b",
        "check": "calc(a * b) == calc(b * a)",
        "examples": [
            {"a": 4, "b": 5, "expected": 20},
            {"a": -3, "b": 7, "expected": -21},
            {"a": 0.5, "b": 6, "expected": 3.0},
        ],
    },
    {
        "name": "identity_addition",
        "description": "a + 0 == a for all a",
        "check": "calc(a + 0) == a",
        "examples": [
            {"a": 42, "expected": 42},
            {"a": -17, "expected": -17},
            {"a": 0, "expected": 0},
            {"a": 3.14, "expected": 3.14},
        ],
    },
    {
        "name": "identity_multiplication",
        "description": "a * 1 == a for all a",
        "check": "calc(a * 1) == a",
        "examples": [
            {"a": 42, "expected": 42},
            {"a": -17, "expected": -17},
            {"a": 0, "expected": 0},
        ],
    },
    {
        "name": "inverse_subtraction",
        "description": "a - a == 0 for all a",
        "check": "calc(a - a) == 0",
        "examples": [
            {"a": 100, "expected": 0},
            {"a": -50, "expected": 0},
            {"a": 3.14159, "expected": 0},
        ],
    },
    {
        "name": "distributive",
        "description": "a * (b + c) == a*b + a*c",
        "check": "calc(a * (b + c)) == calc(a*b + a*c)",
        "examples": [
            {"a": 3, "b": 4, "c": 5, "expected": 27},
            {"a": 2, "b": 10, "c": -3, "expected": 14},
        ],
    },
]

CONVERSION_ROUNDTRIPS: list[dict] = [
    {
        "name": "celsius_fahrenheit_roundtrip",
        "description": "C->F->C should return original value",
        "check": "f_to_c(c_to_f(x)) == x",
        "examples": [
            {"value": 0, "tolerance": 0.01},
            {"value": 100, "tolerance": 0.01},
            {"value": -40, "tolerance": 0.01},
            {"value": 37, "tolerance": 0.01},
        ],
    },
    {
        "name": "km_miles_roundtrip",
        "description": "km->mi->km should return original value",
        "check": "mi_to_km(km_to_mi(x)) == x",
        "examples": [
            {"value": 1, "tolerance": 0.01},
            {"value": 42.195, "tolerance": 0.01},
            {"value": 100, "tolerance": 0.01},
        ],
    },
    {
        "name": "kg_lbs_roundtrip",
        "description": "kg->lbs->kg should return original value",
        "check": "lbs_to_kg(kg_to_lbs(x)) == x",
        "examples": [
            {"value": 1, "tolerance": 0.01},
            {"value": 75, "tolerance": 0.01},
            {"value": 100, "tolerance": 0.01},
        ],
    },
    {
        "name": "liter_gallon_roundtrip",
        "description": "L->gal->L should return original value",
        "check": "gal_to_l(l_to_gal(x)) == x",
        "examples": [
            {"value": 1, "tolerance": 0.01},
            {"value": 3.785, "tolerance": 0.01},
        ],
    },
]

SCIENTIFIC_INVARIANTS: list[dict] = [
    {
        "name": "pythagorean_trig_identity",
        "description": "sin^2(x) + cos^2(x) == 1 for all x",
        "check": "sin(x)^2 + cos(x)^2 == 1",
        "examples": [
            {"x": 0, "tolerance": 0.0001},
            {"x": 1.5708, "tolerance": 0.0001},  # pi/2
            {"x": 3.14159, "tolerance": 0.0001},  # pi
            {"x": 0.7854, "tolerance": 0.0001},  # pi/4
        ],
    },
    {
        "name": "log_exp_inverse",
        "description": "log(exp(x)) == x for all x > 0",
        "check": "log(exp(x)) == x",
        "examples": [
            {"x": 1, "tolerance": 0.001},
            {"x": 2, "tolerance": 0.001},
            {"x": 0.5, "tolerance": 0.001},
        ],
    },
    {
        "name": "sqrt_square_inverse",
        "description": "sqrt(x^2) == |x| for all x",
        "check": "sqrt(x^2) == abs(x)",
        "examples": [
            {"x": 4, "tolerance": 0.0001},
            {"x": 9, "tolerance": 0.0001},
            {"x": 2.5, "tolerance": 0.0001},
        ],
    },
]
