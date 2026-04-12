# Comprehensive Operation Inventory and Harness Upgrade Proposal for AI Coding Agents

## Executive summary

AI coding agents end up “needing thousands of CLI commands” because the underlying job to be done is broad: explore and transform a repo, run toolchains, interact with networks and services, and keep state across long horizons. The practical way to build a *full inventory* is not enumerating every possible binary, flag, and shell idiom; it is defining a capability‑complete set of **operation primitives** (typed, structured) that can express *everything an agent needs*, then mapping the CLI long tail onto those primitives (and onto sandbox tiers). This report does that inventory, and then turns it into an actionable harness architecture. citeturn16view0turn13search0turn6view1

Across modern harnesses (notably those produced by entity["company","Anthropic","ai research company"] and entity["company","OpenAI","ai research company"]), several patterns have converged: (a) a small set of file+search+edit primitives, (b) a command runner for the long tail, (c) governance that combines approvals + sandboxing + policy hooks, (d) memory/compaction as first‑class infrastructure, and (e) tool‑catalog scaling via deferred tool loading and programmatic tool calling. citeturn9view1turn6view2turn6view1turn6view10turn7view1turn7view7

Bash (real shell access) is simultaneously powerful and problematic: it is untyped, parsing‑fragile, injection‑prone, portability‑limited, hard to constrain *correctly*, and often expensive in tokens/latency because it pushes the agent into verbose, step‑by‑step pipelines. A controlled “virtual bash” like just‑bash can be safer for some scenarios, but it still inherits many of bash’s semantic ambiguities and mismatches with structured tasks (e.g., SQL/AST‑like queries). citeturn13search1turn12view1turn21view0turn22search0turn22search23

The recommended harness update is a **multi‑lane execution model**:

- Lane A: **Typed host APIs** for high‑frequency operations (read/write/edit/search/git/build/test) with structured inputs/outputs and enforced limits.
- Lane B: **Specialized query engines** (ripgrep/AST/LSP/SQL) exposed as typed tools, not shell pipelines.
- Lane C: **Virtual shell** (just‑bash) for portable, low‑risk shell semantics (in‑memory or overlay FS; allowlisted network) when you want “shell fluency” without host escape.
- Lane D: **OS‑level sandboxed native commands** (e.g., sandbox‑runtime, Codex Landlock/Seatbelt) for the real long tail.
- Lane E/F: **Container / microVM / per‑sandbox VM** isolation for the highest‑risk commands and untrusted code execution. citeturn19view2turn9view5turn7view5turn6view6turn7view6turn7view3turn7view4

Finally, because recent “Claude Code leak” chatter has been exploited to distribute malware, **harness governance must assume hostile code + hostile artifacts**, including fake repos and tampered binaries. In practice, that increases the ROI of (1) sandbox‑first command execution, (2) secret‑free sandboxes, (3) allowlisted egress, and (4) signed/verified tool distribution. citeturn17news39turn17search17

## Operation taxonomy and inventory for coding harnesses

### How to interpret “full inventory” in a world of infinite CLIs

A coding agent *can* invoke thousands of commands, but most commands collapse into a finite set of **capability shapes**:

- inputs: paths / globs / text / argv / env / network targets / repo refs
- effects: read‑only vs write vs exec vs network vs privileged
- outputs: structured vs text vs streaming vs binary artifacts
- resource profile: CPU, RAM, disk IO, wall time, concurrency
- confinement needs: none / workspace / OS sandbox / container / VM

This is exactly the direction taken by modern harness docs: keep a small set of primitives (read, write/edit, glob/grep, bash) and “let the agent fetch what it needs”, while adding governance and stronger execution boundaries. citeturn9view1turn16view0turn13search0turn6view1

### Feature-by-feature inventory (primitives → current bash practice → problems → recommended lane)

The table below is intentionally “primitive‑level”: each row covers **many** concrete CLI commands (often hundreds). This is the only tractable way to deliver a comprehensive inventory while still giving concrete implementation guidance.

**Sandbox tiers used in this report**

- **T0**: Pure host read APIs (no exec)
- **T1**: Workspace write APIs (typed writes/patches)
- **T2**: Virtual shell / WASI mini-tools (no host exec)
- **T3**: OS-level sandboxed exec (native commands under Seatbelt/Landlock/bwrap etc.)
- **T4**: Container sandbox (rootless Docker + seccomp, optional gVisor)
- **T5**: MicroVM / per-sandbox VM (Firecracker / Cloudflare Sandbox-style VM isolation)

citeturn19view0turn9view5turn7view3turn7view4turn7view5turn7view6turn6view6

