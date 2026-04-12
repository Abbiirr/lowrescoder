# llama-cpp-python

Source: https://llama-cpp-python.readthedocs.io/en/latest/

Why this matters to HybridCoder:
- Python bindings for llama.cpp to run local GGUF models.
- Layer 3 runtime for constrained generation with Outlines.

Notes from local docs:
- Used instead of Ollama because Outlines does not integrate with Ollama's HTTP API.
- Loads Qwen2.5-Coder-1.5B Q4_K_M for Layer 3 tasks.
