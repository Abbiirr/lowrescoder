# LLM Gateway API (formerly Ollama API)

Source: http://localhost:4001/docs

Why this matters to AutoCode:
- OpenAI-compatible API gateway used for Layer 4 generation.
- Aggregates 9 free providers (OpenRouter, Google AI Studio, Cerebras, Groq, Mistral, GitHub Models, NVIDIA NIM, Cloudflare, Cohere).
- Automatic failover, latency-based routing, 5-hour caching.
- HTTP API with streaming token support.

Notes from local docs:
- Base URL: http://localhost:4000/v1
- Docs URL: http://localhost:4001/docs
- Model aliases: `coding` (default for AutoCode), `default`, `fast`, `thinking`, `vision`, `tools`, `big`, `local`.
- Health check: `GET /health/readiness`
- Layer 3 uses llama-cpp-python + native grammar (not the gateway).
