# Executive Summary  
To turn your agent’s usage logs into **training-ready datasets**, we must log each coding task as an *append-only event stream* with rich context and outcomes. Key data include: task metadata, selected context (files/snippets), each model draft, human edits, tool calls/results, and final accepted answer/patch, along with test/build outcomes. Store large blobs (file contents, diff patches, tool outputs) separately by content-hash (e.g. SHA-256), keeping only compact references in the log【29†L150-L158】. Use a stable chat message schema (system/user/assistant roles) when saving prompts and outputs so later TRL training can reapply the GLM chat template correctly【15†L212-L222】【7†L131-L140】. 

Nightly pipelines then **assemble** (prompt → completion) pairs for SFT and (prompt, chosen, rejected) tuples for preference tuning. Store SFT data as JSONL with fields like `{"prompt":[...],"completion":[...]}` or TRL’s conversational format【7†L129-L138】. Preference data can use either explicit prompts (`"prompt","chosen","rejected"`) or the implicit format (`"chosen","rejected"` plus shared prompt)【7†L139-L148】【15†L212-L222】. 

For fine-tuning GLM‑4.7-30B (MoE) with LoRA/QLoRA, plan for **4–16-bit adapters**: QLoRA (4-bit base) often lets a 30B fit in ~20–30 GB of GPU VRAM【24†L229-L236】【27†L71-L79】, whereas 16-bit LoRA needs ~40–80 GB (e.g. ~60 GB as seen on GLM-4.7-Flash【36†L286-L294】). Multi-GPU or advanced engines (DeepSpeed/Accelerate) may be used. Use LoRA ranks in the tens or low hundreds (8–128) and AdamW with a small LR (e.g. 1e-4–5e-4 for LoRA weights) and linear warmup. Checkpoints should be frequent (per epoch or step) since dataset sizes may be modest. After training, save the LoRA adapter in **safetensors** format. To use in Ollama, create a Modelfile with `FROM zai-org/GLM-4.7-Flash` and `ADAPTER path/to/adapter`, then run `ollama create`【10†L100-L109】.  

Evaluation: keep a held-out set of representative coding issues. Check automated metrics on it: **build/test pass rate**, lint/style score, diff size (lines changed), and “does output compile?”. Also sample human comparisons: can domain experts label new vs old answers? Monitor for regressions. Continually scan logs for PII/secrets (e.g. regex or tools like `detect-secrets`) and remove any such events【29†L150-L158】. Before rollout, test the fine-tuned agent end-to-end on a canary set. Use a canary deployment (e.g. route 5–10% traffic) and have a rollback plan if new errors or hallucinations spike.  

**References:** We follow best practices from HuggingFace TRL (SFT & DPO formats【7†L129-L138】【15†L212-L222】), Unsloth (MoE LoRA tips【36†L286-L294】), Ollama docs (LoRA import【10†L100-L109】), and architecture guides on event logs and content-addressed storage【12†L362-L370】【29†L150-L158】.  

```mermaid
flowchart LR
    ES[Task Start / Episode] -->|selects| Ctx[Context Selection (files/snippets)]
    Ctx --> AM[Assistant Draft Output (raw)]
    AM -->|human edits| HM[Human Edits / Patch]
    HM --> TCall[Tool Call (e.g. tests, lint)]
    TCall --> TRes[Tool Result (e.g. test output)]
    TRes --> FM[Final Assistant Output]
    FM --> St[SFT Record]
    HM --> Pref[Preference Pair (chosen vs draft)]
    FM --> Pref
```

## 1. Event schema and storage layout  

- **Event Stream (append-only):** Each task/issue is an “episode” with a unique `episode_id`. Within it, log every step with a timestamp:  
  - `task_start`: includes metadata (repo, branch, ticket text, timestamp).  
  - `context_selected`: which files/snippets were provided to the model (with content-hash and snippet).  
  - `assistant_response`: the model’s output (draft and final).  
  - `human_edit`: any user modifications (diff against draft).  
  - `tool_call`: commands executed (e.g. compile, tests) and their outputs.  
  - `outcome`: e.g. tests passed/failed, lint results.  
  - `task_end`: final commit hash or summary result.  

