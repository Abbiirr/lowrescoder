# Qwen3-8B

Source: https://huggingface.co/Qwen/Qwen3-8B

Why this matters to HybridCoder:
- Default Layer 4 model for complex reasoning and edits.
- Supports thinking mode while fitting 8 GB VRAM with Q4_K_M.

Notes from local docs:
- Quantization target: Q4_K_M (~5 GB VRAM).
- Served via Ollama as the Layer 4 runtime.
- Fallback: Qwen2.5-Coder-7B if Qwen3-8B is unavailable in Ollama.
