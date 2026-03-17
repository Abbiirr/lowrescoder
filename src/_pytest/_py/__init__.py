"""Py shim module for _pytest._py."""
# Ensure these modules are in sys.modules so the py.py shim can find them
import sys

from .error import Error
from .path import Path

sys.modules['_pytest._py.error'] = Error
sys.modules['_pytest._py.path'] = Path