- **Content-addressed store:** Put large text (file contents, diffs, tool stdout) in an object store or file system, keyed by SHA-256. The event holds only the hash (and a short snippet). This deduplicates content【29†L150-L158】. For example, a `context_selected` event might list files by path, hash, and first few chars. For tool results, store exit code and truncated output.  

- **JSON schema example:**  
  ```jsonc
  {
    "episode_id": "2026-02-14T10:12:33Z__repoX__issue123",
    "repo": {"name": "repoX", "url": "git@..."},
    "task": {"id": "ISSUE-123", "title": "Fix NPE", "description": "..."},
    "events": [
      {"t": "2026-02-14T10:12:35Z", "type": "context_selected", 
       "files": [
         {"path": "src/PaymentStatusProcessor.java", "sha256": "abc123...", 
          "snippet": "public class PaymentStatusProcessor {"},
         {"path": "src/util/StringUtils.java",  "sha256": "def456...", "snippet": "public class StringUtils {"}
       ]},
      {"t": "2026-02-14T10:13:10Z", "type": "assistant_response", 
       "response_id": "draft1", 
       "role": "assistant", "content": "Here is a patch...", 
       "accepted": false},
      {"t": "2026-02-14T10:14:05Z", "type": "human_edit", 
       "based_on": "draft1", 
       "diff": "*** Begin Patch\n*** Update File: src/PaymentStatusProcessor.java\n@@ -42,6 +42,7 @@\n+    if (payment == null) return;\n*** End Patch"},
      {"t": "2026-02-14T10:14:30Z", "type": "tool_call", 
       "tool": "pytest", "input": {"cmd": "pytest -q"}, 
       "output": {"exit_code": 0, "stdout": "...tests passed..."}}, 
      {"t": "2026-02-14T10:14:45Z", "type": "assistant_response", 
       "response_id": "final", 
       "role": "assistant", "content": "Patch applied.", 
       "accepted": true},
      {"t": "2026-02-14T10:15:00Z", "type": "task_end", 
       "final_commit": "def789", 
       "outcome": {"tests_pass": true, "lint_pass": true}}
    ]
  }
  ```
  Each event row is minimal (small JSON with timestamps). Large content (full file text, full output) lives outside, keyed by hash【29†L150-L158】.  

- **Storage options:** Use a fast metadata store (e.g. PostgreSQL or NoSQL) for events, and scalable object storage for content (e.g. S3 or a blob store). Key–value stores (e.g. Redis) can cache hot context. See table below for trade-offs:  

  | Storage Tier       | Purpose                       | Pros                                 | Cons                        |
  |--------------------|-------------------------------|--------------------------------------|-----------------------------|
  | Relational DB      | Event metadata                | ACID transactions, easy querying     | Large blob storage inefficient |
  | NoSQL / Timeseries | Event log (append-only schema)| Horizontal scalability, fast writes  | Complex queries can be harder |
  | Object store (S3)  | File/patch/tool-output blobs  | Cheap, dedup (by hash), scalable     | No real-time query (need index) |
  | Cache (Redis)      | Hot context snippets/results  | Low-latency reads                    | Size limited, not persistent |

  In practice, we store only hashes and short text in the DB and offload full content to objects. This is like “content-addressed” logging【29†L150-L158】【12†L362-L370】.

- **Retention & Redaction:** Keep all event logs for reproducibility, but purge sensitive data before training. Scan for PII or secrets (e.g. API keys, user emails) via regex or tools and strip/replace them. Ensure compliance by redacting any proprietary code or client data【29†L150-L158】.

```mermaid
flowchart LR
    LogStore[Event Store (DB)] --> Pipeline[Daily ETL Pipeline]
    Pipeline --> SFT[Generate SFT Dataset]
    Pipeline --> PREF[Generate Preference Dataset]
    SFT --> {Train SFT Model}
    PREF --> {Train DPO/RL Model}
    {Train SFT Model} --> Check[Validation Checks]
    {Train DPO/RL Model} --> Check
```

