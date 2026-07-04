"""Compatibility alias for the shared command runtime.

The canonical command runtime now lives in ``autocode.app.commands``.
This shim keeps the historical import path stable while internal callers
move to the shared application-layer module.
"""

from __future__ import annotations

import sys

from autocode.app import commands as _commands

sys.modules[__name__] = _commands
