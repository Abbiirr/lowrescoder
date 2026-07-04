#!/usr/bin/env bash
# Setup for tb-006-fibonacci-server
# Creates a stub HTTP server script.
set -euo pipefail

cat > server.py << 'STUB'
#!/usr/bin/env python3
"""HTTP server that returns Fibonacci numbers.

Endpoints:
  GET /fib?n=<number>  — returns JSON: {"n": <number>, "result": <fibonacci_number>}

The server must listen on port 8765.
Fibonacci sequence: fib(0)=0, fib(1)=1, fib(2)=1, fib(3)=2, fib(4)=3, fib(5)=5, ...

Use only the Python standard library (http.server, json, urllib.parse).
"""
# TODO: Implement the server
STUB

chmod +x server.py

echo "Setup complete. server.py stub created."