## 2. Generating Datasets for TRL  

Each night (or regularly), run a pipeline that:
- **Assembles SFT examples:** For each episode, take the sequence of messages (including the system prompt and user query) and the *final accepted assistant reply*. Output as e.g.:  
  ```json
  {"prompt":[{"role":"system","content":"Use diff-first style."},
             {"role":"user","content":"Fix bug in X"}],
   "completion":[{"role":"assistant","content":"---PATCH---"}]}
  ```  
  The TRL SFTTrainer accepts “prompt+completion” format (or conversational `messages` with `assistant` role)【7†L129-L138】. Ensure the same chat template is used as in inference.

- **Extracts Preference pairs:** Whenever a draft was rejected (or edited), output a pair: prompt + chosen output vs prompt + rejected output. E.g.:  
  ```json
  {"prompt":[{"role":"system","content":"...rules..."},{"role":"user","content":"Fix X"}],
   "chosen":[{"role":"assistant","content":"Final patch."}],
   "rejected":[{"role":"assistant","content":"Original draft patch."}]}
  ```  
  This fits TRL’s DPOTrainer format【15†L212-L222】. We recommend using explicit prompts and structured roles for clarity【15†L212-L222】. 

- **Formatting options:** TRL supports JSONL, HuggingFace datasets, etc.【7†L129-L138】. Using a single JSONL with keys (`prompt`,`completion` or `messages`) is simplest. Keep both conversational (with `"role"`) and standard (plain text) examples if needed.  

- **Example pipeline step:** A Spark or Python job reads new events, filters accepted vs draft, and writes two files: `train_sft.jsonl` (prompt+final answer) and `train_pref.jsonl` (prompt/chosen/rejected). Use schema from TRL docs (see table in TRL “Dataset formats”【7†L129-L138】).  

## 3. Fine-Tuning Recipe (GLM‑4.7-30B)  

- **LoRA vs QLoRA:** We suggest starting with QLoRA (4-bit) for memory savings, then optionally full LoRA as needed. For a 30B model, QLoRA can often fit in a **48GB GPU** (e.g. NVIDIA A6000/A40) with careful config, since previous work shows ~20–30 GB usage【24†L229-L236】【27†L71-L79】. (By contrast, 16-bit LoRA might need ~60–80 GB, pushing multi-GPU or A100-80GB setups【36†L286-L294】【24†L229-L236】.)  

- **Hardware:** At minimum, one high-memory GPU (>=48GB) for QLoRA. Two mid-tier GPUs (e.g. 2×24GB) with `accelerate` or `DeepSpeed ZeRO-1` can also work for LoRA. Multi-GPU with tensor-parallelism is supported by GLM’s HF implementation. Unsloth’s benchmarks show ~15% VRAM reduction and 2–3× speedup for GLM-4.7 Flash with optimized kernels【19†L438-L446】【21†L531-L540】.  

- **Training steps:** First **SFT phase** on accepted examples: fine-tune the model (with frozen base weights) on the collected prompts→final responses. Use a small learning rate (e.g. 1e-4) on LoRA adapters, for a few epochs (e.g. 3–5) or until convergence. Use gradient accumulation for large batch-equivalent sizes if VRAM is limited. Save LoRA checkpoints each epoch. Then **DPO** (or another preference optimization) on the chosen vs rejected pairs【15†L212-L222】. DPO in TRL is straightforward (no extra reward model needed) once you have `(prompt, chosen, rejected)` data.  

- **Hyperparameters:** Typical settings (to adapt):  
  - *LoRA rank:* 8–64 (higher may improve fit but uses more memory).  
  - *Optimizer:* AdamW or Lion; small LR (1e-4 to 5e-4) and weight decay ~0.  
  - *Batch:* As large as fits; use gradient-accumulate to simulate 16–32 batch if needed.  
  - *Scheduler:* linear decay with warmup (e.g. 100–1000 steps).  
  - *Precision:* 4-bit base + 16-bit gradients (QLoRA) or 16-bit base. BitsAndBytes NF4 is recommended for 4-bit.  
  - *Other:* Freeze the MoE router and other non-expert params to reduce instability【36†L300-L307】.  

