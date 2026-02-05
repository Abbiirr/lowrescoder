# Research: Local LLM Inference Stack (2025-2026)

> Generated from research for HybridCoder project planning

---

## 1. Inference Engine Comparison

### llama.cpp
- **Status**: b4000+ builds, continuous releases
- **Backend**: C/C++ with CUDA, Metal, Vulkan, SYCL
- **Quantization**: GGUF format; Q2_K through Q8_0 and FP16
- **Throughput (7B Q4_K_M)**: ~30-60 tok/s RTX 3080/4070; ~25-40 tok/s M2 Pro; ~8-15 tok/s CPU-only
- **Memory (7B Q4_K_M)**: ~4.5 GB VRAM + ~1-2 GB KV cache at 8K context
- **Key features**: OpenAI-compatible server, speculative decoding, GBNF grammar-constrained sampling, continuous batching, flash attention, GPU+CPU split
- **Structured output**: Built-in GBNF grammar support
- **Best for**: Maximum performance, fine-grained control

### Ollama
- **Latest**: v0.5.x (built on llama.cpp)
- **Adds**: Model management, REST API, Modelfile system, auto GPU detection
- **Throughput**: Same as llama.cpp minus ~1-3% HTTP overhead
- **Memory**: Same + ~50-100 MB for Go server
- **API**: `/api/generate`, `/api/chat`, `/api/embed` — all support streaming
- **Structured output**: JSON mode + JSON schema (v0.5+). Does NOT support arbitrary GBNF grammars
- **CRITICAL**: Outlines does NOT work with Ollama's HTTP API
- **Best for**: Easiest setup, model management, quick prototyping

### vLLM
- **Latest**: v0.7.x
- **Backend**: CUDA-focused; PagedAttention
- **Throughput (7B)**: 80-150+ tok/s A100; 40-80 tok/s consumer
- **Memory**: Higher baseline ~6-8 GB VRAM for 7B Q4
- **Structured output**: First-class Outlines integration (built-in dependency)
- **Limitation**: Primarily Linux; Windows experimental; heavier footprint
- **Best for**: Multi-user serving, batch processing

### MLX (Apple Silicon only)
- **Latest**: mlx-lm 0.20+
- **Throughput (7B Q4)**: ~35-50 tok/s M2 Pro; ~60-80 tok/s M3 Max
- **Memory**: Uses unified memory; ~4-5 GB for 7B Q4
- **Limitation**: macOS only
- **Best for**: macOS-only projects

---

## 2. CRITICAL Architecture Decision: Ollama + Outlines Incompatibility

**Outlines does NOT integrate with Ollama's HTTP API.** Supported backends:
- transformers (HuggingFace)
- llama-cpp-python
- vLLM (built-in)

### Resolution Options
1. Drop Outlines, use Ollama's native JSON schema (simpler, less powerful)
2. **Use llama-cpp-python as secondary backend for Outlines** (RECOMMENDED)
3. Use vLLM instead of Ollama (heavier, Linux-focused)

### Recommended Two-Tier Architecture
- **Layer 3**: llama-cpp-python + Outlines (constrained generation)
- **Layer 4**: Ollama (free-form reasoning, streaming)

---

## 3. Outlines Grammar-Constrained Generation

- **Latest**: Outlines 0.1.x (under `dottxt-ai/outlines`)
- **License**: Apache 2.0

### How It Works
1. Pre-computes FSM/pushdown automaton from Pydantic model / JSON schema / regex / EBNF grammar
2. At each decoding step, masks invalid tokens (logits → -∞)
3. Every generated sequence guaranteed valid

### Supported Constraints
- JSON Schema / Pydantic models: `outlines.generate.json(model, SchemaClass)`
- Regex: `outlines.generate.regex(model, pattern)`
- Context-free grammar (EBNF): `outlines.generate.cfg(model, grammar_string)`
- Choice: `outlines.generate.choice(model, ["opt1", "opt2"])`

### Performance
- Index building: One-time 1-30s, cached after first build
- Per-token overhead: ~1-5% throughput reduction
- Memory: ~10-50 MB for FSM index
- Net effect: Eliminates retries for malformed output

---

## 4. Qwen2.5-Coder 7B Benchmarks

| Benchmark | Score | Notes |
|-----------|-------|-------|
| HumanEval (Python) | ~84-88% pass@1 | Best-in-class 7B |
| HumanEval+ | ~80-82% pass@1 | Stricter tests |
| MBPP | ~76-80% pass@1 | Multi-language |
| BigCodeBench (Full) | ~40-45% | Complex tasks |
| MultiPL-E (Python) | ~82-85% | |
| MultiPL-E (Java) | ~72-76% | |
| Aider polyglot | ~30-40% | **Primary target** |

