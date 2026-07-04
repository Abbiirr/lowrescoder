# Task: Fibonacci HTTP Server

## Objective

Build an HTTP server that returns Fibonacci numbers via a REST endpoint.

## Requirements

1. Edit `server.py` to implement an HTTP server.
2. The server must listen on **port 8765**.
3. Endpoint: `GET /fib?n=<number>` returns JSON: `{"n": <number>, "result": <fibonacci_value>}`
4. Fibonacci definition: `fib(0) = 0`, `fib(1) = 1`, `fib(n) = fib(n-1) + fib(n-2)`
5. Use only the Python standard library (no Flask, FastAPI, etc.).
6. The server should handle at least `n` values from 0 to 30.
7. Return HTTP 400 with `{"error": "..."}` for invalid input (missing n, non-integer, negative).

## Examples

```
GET /fib?n=0  -> {"n": 0, "result": 0}
GET /fib?n=1  -> {"n": 1, "result": 1}
GET /fib?n=10 -> {"n": 10, "result": 55}
```

## Files

- `server.py` — the server script you must edit
