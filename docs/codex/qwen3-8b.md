# Qwen3-8B (Legacy Reference)

Source: https://huggingface.co/Qwen/Qwen3-8B

Why this matters to AutoCode:
- Previously the default Layer 4 model for complex reasoning and edits.
- Now superseded by the LLM Gateway's `coding` alias, which routes to the best available coding model across 9 providers (GPT-4.1, DeepSeek-R1, Codestral, Devstral, Qwen3-Coder, etc.).
- Qwen3-8B remains available via the `local` alias (Ollama-only, for privacy-sensitive workloads).

Notes:
- Gateway base URL: http://localhost:4000/v1
- Gateway docs: http://localhost:4001/docs
- For local-only inference: use model alias `local`
