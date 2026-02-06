# Design Document: Low-Resource, High-Performance Hybrid AI Coding Agent

**Author:** Manus AI
**Date:** January 27, 2026
**Goal:** To design a very low-resource capable coding agent, implemented as a CLI tool, that harnesses the power of non-LLM AI for most tasks and uses small LLMs (7-11B parameters) sparingly, with a performance target on par with Claude Code for Python and Java development.

## 1. Executive Summary: The Hybrid Layered Intelligence Architecture

The goal of achieving Claude Code-level performance while minimizing resource consumption is highly ambitious, but entirely feasible by leveraging the formal structure of code. The proposed solution is a **Hybrid Layered Intelligence Architecture** [1], which treats the Large Language Model (LLM) as the **last resort** rather than the first choice. This architecture is designed to handle 60-80% of coding assistance tasks with zero or minimal LLM tokens by exhausting cheaper, deterministic methods first [1].

Beyond intelligence, the **User Experience (UX)** must match the polish of professional tools like Claude Code. This requires a sophisticated **Terminal User Interface (TUI)** that supports flicker-free streaming, concurrent input, and rich tool-call visualizations [11]. By combining `prompt_toolkit` for input and `Rich` for rendering, the agent can provide a high-fidelity, local-first development experience [11].

The core principle is a **cascading system** that routes queries through four distinct layers of intelligence, ensuring that only the most complex, ambiguous tasks are escalated to the LLM [1]:

1.  **Deterministic Analysis (Non-LLM):** Handles syntax, type checking, and pattern matching instantly.
2.  **Retrieval and Context (Minimal LLM):** Provides relevant code snippets and project rules using efficient hybrid search.
3.  **Constrained Generation (Efficient LLM):** Uses small, local LLMs to generate syntactically guaranteed code completions and simple edits.
4.  **Full Reasoning (Targeted LLM):** Engages the LLM for complex planning, multi-step refactoring, and ambiguous natural language interpretation.

## 2. Core Architectural Design: Cascading Intelligence

The agent operates as a **layered intelligence system** [1], where each layer is responsible for a progressively more complex and less deterministic set of tasks.

| Layer | Primary Intelligence Source | Resource Consumption | Typical Latency | Example Task |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1** | Deterministic Tools (Tree-sitter, LSP, Static Analyzers) | Zero LLM Tokens | Sub-millisecond to 50ms | "Find all usages of `UserService`" |
| **Layer 2** | Hybrid RAG (LanceDB, Embeddings) | Minimal LLM Tokens (for embedding/re-ranking) | 100ms - 500ms | "Retrieve code for `handle_auth_token`" |
| **Layer 3** | Small Local LLM (7B-11B) + Grammar Constraint | Low (Local Inference) | 500ms - 2s | "Complete the function signature" |
| **Layer 4** | Medium/Large Local LLM (7B) + Agentic Workflow | Moderate (Local Inference) | 5s - 30s | "Refactor `User.java` to use the new `AuthService`" |

The **Cascading System** logic is critical:
1.  A user request is first checked against Layer 1 (e.g., "Is this a known pattern match?").
2.  If Layer 1 fails, the system moves to Layer 2 to enrich the context (e.g., "What relevant code/docs exist?").
3.  If context is sufficient, Layer 3 attempts a constrained, fast generation.
4.  Only if all previous layers fail or the task is inherently complex (e.g., multi-file planning) is the request escalated to Layer 4, which uses the full reasoning power of the small LLM [1].

## 3. Layer 1: Deterministic Intelligence (The Non-LLM Core)

The foundation of the agent is classical code intelligence, which provides deterministic, low-latency, and highly accurate information [1].

### 3.1. Abstract Syntax Tree (AST) and Incremental Parsing
**Tree-sitter** is the universal foundation for code understanding [1]. It provides:
*   **Incremental Parsing:** Sub-millisecond updates, essential for a responsive CLI tool.
*   **Error Tolerance:** Continues parsing despite syntax errors, crucial during active coding.
*   **Structural Pattern Matching:** Uses S-expressions for powerful, non-regex-based code queries [1].

