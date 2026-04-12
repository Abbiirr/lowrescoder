# Research References

All external benchmarks, papers, and sources used to design the agentic benchmark plan.

---

## Tier 1: Directly Applicable (High Priority)

### SWE-bench Family
- **SWE-bench** — Real GitHub issue resolution across 12 Python repos (2,294 tasks)
  - Paper: https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html
  - GitHub: https://github.com/SWE-bench/SWE-bench
  - Key finding: Scaffold choice causes up to 15% performance delta on same model

- **SWE-bench Verified** — Curated 500-task subset with human-verified tests
  - https://openai.com/index/introducing-swe-bench-verified/
  - Verdent scaffold analysis: https://www.verdent.ai/blog/swe-bench-verified-technical-report

- **SWE-bench Pro** — Long-horizon tasks (107 lines avg, 4.1 files avg) from 41 repos
  - Paper: https://arxiv.org/pdf/2509.16941
  - https://scale.com/research/swe_bench_pro

- **SWE-EVO** — Multi-PR codebase evolution tasks (21 files avg, 874 tests avg)
  - Paper: https://arxiv.org/abs/2512.18470

- **SWE-bench Architecture Analysis** — 7 scaffold archetypes compared
  - Paper: https://arxiv.org/html/2506.17208v2
  - Key finding: No single architecture wins — different scaffolds excel at different problem types

- **SWE-bench Skill Analysis** (Epoch AI)
  - https://epoch.ai/blog/what-skills-does-swe-bench-verified-evaluate
  - Key finding: 87% bug fixes, 39% trivial (<15 min), only 8% medium complexity

### Terminal-Bench
- **Terminal-Bench** — 89 real terminal tasks in Docker sandboxes
  - Paper: https://arxiv.org/html/2601.11868v1
  - Website: https://www.tbench.ai/
  - Key finding: Execution errors (24.1%) and coherence errors are top failure modes

- **Terminal-Bench 2.0** — Expanded evaluation
  - https://snorkel.ai/blog/terminal-bench-2-0-raising-the-bar-for-ai-agent-evaluation/

### Recovery-Bench
- **Recovery-Bench** — Recovery from prior agent failures
  - https://www.letta.com/blog/recovery-bench
  - Key finding: Recovery is orthogonal to fresh-state ability. Best coder != best recoverer. Average 57% accuracy loss in corrupted state.

### ReliabilityBench
- **ReliabilityBench** — Chaos engineering for agents
  - Paper: https://arxiv.org/abs/2601.06112
  - Key finding: ReAct beats Reflexion under faults (80.9% vs 67.3% recovery)
  - Defines R(k, epsilon, lambda) reliability surface

### ContextBench
- **ContextBench** — Context retrieval quality measurement
  - Paper: https://arxiv.org/html/2602.05892v1
  - Key finding: Retrieval quality is separable from patch quality

---

## Tier 2: Methodology Applicable (Medium Priority)

### Aider Benchmarks
- **Aider Polyglot** — 225 Exercism problems across 6 languages, two-attempt protocol
  - https://aider.chat/docs/benchmarks.html
  - https://aider.chat/docs/leaderboards/
  - Key finding: Edit format compliance is the #1 agent-layer variable

- **Aider Architect/Editor Pattern**
  - https://aider.chat/2024/09/26/architect.html
  - Key finding: Splitting reasoning from editing produces SOTA results

### EDIT-Bench
- **EDIT-Bench** — 540 real code edit problems (ICML 2025)
  - Paper: https://arxiv.org/abs/2511.04486
  - Key finding: Only 1 of 40 models scored above 60%. Performance varies 11% based on context provided.

### FeatBench
- **FeatBench** — Feature implementation with regression checks (F2P + P2P)
  - Paper: https://arxiv.org/html/2509.22237v1
  - Key finding: P2P (Pass-to-Pass) tests catch regressions that F2P misses

### tau-bench / tau2-bench
- **tau-bench** — Tool-agent-user consistency
  - https://sierra.ai/blog/benchmarking-ai-agents
  - Key finding: pass^k metric reveals exponential reliability decay

### LoCoBench-Agent
- **LoCoBench-Agent** — Long-context SE (10K to 1M tokens, 8 tool types)
  - Paper: https://arxiv.org/abs/2511.13998
  - Key finding: "Strategic tool usage patterns differentiate high-performing agents"