| Category | Feature primitive (what the harness must support) | Current standard practice (bash/CLI & common wrappers) | Bash-specific limitations | Safer / more efficient alternative | Tier | Priority (ROI × risk) |
|---|---|---|---|---|---|---|
| Workspace discovery | List directory / tree view | `ls`, `find`, `tree`; wrappers call `subprocess` or `child_process.spawn` | Parsing depends on locale, terminal widths; huge outputs; not portable flags | Typed `list_dir(path, depth, ignore)` returning JSON | T0 | High |
| Workspace discovery | Glob (pattern→paths) | `find -name`, shell globs `**/*` | Glob expansion differs by shell; injection via untrusted patterns | Typed `glob(patterns, respect_ignore)`; reuse `gitignore` rules | T0 | High |
| Content retrieval | Read file (chunked) | `cat`, `sed -n`, `head/tail` | Easy to accidentally read huge files; binary data breaks; token bloat | Typed `read_file(path, offset, limit, encoding)` (offset/limit mandatory) | T0 | High |
| Content retrieval | Read structured file (JSON/YAML/TOML) | `cat | jq`, `python -c` one-offs | Depends on tool availability; brittle pipelines | Typed `read_json(path)` / `read_yaml(path)` with schema option | T0 | High |
| Search | Regex search in files | `grep -R`, `rg` | CLI output parsing; performance varies; huge outputs | Built-in `grep(query, paths, max_hits, context)` with structured hits | T0 | High |
| Search | Fast repo search respecting ignore | `rg` | Requires ripgrep installed; output parsing | Embed ripgrep engine or ship ripgrep as a service; mirror `rg` semantics | T0/T2 | High citeturn15search2 |
| Search | Semantic search / embeddings index | ad-hoc: `ripgrep` + guess; some tools build indexes | Shell can’t express “meaning”; many tokens when over-reading | Dedicated semantic index (local) + typed `semantic_search(query, k)` | T0/T1 | Medium (depends) citeturn11view0 |
| Code intelligence | Symbol definition / references | `rg` heuristics; IDE-only otherwise | Text search misses semantics; false positives | LSP-backed tools (`definition`, `references`, `symbols`, `diagnostics`) | T0 | High citeturn9view0turn8search3turn9view2 |
| Editing | Apply patch / unified diff | `apply_patch`, `git apply`, heredocs | Line-ending issues; context mismatch; shell quoting | Typed `apply_patch(files: PatchOp[])` with preflight and dry-run | T1 | High |
| Editing | Targeted edit (replace span) | `perl -pi`, `sed -i`, editor macros | Fragile regex edits; platform differences | Typed `edit_file(path, edits=[{range,text}])` with conflict detection | T1 | High |
| Editing | Multi-file refactor | Shell loops + `sed`, `rg` + manual edits | Hard to maintain correctness; easy to over-edit; hard to rollback | LSP-assisted refactor APIs + transactional writes | T1 | High |
| Formatting | Run formatter | `prettier`, `black`, `gofmt` via bash | Tool not installed; misconfigured env; noisy output | “Formatter tool” with structured result; runs inside sandbox lane | T3/T4 | Medium |
| Git inspection | Status/diff/log | `git status`, `git diff`, `git log` | Output parsing; local config changes output; pager issues | Typed git API (libgit2) **or** constrained `git` runner returning structured diff | T0/T3 | High citeturn15search1turn15search3turn6view1 |
| Git branching | Worktrees / isolation | `git worktree add` | Easy to pollute main tree; race conditions | “Worktree manager” tool (create/cleanup) | T1/T3 | Medium citeturn15search3turn20view0 |
| Git mutation | Commit / rebase / merge | `git commit`, `git rebase` | Risky side effects; needs editor; interactive prompts | Approval-gated git mutations + policy hooks + sandboxed `git` | T3/T4 | High risk / Medium ROI citeturn21view1turn19view0 |
| Dependency install | Package manager install | `npm i`, `pip install`, `cargo build` | Requires network; supply chain risk; huge logs | Dedicated “deps” lane with allowlisted registries + caching + sandbox | T3/T4/T5 | High citeturn6view2turn19view0 |
| Build | Compile/build | `make`, `npm run build`, `cargo build` | Non-deterministic; long runtime; parallelism handling | Sandboxed build runner with streaming logs and timeouts | T3/T4/T5 | High |
| Tests | Run unit/integration tests | `pytest`, `go test`, `npm test` | Flaky tests; large output; long runtime | Test runner tool: structured failures, junit parsing, retry policy | T3/T4/T5 | High |
| Runtime | Start dev server / watch files | `npm run dev`, `uvicorn --reload` | Needs background process management | Background process API + file watching (inotify) surfaced structurally | T3/T4 | Medium citeturn3search20turn3search25 |
| Process control | Spawn/kill/ps | `ps`, `kill`, `lsof` | Unsafe to expose broadly; platform differences | Restricted process supervisor (only processes started by agent) | T3 | Medium |
| Network | Fetch docs / web pages | `curl`, `wget` | Exfil risk; redirects; TLS; parsing HTML brittle | Typed `web_fetch(url)` with allowlist + parser | T0/T3 | High citeturn18view0turn19view0 |
| Network | Call APIs (GitHub, CI, etc.) | `curl` + tokens in env | Secrets exposure; hard to audit | Typed tool calling via OpenAPI/MCP gateway (Executor-style) | T0/T1 | High citeturn12view5turn6view10 |
| Data querying | Query structured artifacts/logs | `jq`, `awk`, ad-hoc parsing | Complex queries become huge pipelines; token-heavy | Embed SQL/SQLite or dedicated query engines; hybrid verify | T2/T3 | High citeturn13search1turn12view3 |
| Context scaling | Thousands of tools | Dump all tool schemas into prompt | Context bloat; tool selection accuracy collapses | Tool search / deferred loading | T0 | High citeturn6view10turn7view7 |
| Context scaling | Multi-tool workflows | Model roundtrip per tool call | Latency + token cost; too much tool output in context | Programmatic tool calling (code writes scripts to call tools) | T0 | High citeturn7view1turn7view7 |
| Long-horizon memory | Persistent project memory | Ad-hoc notes; copy/paste; huge prompts | Context drift; repetition; forgotten constraints | Memory planes: concise index + on-demand topic files | T0 | High citeturn6view9turn16view0 |
| Long-horizon memory | Compaction | Truncate conversation and hope | Lost decisions; inconsistent state | Compaction + keep recent files + tool-result clearing | T0 | High citeturn16view0turn16view1turn16view2turn10view0 |
| Governance | Permission prompts | UI prompts (“yes yes yes”) | Approval fatigue; bypass temptation | Auto-mode classifiers + allowlists + hard denylists | T0/T3 | High citeturn14search12turn18view0turn7view0 |
| Governance | Policy enforcement | “Don’t do X” in system prompt | Prompt injection; model mistakes | Hooks + OS sandbox + managed settings fail-closed | T3+ | High citeturn6view8turn19view0turn18view0 |
| Isolation | Run untrusted workloads | “Just run it” on host | Host compromise; secret theft | gVisor / containers / microVMs | T4/T5 | High citeturn7view5turn6view6 |
| Portability | Cross‑platform exec semantics | Assume Linux shell | Windows/macOS differences | Prefer typed APIs; when exec is needed use OS-native enforcement per platform | T3 | High citeturn6view1turn9view5turn19view0 |