### 3.2. Language Server Protocol (LSP) Integration
LSP operations deliver high-quality, type-aware code intelligence at low latency [1].
*   **Python:** **Pyright** provides exceptional static type inference, even without explicit type annotations [2].
*   **Java:** **Eclipse JDT** (in headless mode) exposes the full Java type system programmatically, enabling operations like `textDocument/references` and `textDocument/definition` [3].

### 3.3. Static Analysis and Pattern Matching
**Semgrep** is recommended for its speed and ease of rule creation [4].
*   **Function:** A rules-based system can deterministically catch hardcoded credentials, SQL injection patterns, and style violations [1].
*   **Refactoring:** Simple refactoring tasks can be handled by Semgrep rules combined with AST transformation, bypassing the LLM entirely [1].

## 4. Layer 2: Context and Retrieval (The Efficient RAG Layer)

The Retrieval-Augmented Generation (RAG) layer is optimized to provide the most relevant context while minimizing the token count sent to the LLM.

### 4.1. AST-Aware Code Chunking
Traditional line-based chunking is inefficient for code. **AST-aware chunking** (e.g., using a Tree-sitter based approach like `astchunk`) is mandatory, as it outperforms line-based methods by 5.5+ points on code retrieval benchmarks [1] [5].

### 4.2. Hybrid Search and Vector Database
**Hybrid Search** (semantic + keyword/BM25) is essential, as research shows 74-76% of results from each method are distinct [1].
*   **Vector Database:** **LanceDB** is recommended for local vector storage with built-in hybrid search capabilities [6].
*   **Embeddings:** **voyage-code-3** is the current state-of-the-art, outperforming alternatives like OpenAI-v3-large by over 13% on code retrieval tasks [7].

## 5. Layer 3 & 4: LLM Integration (Targeted and Optimized Use)

The LLM is reserved for tasks that require genuine reasoning, planning, or ambiguous natural language interpretation.

### 5.1. Small Model Selection and Optimization
The target is a 7-11B parameter model that can run locally on consumer hardware.
*   **Recommended Model:** **Qwen2.5-Coder 7B** is the top open-source contender, achieving 88.4% on HumanEval [1].
*   **Quantization:** **Q4\_K\_M GGUF quantization** is the recommended default, requiring only ~4.5GB VRAM while retaining high quality [1].

### 5.2. Grammar-Constrained Generation
To eliminate syntax errors and retry loops, the LLM output must be constrained to valid syntax [1].
*   **Tooling:** **Outlines** or **SynCode** [9] can be used to compile language grammars (Python, Java) into finite state machines, masking invalid tokens during generation.

### 5.3. Agentic Workflow and Feedback Loops
*   **Architect/Editor Pattern:** A stronger model handles the high-level planning and produces plain-text instructions (the "Architect"). A smaller, faster local model then implements those instructions (the "Editor") [1].
*   **Compiler-Guided Generation (LLMLOOP):** The agent must incorporate a feedback loop that uses deterministic tools to validate LLM output [10].
*   **Git Integration:** **Atomic commits** for every AI change with a descriptive message are non-negotiable for safety and transparency [1].

## 6. Implementation Roadmap

The development follows a phased approach, integrating intelligence layers with a polished TUI.

| Phase | Title | Key Deliverables | Focus |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **TUI & REPL Foundation** | `prompt_toolkit` + `Rich` integration, `patch_stdout` setup, styled prompts, slash commands. | UX Skeleton |
| **Phase 2** | **Deterministic Core** | Tree-sitter parsing, LSP integration (Pyright/JDT), Semgrep rule execution. | Non-LLM Intelligence |
| **Phase 3** | **Context & Retrieval** | AST-aware chunking, LanceDB Hybrid Search, `AGENT.md` memory hierarchy. | Efficient RAG |
| **Phase 4** | **Streaming & Generation** | Local LLM (Qwen2.5-Coder 7B) integration, `Rich.Live` streaming with sync markers, Grammar constraints. | Optimized LLM Use |
| **Phase 5** | **Agentic Workflow** | Tool call UX (spinners/panels), Architect/Editor pattern, Compiler-guided feedback loop. | Full Agentic Capability |
| **Phase 6** | **Persistence & Polish** | SQLite session management, Auto-compaction (80% threshold), Delta rendering for flicker reduction. | Production Readiness |