### ACE-Bench
- **ACE-Bench** — Feature development (not just bug fixes)
  - Paper: https://openreview.net/forum?id=41xrZ3uGuI
  - Key finding: Claude 4 Sonnet: 70.4% SWE-bench but only 7.5% ACE-Bench

### Confucius Code Agent
- **CCA** — Scalable scaffold with context compression
  - Paper: https://arxiv.org/html/2512.10398v3
  - Key finding: Context compression provides +6.6 point boost. Weaker model + strong scaffold beats stronger model + weak scaffold.

---

## Tier 3: Conceptual / Future Reference

### BFCL (Berkeley Function Calling Leaderboard)
- V4: https://gorilla.cs.berkeley.edu/leaderboard.html
- Measures: function call accuracy, parallel calls, multi-turn, relevance detection

### MCP-AgentBench / MCP-Bench
- Paper: https://arxiv.org/pdf/2509.09734
- Paper: https://arxiv.org/abs/2508.20453
- 188 tools across 33 MCP servers, 6 complexity levels

### IDE-Bench
- Paper: https://arxiv.org/html/2601.20886v2
- 80 multi-file tasks across 8 domains with IDE tool access

### EvoCodeBench
- Paper: https://arxiv.org/abs/2602.10171
- Iterative refinement — measures improvement across revision rounds

### TRAIL (Trace Reasoning and Agentic Issue Localization)
- https://www.patronus.ai/blog/introducing-trail-a-benchmark-for-agentic-evaluation
- 148 annotated traces, 841 errors, meta-evaluation of agent behavior

### CORE-Bench
- Paper: https://arxiv.org/abs/2409.11363
- Computational reproducibility of scientific papers

### AgentBench
- Paper: https://arxiv.org/abs/2308.03688
- 8-domain multi-task evaluation

### ToolBench
- GitHub: https://github.com/OpenBMB/ToolBench
- 16,000+ APIs, 3,451 tools

### Web-Bench
- GitHub: https://github.com/bytedance/web-bench
- 50 projects x 20 sequential tasks for web development

### SWE-Lancer
- https://openai.com/index/swe-lancer/
- Real freelance SWE tasks with economic framing

---

## Meta-Resources

### Benchmark Compendiums
- AI Agent Benchmark Compendium (50+ benchmarks): https://github.com/philschmid/ai-agent-benchmark-compendium
- Agent Harness 2026: https://www.philschmid.de/agent-harness-2026

### Evaluation Methodology Guides
- Anthropic: Demystifying Evals for AI Agents: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic: Quantifying Infrastructure Noise: https://www.anthropic.com/engineering/infrastructure-noise
- Promptfoo: Evaluate Coding Agents: https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/

### Code Edit Analysis
- Code Surgery (file edit patterns): https://fabianhertwig.com/blog/coding-assistants-file-edits/
- SWE-bench Python syntax error analysis: https://arxiv.org/html/2410.12468v2

### Agent Architecture Studies
- Anthar Study (beyond benchmarks): https://www.deccan.ai/research/anthar-study-evaluating-ai-coding-agents-beyond-benchmarks
- Beyond Task Completion Framework: https://arxiv.org/html/2512.12791v1
- Rethinking Coding Agent Benchmarks: https://medium.com/@steph.jarmak/rethinking-coding-agent-benchmarks-5cde3c696e4a
- Reliability Gap (enterprise agents): https://simmering.dev/blog/agent-benchmarks/

### Additional Benchmarks
- LiveCodeBench: https://livecodebench.github.io/
- Multi-SWE-bench: https://github.com/multi-swe-bench/multi-swe-bench
- MLE-bench (ML engineering): https://openai.com/index/mle-bench/
- ML-Bench: https://ml-bench.github.io/
- MLAgentBench: https://arxiv.org/abs/2310.03302
- LOCA-bench (context scaling): https://arxiv.org/html/2602.07962
- Context-Bench (Letta): https://www.letta.com/blog/context-bench
- AgentLongBench: https://arxiv.org/abs/2601.20730
- Saving SWE-Bench (mutation analysis): https://arxiv.org/abs/2510.08996