This inventory is “complete” in the sense that any concrete CLI command you can name will map to one row (or a small combination). The long tail is handled by the **command runner lane**, governed by a capability policy and sandbox tier selection, rather than by making the model memorize thousands of command names.

## Why bash is problematic as a primary harness interface

### Bash is an untyped, ambiguous protocol

A shell string confounds: command selection, argument parsing, variable expansion, globbing, redirection, pipelines, control flow, and quoting rules—and those rules vary across shells and across OSes. This makes it hard to (a) reliably parse intent, (b) reliably audit effects, and (c) safely “auto-approve” without being tricked by composition. Codex explicitly treats shell wrappers like `bash -lc` as special cases because scripts can hide multiple actions inside one string; it only splits scripts into individual commands (for rule evaluation) when the script is simple enough to parse safely. citeturn21view0

The standard OS/process APIs reinforce the same point: Python’s subprocess docs warn to read “Security Considerations” before using `shell=True`, and OWASP documents command injection as executing attacker‑supplied OS commands via a vulnerable shell boundary. citeturn22search0turn22search23

### Bash makes context and cost worse for structured tasks

The Vercel/Braintrust “bash vs SQL” evaluation is a concrete demonstration of how “shell fluency” does not guarantee correctness or efficiency: in their setup, a SQL agent achieved 100% accuracy while a bash agent achieved 52.7% accuracy and used ~7× more tokens, costing more and taking longer; a hybrid model that used SQL and verified via filesystem checks hit 100%. citeturn13search1turn13search4

This should shape harness design: use filesystem tools (and possibly a virtual shell) for exploration and verification, but provide **purpose-built query tools** (SQL, AST/LSP) for structured tasks. The point is not “bash is useless”; it is “bash is a great *exploration UI*, but a poor *typed computation substrate*.” citeturn13search1turn9view0turn9view2

### Real bash is hard to sandbox correctly without OS help

Claude Code’s sandboxing docs explicitly call out OS-level enforcement: Seatbelt on macOS and bubblewrap on Linux/WSL2, with restrictions applying to all subprocesses (e.g., `npm`, `terraform`, `kubectl`). It also documents that the harness can fail open by default unless configured to fail closed (`sandbox.failIfUnavailable`). citeturn19view0turn9view3

Anthropic’s open-source sandbox runtime (“srt”) exists precisely because path-checking inside a Node/Python process is insufficient: OS-level primitives + proxy-based egress filtering are used to enforce filesystem and network restrictions even if the agent is compromised. citeturn19view1turn19view2

### Bash is stateful in ways that confuse agents

