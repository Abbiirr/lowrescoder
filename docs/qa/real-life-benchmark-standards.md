# Real-Life Coding-Agent Benchmark Standards (Reference)

Updated: 2026-02-12

## Common Real-World Benchmarks

1. SWE-bench / SWE-bench Verified
   - Real GitHub issue resolution on real repositories.
   - https://github.com/SWE-bench/SWE-bench
   - https://openai.com/index/introducing-swe-bench-verified/

2. Aider benchmark suite / leaderboard
   - Practical code-editing and refactoring task comparisons across coding agents.
   - https://aider.chat/docs/leaderboards/
   - https://github.com/Aider-AI/aider/tree/main/benchmark

3. WebArena
   - End-to-end web task completion benchmark for autonomous agents.
   - https://webarena.dev/
   - https://github.com/web-arena-x/webarena

4. Web-Bench
   - Realistic web development and app-building evaluation tasks.
   - https://github.com/bytedance/web-bench

5. WebGen-Bench
   - Functional website generation benchmark (from prompts to working web artifacts).
   - https://arxiv.org/abs/2505.03733

## How This Repo Uses These Standards

- We keep synthetic fast benchmarks for daily regression (`tests/benchmark/`).
- We add one real-life functional project task benchmark:
  - `tests/benchmark/test_project_creation.py`
  - Task: score a generated React calculator app against a practical rubric.
  - External target projects can be scored via:
    - `AUTOCODE_BENCH_TARGET_DIR=<path>`
    - optional `AUTOCODE_BENCH_RUN_NODE=1`