### vs Competitors at 7B Scale

| Model | HumanEval | MBPP |
|-------|-----------|------|
| **Qwen2.5-Coder-7B-Instruct** | ~84-88% | ~76-80% |
| DeepSeek-Coder-V2-Lite | ~80-82% | ~73-76% |
| CodeLlama-7B-Instruct | ~40-45% | ~52-55% |
| StarCoder2-7B | ~35-40% | ~55-58% |
| Yi-Coder-9B-Chat | ~78-82% | ~72-75% |

**Qwen2.5-Coder-7B is clearly the best 7B code model.**

### Inference Performance (Q4_K_M)
- VRAM: ~4.5 GB (weights) + ~1.5 GB (KV cache 8K) = ~6 GB
- Throughput: 30-50 tok/s RTX 3060/3070; 40-60 tok/s RTX 4070
- Time-to-first-token: ~200-500ms

---

## 5. GGUF Quantization Quality Loss

| Quant | Bits/Weight | Size (7B) | Quality vs FP16 |
|-------|-------------|-----------|-----------------|
| Q2_K | ~2.6 | ~2.8 GB | Severe (>10% drop) |
| Q3_K_M | ~3.4 | ~3.5 GB | Noticeable (~5-8%) |
| **Q4_K_M** | **~4.8** | **~4.5 GB** | **Mild (~1-3%)** |
| Q5_K_M | ~5.7 | ~5.3 GB | Minimal (<1%) |
| Q6_K | ~6.6 | ~6.0 GB | Near-lossless (<0.5%) |
| Q8_0 | 8.0 | ~7.5 GB | Lossless |

**Q4_K_M is the sweet spot for 8GB VRAM target.**

---

## 6. Small Models for Layer 3 (1B-3B)

### Recommended: Qwen2.5-Coder-1.5B-Instruct (Q4_K_M)
- HumanEval: ~70-74% pass@1
- Memory: ~1.0-1.2 GB
- Throughput: 80-120 tok/s GPU; 30-50 tok/s CPU
- Same model family as 7B (consistent tokenizer)

### Fallback: Qwen2.5-Coder-3B-Instruct
- HumanEval: ~76-80% pass@1
- Memory: ~2.0-2.2 GB
- Throughput: 60-90 tok/s GPU

### Dual-Model Memory Budget
| Component | VRAM |
|-----------|------|
| Qwen2.5-Coder-7B Q4_K_M (Layer 4) | ~4.5 GB |
| Qwen2.5-Coder-1.5B Q4_K_M (Layer 3) | ~1.0 GB |
| KV cache (7B, 8K context) | ~1.5 GB |
| KV cache (1.5B, 4K context) | ~0.3 GB |
| **Total** | **~7.3 GB** |

Fits within 8 GB VRAM.

---

## 7. Python Ollama Client (Async Streaming)

```python
# Async streaming example
from ollama import AsyncClient

async def stream_chat(prompt: str):
    client = AsyncClient()
    async for chunk in await client.chat(
        model='qwen2.5-coder:7b-instruct-q4_K_M',
        messages=[{'role': 'user', 'content': prompt}],
        stream=True,
    ):
        yield chunk['message']['content']
```

### Structured Output via Ollama (Layer 4)
```python
response = ollama.chat(
    model='qwen2.5-coder:7b-instruct-q4_K_M',
    messages=[...],
    format=MyPydanticModel.model_json_schema(),  # v0.5+ JSON schema
)
```

### Constrained Output via Outlines (Layer 3)
```python
from llama_cpp import Llama
from outlines.models.llamacpp import LlamaCpp
from outlines import generate

llm = Llama(model_path="path.gguf", n_gpu_layers=-1, n_ctx=4096)
model = LlamaCpp(llm)
generator = generate.json(model, EditInstruction)
result = generator(prompt)  # Always valid
```

---

## Key Takeaways for HybridCoder

1. **Two-tier inference**: Ollama (Layer 4) + llama-cpp-python/Outlines (Layer 3)
2. **Qwen2.5-Coder family**: 7B for reasoning, 1.5B for constrained generation
3. **Q4_K_M quantization**: Best cost/quality tradeoff for 8GB VRAM
4. **Aider benchmark ~30-40%**: Realistic for 7B; prompt engineering + LLMLOOP critical
5. **Total VRAM budget ~7.3 GB**: Both models fit in 8 GB simultaneously
