#!/usr/bin/env python3
"""Slow backend that never sends on_status — tests stageInit timeout behavior."""
import time, sys
# Accept 'serve' arg from findPythonBackend
time.sleep(60)