Even “bash tools” provided by harnesses often differ from a real interactive shell. Claude Code’s tools reference notes that each Bash tool call runs in a separate process; working directory persists but environment variables do not persist, and special measures are needed to carry environment across calls. This kind of “partial statefulness” is a frequent source of agent mis-execution and wasted turns. citeturn9view0

### Shell output is not a safe or stable data format

Bash outputs are typically human-oriented. They are hard to parse reliably, may change across versions, and can include binary data, ANSI color codes, pagers, and locale-dependent formatting. This affects correctness and raises token cost (agents over-read, re-run, or reformat). Practical harnesses therefore increasingly standardize on **structured output contracts** for core operations, and restrict shell usage to cases where human-style output is unavoidable.

## Safer and more efficient alternatives to bash, organized as execution lanes

### Multi-lane execution model

A key upgrade is to treat “running commands” as a *routing problem*: choose the safest lane that can perform the task. This is similar in spirit to how modern harnesses combine: permissions + sandboxing + specialized tools + programmatic tool calling. citeturn7view7turn19view0turn12view5

```mermaid
flowchart LR
  subgraph Model["LLM / Planner"]
    P[Plan + decide next operation]
  end

  subgraph LaneA["Lane A: Typed host APIs (T0–T1)"]
    A1[read_file / write_file / edit_file]
    A2[grep / glob / list]
    A3[git_status / git_diff]
    A4[lsp_definition / lsp_refs]
  end

  subgraph LaneB["Lane B: Specialized engines (T0–T2)"]
    B1[SQL/SQLite query tool]
    B2[AST/Tree-sitter queries]
    B3[Semantic index search]
  end

  subgraph LaneC["Lane C: Virtual shell (T2)"]
    C1[just-bash with overlay FS]
  end

  subgraph LaneD["Lane D: OS-sandboxed native exec (T3)"]
    D1[srt / seatbelt / landlock / bubblewrap]
  end

  subgraph LaneE["Lane E/F: Container or VM isolation (T4–T5)"]
    E1[rootless Docker + seccomp]
    E2[gVisor runsc]
    E3[Firecracker microVM]
    E4[Per-sandbox VM (Cloudflare Sandbox)]
  end

  P -->|prefer| LaneA
  P -->|if needs structured compute| LaneB
  P -->|if needs shell semantics but portable| LaneC
  P -->|if needs long-tail native commands| LaneD
  P -->|if untrusted/high risk| LaneE
```

Why these lanes are *specifically* supported by primary sources:

- just‑bash is designed as a virtual bash env with an in-memory filesystem, supports an overlay filesystem mode, and can enforce a network allowlist; it also provides optional JS/Python execution in WASM sandboxes with explicit limits (e.g., QuickJS 64 MB memory cap). citeturn12view0turn12view1turn12view3  
- sandbox-runtime (“srt”) is explicitly positioned as OS-level sandboxing for arbitrary processes without a container, using `sandbox-exec` on macOS and `bubblewrap` on Linux plus network proxy filtering. citeturn19view2turn19view1  
- Codex’s CLI exposes a “sandbox helper” and documents macOS Seatbelt and Linux Landlock (+ seccomp, optional bubblewrap pipeline) as the mechanism to run commands under the same policies Codex uses. citeturn9view5turn6view1  
- Container and VM tiers are grounded in official docs: Docker rootless mode reduces privilege of daemon/containers; Docker seccomp uses an allowlist profile; gVisor is a userspace “application kernel” providing a strong isolation layer; Firecracker is a microVM VMM with minimalist design to reduce attack surface; Cloudflare Sandbox describes per-sandbox VM isolation with quotas. citeturn7view3turn7view4turn7view5turn6view6turn7view6  
- WASI/Wasmtime provides capability-based filesystem access; Wasmtime’s docs emphasize capability-based filesystem access (only granted directories), and its tutorial explains `--dir` preopens as explicit capabilities. This is a strong substrate for “mini-tools” you can ship safely. citeturn6view7turn4search1

### Replacing whole classes of bash commands with typed tools

A practical mapping:

- Replace `cat/head/tail/sed -n` → `read_file(offset, limit)` with strict byte/line caps.
- Replace `grep/find` usage for code navigation → first try `rg`-style search tool, then LSP semantic tools for symbol tasks. citeturn9view0turn15search2
- Replace “parse JSON with jq” → `query_json(path, jq_expr)` (typed wrapper) or, for real analytics, put the data into SQLite and offer `sql_query(db, sql)` (plus verification). citeturn13search1turn12view3
- Replace “git plumbing via bash” → typed git operations, or restricted `git` runner returning structured diff/log and explicitly gating mutation. Use worktrees for isolation. citeturn15search3turn20view0
- Replace “API calls via curl” → typed HTTP tools with domain allowlists and secret-free call sites (token injection outside sandbox), similar to just-bash allowlist transforms and Claude Code’s sandbox proxy model. citeturn12view1turn19view0turn19view1
- Replace “chains of tool calls” → programmatic tool calling: let the model write code that calls tools, filters, and returns only the useful subset. citeturn7view1turn7view7