## 7. Advanced UX and TUI Implementation

To rival Claude Code, the CLI must move beyond simple text input/output to a stateful, interactive environment [11].

### 7.1. The Coexistence Architecture
The single hardest TUI problem is making `Rich.Live` output and `prompt_toolkit` input share the terminal without corruption [11].
*   **Strategy:** Use `patch_stdout()` to bridge the libraries, route `Rich` output to `stderr` while `prompt_toolkit` owns `stdout`, and use `asyncio.Queue` to decouple LLM streaming from rendering [11].
*   **Flicker Reduction:** Implement **Synchronized Output (Mode 2026)** by wrapping rendering frames in `\033[?2026h` and `\033[?2026l` markers [11].

### 7.2. Progressive Streaming and Tool Visualization
*   **O(n) Markdown Rendering:** Avoid re-parsing the entire document on every token. Implement **block-level finalization**, where only the trailing incomplete block is live-updated [11].
*   **Tool UX:** Use `Rich.Status` spinners during execution and `Rich.Panel` for results. File modifications should be displayed as colored unified diffs using `Rich.Syntax` [11].
*   **Approval Modes:** Implement a 3-tier approval system: **Ask** (all tools), **Auto-edit** (read-only auto-approved), and **Full-auto** (no confirmation) [11].

### 7.3. Context and Session Management
*   **Auto-Compaction:** Monitor token usage and trigger intelligent summarization at **80% context usage** to prevent reasoning degradation [11].
*   **Project Memory:** Adopt the `AGENT.md` / `CLAUDE.md` pattern for project-level conventions, loading them hierarchically from the project root up to the home directory [11].
*   **Persistence:** Use a SQLite backend to store session history, allowing users to resume previous conversations with `--resume <ID>` or a `/resume` command [11].

## 8. Recommended Technology Stack

| Component | Recommendation | Purpose |
| :--- | :--- | :--- |
| **TUI Framework** | `prompt_toolkit` + `Rich` | Industry-standard for interactive Python CLIs. |
| **Concurrency** | `asyncio` | Handles input, streaming, and tool execution in parallel. |
| **Parsing** | Tree-sitter | Universal, incremental AST generation. |
| **Type Analysis** | Pyright (Python), Eclipse JDT (Java) | High-performance static type checking. |
| **Vector DB** | LanceDB | Local, hybrid (semantic + BM25) search. |
| **Local LLM** | Qwen2.5-Coder 7B (Q4\_K\_M) | Best-in-class performance for a small, local model. |
| **Grammar Constraint** | Outlines / SynCode | Guarantees syntactically valid code output. |
| **Persistence** | SQLite | Session and message history storage. |

***

### References

[1] Building a local-first hybrid AI coding assistant. *pasted\_content.txt*.
[2] microsoft/pyright: Static Type Checker for Python. *GitHub*.
[3] Using the Eclipse IDE for Java programming - Tutorial. *Vogella*.
[4] Semgrep: a static analysis journey. *Semgrep Blog*.
[5] Building code-chunk: AST Aware Code Chunking. *Supermemory*.
[6] Hybrid Search: Combining BM25 and Semantic Search for Better Results with LanceDB. *LanceDB Blog*.
[7] voyage-code-3: More Accurate Code Retrieval With Lower Dimensional Quantized Embeddings. *Voyage AI Blog*.
[8] DeepSeek 2.5 vs Claude 3.5 Sonnet for Coding. *Reddit*.
[9] structuredllm/syncode: Efficient and general syntactical ... *GitHub*.
[10] Reductive Analysis with Compiler-Guided Large Language Models for Input-Centric Code Optimizations. *PLDI 2025*.
[11] Building a polished inline TUI coding agent in Python. *pasted\_content\_2.txt*.
