# Language Server Protocol (LSP) Specification

Source: https://microsoft.github.io/language-server-protocol/

Why this matters to HybridCoder:
- Defines JSON-RPC methods for hover, definition, references, symbols, diagnostics.
- Basis for Pyright and JDT LS integration.
- Request semantics guide caching and latency budgets.

Notes from local docs:
- Spec version referenced is 3.17.
- Deterministic query types should not require LLM calls.