## Concrete implementation guidance for a next-generation harness

### Typed tool surface: recommended API signatures and contracts

Below is a minimal—but capability complete—typed surface. It is compatible with the patterns documented by Claude’s Agent SDK (Read/Write/Edit/Glob/Grep/Bash/LSP) and with other harnesses that ship similar tool sets by default. citeturn9view1turn10view2turn9view2

#### Files and search (T0/T1)

```ts
// Core data types
type Path = string;

type ReadFileRequest = {
  path: Path;
  offsetBytes?: number;        // default 0
  maxBytes: number;            // REQUIRED (hard cap)
  encoding?: "utf8" | "binary";
};

type ReadFileResponse = {
  path: Path;
  encoding: "utf8" | "binary";
  truncated: boolean;
  bytesRead: number;
  content: string;             // base64 if binary
  sha256?: string;             // optional for cache + integrity
};

type GrepHit = { path: Path; line: number; column: number; context: string };
type GrepRequest = {
  query: string;               // regex or literal (flag)
  paths?: Path[];
  respectIgnore: boolean;      // gitignore / tool ignore list
  maxHits: number;             // REQUIRED
  maxBytesScanned?: number;    // safety
};
type GrepResponse = { hits: GrepHit[]; truncated: boolean };

type ApplyPatchRequest = {
  operations: Array<{
    path: Path;
    // "range edits" or "unified diff". Enforce preflight.
    kind: "unified_diff" | "range_edits";
    payload: string;
  }>;
  dryRun?: boolean;
};
type ApplyPatchResponse = {
  applied: boolean;
  conflicts: Array<{ path: Path; reason: string }>;
  changedFiles: Path[];
};
```

Key safety/efficiency rules:

- Make **byte/line caps mandatory** on reads and searches to prevent token blowups.
- Return **structured** hits (file, line, column), not raw `grep` text.
- Make editing **transactional**: dry-run, conflict report, then commit.

This mirrors how “tool-result bloat” becomes the dominating cost unless you use tool-result clearing or compaction; typed tools make it easier to clear and regenerate precise results later. citeturn16view1turn16view2

#### Git operations (T0/T3+)

Two viable strategies:

- **Strategy 1: typed git library** (e.g., libgit2) for status/diff/log and certain safe mutations. citeturn15search1  
- **Strategy 2: sandboxed git CLI** but with argv-structured calls and deterministic output options.

Either way, expose:

```ts
type GitStatus = { branch?: string; changed: Path[]; untracked: Path[]; ahead?: number; behind?: number };
type GitDiffRequest = { paths?: Path[]; staged?: boolean; contextLines?: number; maxBytes: number };
type GitDiffResponse = { diff: string; truncated: boolean };

type GitWorktreeCreateRequest = { name: string; baseRef?: string };
type GitWorktreeCreateResponse = { worktreePath: Path };
```

Use worktrees for isolation; Claude Code explicitly supports “start in an isolated git worktree,” and git-worktree itself documents that worktrees share repo data but keep per-worktree `HEAD/index` etc separate. citeturn20view0turn15search3

#### Command execution / long tail (T2–T5)

Make “exec” *not one tool*, but a policy router:

```ts
type ExecRequest = {
  argv: string[];           // NEVER accept shell strings by default
  cwd?: Path;
  env?: Record<string,string>;
  stdin?: string;           // bounded
  timeoutMs: number;        // REQUIRED
  maxStdoutBytes: number;   // REQUIRED
  maxStderrBytes: number;   // REQUIRED
  network?: { mode: "off" | "allowlist"; allowHosts?: string[] };
  fs?: { readRoots: Path[]; writeRoots: Path[]; denyPaths?: Path[] };
  tierHint?: "T2" | "T3" | "T4" | "T5";
};

type ExecResponse = {
  exitCode: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
  durationMs: number;
  tierUsed: "T2" | "T3" | "T4" | "T5";
};
```

**Policy**: default to `argv` + no network + workspace-only writes. If the model asks for `bash -lc`, treat it as *risk escalation* (same rationale as Codex rules: compound shell scripts hide multiple actions). citeturn21view0turn22search0turn22search23

### Permission model: from “prompt spam” to governance

Borrow directly from proven designs:

- Claude permission rules: `Tool` or `Tool(specifier)` with patterns like `Bash(npm run test *)` and deny-first precedence; plus advice to deny network tools like `curl` and use a dedicated web tool instead. citeturn18view0  
- Codex rules: explicit per-command prefixes, with *inline unit tests* (`match`/`not_match`), and the explicit note that decisions combine to the most restrictive result. citeturn21view0  
- Codex sandboxing/approvals: sandbox defines technical boundaries; approval policy decides when to stop; spawned commands inherit sandbox boundaries. citeturn6view1turn6view2

