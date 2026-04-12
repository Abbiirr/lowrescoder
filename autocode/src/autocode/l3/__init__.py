"""Layer 3: Constrained Generation.

Uses llama-cpp-python with native grammar constraints for fast,
structured output from small models (1.5B-3B parameters).

The L3 engine is optional — if llama-cpp-python is not installed,
the system falls through to L4 (full reasoning) transparently.
"""
