# Qwen2.5-Coder 7B Instruct

Source: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct

Why this matters to HybridCoder:
- Legacy 7B model for local reasoning and complex edits (fallback only).
- Superseded by Qwen3-8B Q4_K_M as the default Layer 4 model.

Notes from local docs:
- Quantization target: Q4_K_M.
- Default context length: 32k (per plan/spec).
- Use only if Qwen3-8B is unavailable or unstable in Ollama.