Recommended permission object model:

- **Hard policy layer** (managed): deny rules, protected paths, network defaults, “fail-closed” toggles (e.g., sandbox cannot start → exit). Claude Code supports managed settings and explicit fail-closed knobs. citeturn9view3turn18view0turn19view0  
- **Project layer**: safe allowances for common workflows (tests, builds, formatters) and tool configs.
- **User layer**: convenience allowlist (personal), never overriding managed denies.

### Sandbox configuration patterns

A defensible “tier selection” policy:

- **T2 (virtual shell/WASI)** for exploration tasks and deterministic transforms.
- **T3 (OS sandbox)** for ordinary native tools (git, language runtime) where you need real binaries but can enforce no-exfil boundaries.
- **T4/T5** for “untrusted code execution” and dependency installs, because those are both high-risk and high-frequency in coding tasks.

Concrete basis:

- Claude Code sandboxing: OS-level restrictions (Seatbelt/bubblewrap) apply to subprocesses; network goes through proxy allowlists; can grant additional write paths via settings. citeturn19view0turn19view1  
- sandbox-runtime: OS-level sandboxing without containers, with explicit filesystem and network restrictions and secure-by-default posture. citeturn19view2  
- Docker: rootless mode reduces daemon/container privilege; seccomp default profile is allowlist-based. citeturn7view3turn7view4turn2search19  
- gVisor: userspace application kernel isolation layer; integrates as OCI runtime (`runsc`). citeturn7view5  
- Firecracker: microVMs provide stronger isolation than containers; minimalist VMM reduces attack surface. citeturn6view6turn3search4  
- Cloudflare Sandbox: per-sandbox VM isolation with resource quotas; explicit filesystem/process/network isolation. citeturn7view6turn3search25

### Memory planes and context management

Claude Code provides a concrete, production reference for *what must be persisted* and *what must be kept small*:

- MEMORY.md: only first 200 lines or first 25KB loaded at session start; topic files are read on demand. citeturn6view9  
- Tool search: load tool definitions on demand to avoid tool-schema bloat (example: 55k tokens for multi-server tool definitions; tool search often reduces by >85%). citeturn6view10  
- Programmatic tool calling: reduces multi-tool roundtrips and token consumption by running scripts in code execution containers and only returning filtered results. citeturn7view1turn7view7  
- Tool-result clearing + compaction: handle long-horizon context growth; keep recent files/decisions; clear re-fetchable tool results. citeturn16view0turn16view1turn16view2turn10view0

A practical harness must therefore implement at least four planes:

```mermaid
flowchart TB
  subgraph Plane0["Plane 0: Immutable system & policy"]
    S1[Managed settings: deny rules, sandbox must-start, allowed domains]
    S2[Tool schemas (deferred via tool-search)]
  end

  subgraph Plane1["Plane 1: Project instructions"]
    P1[CLAUDE.md / AGENTS.md style rules]
    P2[Runbooks: build/test commands, repo conventions]
  end

  subgraph Plane2["Plane 2: Session working set"]
    W1[Recent messages]
    W2[Recent files (N most recent)]
    W3[Active TODO / plan state]
  end

  subgraph Plane3["Plane 3: Durable memory"]
    M1[Concise MEMORY index (<=200 lines / 25KB)]
    M2[Topic files loaded on-demand]
  end

  subgraph Plane4["Plane 4: Tool artifacts"]
    T1[Tool results cache (re-fetchable)]
    T2[Cleared/compacted history]
  end

  Plane0 --> Plane1 --> Plane2 --> Plane3
  Plane2 --> Plane4
```

This “many planes” view also explains why “one loop + bash is enough” is true only at prototype stage; production harnesses add permissions, streaming, concurrency, compaction, subagents, persistence, and MCP. citeturn6view5turn5search14

### Programmatic tool calling patterns (PTC)

Programmatic tool calling is the best way to handle “many thousands of operations” without flooding the model context: let the model write code that calls tools, filters, aggregates, and returns only what matters. Anthropic explicitly frames PTC as reducing latency and token cost; it relies on code execution containers that can be reused and have lifetime/idle timeouts. citeturn7view1turn7view7

**Harness-side pattern (TypeScript pseudocode)**

```ts
// 1) Expose tool functions into a code execution environment.
// 2) In the main agent loop, allow the model to emit a "ptc" block.
// 3) Execute it in a sandbox with no network, strict CPU/mem/time.
async function runPTC(script: string, toolFns: Record<string, Function>) {
  // validate: no file/network unless via toolFns; timeouts; output caps.
  const result = await codeExecutionSandbox.run(script, { toolFns });
  return result; // already filtered/aggregated
}
```

This complements tool search: tool search shrinks tool definitions; PTC shrinks tool-result roundtrips. citeturn6view10turn7view1turn7view7