- **Checkpoints:** Save adapter weights and optimizer state every epoch. Keep at least last 3 checkpoints, and consider early stopping if validation loss stalls or performance degrades on held-out tasks.

- **Produce adapters for Ollama:** After training, export the LoRA adapter as safetensors. In an Ollama `Modelfile`, reference the base GLM-4.7-Flash and your adapter:  
  ```
  FROM zai-org/GLM-4.7-Flash
  ADAPTER /path/to/adapter_dir
  ```  
  Then `ollama create my-agent -f Modelfile`. Ollama supports importing HuggingFace-format LoRA safetensors【10†L100-L109】.

## 4. Evaluation & Monitoring  

- **Hold-out set:** Reserve a set of coding tasks (new issues or issues set aside) for evaluation. Treat these as unseen “test episodes.” After each training round, run the fine-tuned agent on these tasks.  

- **Automated checks:** For each output, run existing project *unit tests, linters, type-checkers*, and measure pass/fail. Compute metrics: **test-pass rate**, **lint errors count**, and **diff size** (e.g. lines changed). Compare to the base model’s performance to ensure no regressions.  

- **Human evaluation:** Periodically sample agent responses on random tasks. Have engineers rate if the answer is better/equal/worse than the original model’s. This yields a *preference metric*.  

- **Metrics:** Track cross-entropy loss on a validation split of SFT data, accuracy of choosing “better” responses in preference data, etc. TRL’s DPO trainer logs `rewards/chosen` vs `rejected` metrics【15†L269-L278】 which can quantify alignment gains.  

- **Data drift and safety:** Monitor incoming logs for changes: e.g. if context or task distribution shifts. Periodically re-run a quality check pipeline on recent data. Use automated PII detectors or secret scanners to flag sensitive content【29†L150-L158】. Filter any new private data before it enters training.

- **Rollback plan:** Use canary/AB testing. For rollout, deploy the fine-tuned agent in staging and compare key metrics (test pass rate, code coverage) to the baseline. Gradually increase traffic. If error rates rise or performance drops, revert to the previous adapter. Maintain the last known-good adapter and training data snapshot for quick rollback.

## 5. Checklists & Best Practices  

- [ ] **Consistently log:** Enforce schema on every log write (ensuring each event type has required fields).  
- [ ] **Capture drafts vs finals:** Always record both model drafts and human-edited final answers for preference learning.  
- [ ] **Content-address:** Store text blobs by hash【29†L150-L158】, never inline large data.  
- [ ] **Daily ETL job:** Implement a pipeline to produce TRL-compatible JSONL datasets for SFT and preferences.  
- [ ] **Anonymize data:** Run PII/secret filters nightly, and drop/replace any hits before training.  
- [ ] **Adaptive compute:** Start with QLoRA on one GPU (e.g. 48GB). If VRAM is insufficient or performance lagging, scale up (more GPUs or switch to 16-bit LoRA on higher-memory hardware).  
- [ ] **Hyperparam tuning:** Experiment with LoRA ranks (64,128), LR (1e-4–5e-4), and batch sizes. Validate on held-out tasks.  
- [ ] **Evaluation suite:** Automate builds/tests on agent outputs and integrate into CI. Include prompts for common bug types.  
- [ ] **Version adapters:** Tag each adapter release with metadata (training data snapshot, epochs, commit). Use Ollama Modelfile to keep base+adapter versions clear.  
- [ ] **Monitor drift:** Check performance on validation set every few weeks. If drop is detected, trigger data refresh or retraining.  

**Sources:** Methodology follows TRL dataset guidelines【7†L129-L138】【15†L212-L222】, Ollama adapter instructions【10†L100-L109】, and MoE fine-tuning best practices【36†L286-L294】【36†L300-L307】. Event-log design draws on “system of record” event logs【12†L362-L370】 and content-addressed storage patterns【29†L150-L158】. Compute planning uses VRAM estimates from QLoRA papers and community reports【24†L229-L236】【27†L71-L79】.