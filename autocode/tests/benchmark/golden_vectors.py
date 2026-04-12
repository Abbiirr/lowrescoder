"""Golden test vectors for calculator benchmark modes.

DEFERRED: These vectors define expected input/output pairs for deterministic
validation of generated calculator applications. Currently data-only — no
execution logic. Will be wired into the benchmark when browser-based
functional testing (Playwright) is added.

Each vector is a dict with:
    - input: str — the expression or conversion to evaluate
    - expected: str | float — the expected result
    - description: str — human-readable description of what's being tested
    - tolerance: float | None — acceptable delta for floating-point results
"""

from __future__ import annotations

REGULAR_CALCULATOR_VECTORS: list[dict] = [
    {
        "input": "2 + 3",
        "expected": 5,
        "description": "Basic addition",
        "tolerance": None,
    },
    {
        "input": "10 - 4",
        "expected": 6,
        "description": "Basic subtraction",
        "tolerance": None,
    },
    {
        "input": "6 * 7",
        "expected": 42,
        "description": "Basic multiplication",
        "tolerance": None,
    },
    {
        "input": "15 / 4",
        "expected": 3.75,
        "description": "Division with decimal result",
        "tolerance": 0.001,
    },
    {
        "input": "1 / 0",
        "expected": "Error",
        "description": "Division by zero — should display error or Infinity",
        "tolerance": None,
    },
    {
        "input": "0.1 + 0.2",
        "expected": 0.3,
        "description": "Floating-point precision (big.js should handle this)",
        "tolerance": 0.001,
    },
    {
        "input": "100 - 99.99",
        "expected": 0.01,
        "description": "Floating-point subtraction precision",
        "tolerance": 0.001,
    },
]

SCIENTIFIC_CALCULATOR_VECTORS: list[dict] = [
    {
        "input": "sin(0)",
        "expected": 0.0,
        "description": "Sine of 0 radians",
        "tolerance": 0.0001,
    },
    {
        "input": "cos(0)",
        "expected": 1.0,
        "description": "Cosine of 0 radians",
        "tolerance": 0.0001,
    },
    {
        "input": "tan(0)",
        "expected": 0.0,
        "description": "Tangent of 0 radians",
        "tolerance": 0.0001,
    },
    {
        "input": "sqrt(144)",
        "expected": 12.0,
        "description": "Square root of perfect square",
        "tolerance": 0.0001,
    },
    {
        "input": "log(1)",
        "expected": 0.0,
        "description": "Natural log of 1",
        "tolerance": 0.0001,
    },
    {
        "input": "log(e)",
        "expected": 1.0,
        "description": "Natural log of e",
        "tolerance": 0.001,
    },
    {
        "input": "2^10",
        "expected": 1024,
        "description": "Power operation",
        "tolerance": None,
    },
    {
        "input": "factorial(5)",
        "expected": 120,
        "description": "Factorial of 5",
        "tolerance": None,
    },
]

UNIT_CONVERTER_VECTORS: list[dict] = [
    {
        "input": {"value": 1, "from": "km", "to": "miles"},
        "expected": 0.621371,
        "description": "Kilometers to miles",
        "tolerance": 0.001,
    },
    {
        "input": {"value": 1, "from": "kg", "to": "lbs"},
        "expected": 2.20462,
        "description": "Kilograms to pounds",
        "tolerance": 0.001,
    },
    {
        "input": {"value": 0, "from": "celsius", "to": "fahrenheit"},
        "expected": 32.0,
        "description": "0°C to Fahrenheit",
        "tolerance": 0.1,
    },
    {
        "input": {"value": 100, "from": "celsius", "to": "fahrenheit"},
        "expected": 212.0,
        "description": "100°C to Fahrenheit (boiling point)",
        "tolerance": 0.1,
    },
    {
        "input": {"value": 0, "from": "celsius", "to": "kelvin"},
        "expected": 273.15,
        "description": "0°C to Kelvin",
        "tolerance": 0.01,
    },
    {
        "input": {"value": 1, "from": "liter", "to": "gallon"},
        "expected": 0.264172,
        "description": "Liters to US gallons",
        "tolerance": 0.001,
    },
    {
        "input": {"value": 60, "from": "mph", "to": "kmh"},
        "expected": 96.5606,
        "description": "Miles per hour to km/h",
        "tolerance": 0.01,
    },
]