## Special case study: how leading coding harnesses implement these operations

This section summarizes what can be reliably confirmed from official docs and primary sources. Where a harness offers both product and open-source components, the focus is on documented behavior (not rumor).

### Claude Code

- **Tool primitives**: documented Agent SDK tool set includes Read/Write/Edit/Bash/Glob/Grep/WebSearch/WebFetch and user question tool. citeturn9view1  
- **Bash semantics**: separate process per command; cwd persists; env does not persist unless configured. citeturn9view0  
- **Hooks**: supports lifecycle hooks as shell commands, HTTP endpoints, or LLM prompts with JSON I/O schemas. citeturn6view8  
- **Permissions**: pattern rules like `Bash(npm run test *)`; explicit guidance to deny bash network tools and prefer WebFetch; sandbox boundary can substitute for per-command prompt. citeturn18view0  
- **Sandboxing**: Seatbelt/bubblewrap + proxy network isolation; can fail closed if sandbox cannot start; applies to subprocesses. citeturn19view0turn19view1  
- **Memory**: MEMORY.md start-of-session truncation (200 lines or 25KB); topic files loaded on demand. citeturn6view9  
- **Scaling context**: guidance includes compaction, tool-result clearing, tool search, and related context engineering methods. citeturn16view0turn16view1turn6view10  
- **Worktree isolation**: the CLI can start in an isolated git worktree. citeturn20view0turn15search3

### Codex CLI

- **Sandbox model**: sandboxing is the boundary enabling autonomy; spawned local commands run in constrained environment; crossing boundaries triggers approval flow; spawned tools inherit the same sandbox. citeturn6view1turn6view2  
- **OS enforcement**: CLI docs describe macOS Seatbelt and Linux Landlock (+ seccomp; optional bubblewrap pipeline) for `codex sandbox`. citeturn9view5  
- **Rules language**: rules can be expressed as command prefix rules; rules can include inline “unit tests”; Codex treats shell wrapper scripts specially and uses tree-sitter to split safe scripts for per-command evaluation. citeturn21view0turn15search0  
- **Config layering**: user config `~/.codex/config.toml` and trusted per-project overrides with precedence rules. citeturn21view2  
- **Network defaults**: docs describe default workspace-write mode with network off unless enabled. citeturn6view2turn21view1

### OpenCode

- **Tool set**: built-in tools include bash/edit/write/read/grep/glob/list, optional LSP, apply_patch, webfetch/websearch, and tool gating via permissions. citeturn9view2turn12view4  
- **Permissions posture**: by default all tools enabled without permission prompts; configurable allow/deny/ask. citeturn9view2turn12view4  
- **Extensibility**: plugin model that loads project or global plugins. citeturn10view3  
- **Design emphasis**: positioned as terminal/IDE/desktop agent with LSP enabled in product messaging. citeturn8search3turn9view2  

### Forge Code and Forge ACP

There are two distinct “Forge” entities in the ecosystem:

- **Forge (ACP CLI)**: “universal CLI for coding agents” implementing Agent Client Protocol; designed specifically to run agents in their native harnesses rather than a one-size-fits-all harness. citeturn11view1turn17search0turn17search3  
- **ForgeCode (AI terminal environment)**: documentation emphasizes “secure by design,” “restricted shell mode,” MCP integration, and semantic search indexing. citeturn11view0turn11view2  

ACP itself is JSON-RPC 2.0 methods + notifications, explicitly supporting local subprocess agents as well as remote agents via HTTP/WebSocket. This is relevant because it suggests a path to decouple “UI client” from “execution harness” cleanly. citeturn17search0turn17search3

### Pi coding agent

- **Default tools**: Pi gives the model `read`, `write`, `edit`, `bash` by default, with additional built-ins such as grep/find/ls; it supports tool selection flags. citeturn6view0turn12view6  
- **Sessions + compaction**: has compaction and branch summarization with explicit token thresholds, a reserved token buffer, and structured summaries. citeturn10view0  
- **Extensibility**: supports extensions and skills; docs include SDK usage and multiple modes. citeturn10view2turn6view0  

### Lessons to apply to your harness update

1. **Use OS-level sandboxing for any real command runner**, because “application-layer checks” cannot reliably contain subprocess behavior; both Claude Code and Codex explicitly ground their command confinement in OS primitives. citeturn19view0turn9view5turn6view1turn19view2  
2. **Separate tool governance from tool execution**: sandbox defines technical boundaries; approvals decide when the agent must stop. citeturn6view1turn6view2  
3. **Add programmable governance points** (hooks/plugins) so you can convert failures into deterministic harness improvements. Claude Code’s hook model and OpenCode’s plugin model are explicit examples. citeturn6view8turn10view3  
4. **Treat memory and compaction as infrastructure**, not prompts: MEMORY.md truncation strategies, tool-result clearing, and compaction recipes exist because long-running agents otherwise drown. citeturn6view9turn16view1turn10view0  
5. **Scale tools with tool search and scale workflows with programmatic tool calling** for large catalogs and multi-step work. citeturn6view10turn7view1  

## Prioritized upgrade roadmap by ROI and risk

### Recommended priority order

**Top priorities** are those that simultaneously reduce catastrophic risk and improve reliability/cost:

- Replace bash-first workflows with typed primitives for read/search/edit/git/test.
- Introduce sandbox-tier routing for any residual command execution.
- Implement memory planes + compaction + tool-result clearing.
- Add tool search and programmatic tool calling to manage “thousands of features” without context bloat.
- Add policy hooks and managed settings, with fail-closed defaults where appropriate.

These are precisely the mechanisms described as “production-grade harness” layers beyond a minimal tool loop. citeturn6view5turn16view1turn7view7turn19view0

### Comparison table: recommended features → implementation path

| Feature | Current standard | Bash limitations | Proposed solution | Sandbox tier | Priority |
|---|---|---|---|---|---|
| Chunked reads + bounded search | `cat`, `grep`, `rg` | token floods; brittle parsing | Typed read/grep with hard caps + structured hits | T0 | Highest |
| Transactional editing | `sed -i`, heredocs | unsafe mass edits; hard rollback | Patch API + dry-run + commit; auto-format hooks | T1 | Highest |
| LSP-based navigation | text grep heuristics | wrong/slow on large repos | LSP tool (defs, refs, diags) | T0 | High citeturn9view0 |
| Structured data querying | `jq`, `awk` | pipelines explode; poor accuracy | SQLite/SQL tool + optional verify via FS | T2/T3 | High citeturn13search1 |
| Safe command runner | `bash -lc` on host | injection + exfil + portability | Argv-first exec + OS sandbox runtime | T3 | Highest citeturn21view0turn19view2 |
| High-risk execution (deps/build) | host installs | supply chain + escape risk | Containers/microVM per job; allowlisted registries | T4/T5 | Highest citeturn6view6turn7view4 |
| Tool search | huge tool list in prompt | context bloat | Tool search/deferred loading | T0 | High citeturn6view10 |
| Programmatic tool calling | tool round-trips | latency + token cost | PTC via code execution sandbox | T0 | High citeturn7view1 |
| Persistent memory plane | huge prompts | drift | MEMORY index + on-demand topic files | T0 | High citeturn6view9 |
| Compaction + tool-result clearing | none / manual | context overflow | automatic strategies | T0 | High citeturn16view2turn16view1 |
| Governance hooks | prompt-only policy | bypassable | Pre/Post tool hooks + managed settings | T3+ | High citeturn6view8turn18view0 |

### Migration steps from bash-centric harness

1. **Introduce typed “core ops” first** (read/search/edit/list + git status/diff). You can do this without changing the agent loop; just add tools and prefer them in tool selection logic. Claude Code’s Agent SDK overview illustrates how a small tool set can cover most repo work. citeturn9view1  
2. **Cap and structure outputs** immediately (max bytes, max hits). This pairs naturally with tool-result clearing later. citeturn16view1turn16view2  
3. **Replace shell-string exec with argv exec**. Treat any request for `bash -lc` as elevated risk; apply rules like Codex does for compound commands. citeturn21view0turn22search0  
4. **Implement OS-level sandboxing for the remaining exec lane** (Seatbelt/Landlock/bwrap via sandbox-runtime or equivalent). Ensure you can fail closed when the sandbox is required. citeturn19view0turn19view2  
5. **Add a virtual shell lane (just-bash)** for portable, low-risk shell semantics in environments where OS sandboxing is unavailable/expensive; use overlay FS so reads can come from disk and writes remain ephemeral. citeturn12view0turn12view1  
6. **Add a high-risk isolation lane** (rootless Docker + seccomp, optional gVisor; optionally Firecracker/microVM for highest risk). citeturn7view3turn7view4turn7view5turn6view6  
7. **Add compaction and memory planes** (concise index + on-demand deep files). This follows known, documented patterns. citeturn6view9turn16view0turn10view0  
8. **Adopt tool search + programmatic tool calling** once tool catalog and workflow depth grow; they directly address context bloat and multi-step overhead. citeturn6view10turn7view1  

### Security note on post-leak ecosystem risk

Given reporting that attackers used “Claude Code leak” interest to distribute malware via malicious repositories, treat any “download a tool/repo/binary suggested by the model” as **untrusted**. Your harness should default to (a) isolated downloads, (b) restricted egress, (c) no host secrets in execution environment, and (d) auditing of artifacts. citeturn17news39turn17search17

### Incorporating the linked discussion artifacts

The user-supplied summary notes the rise of “filesystem + bash” as a strong abstraction and highlights the need to move beyond it for correctness, robustness, and safety. fileciteturn0file0