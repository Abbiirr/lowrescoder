# AutoCode Suite

This folder is the full AutoCode workspace: the coding agent itself plus the
components used to validate, measure, and design it. Each sibling is an
independent component (set up its own git per folder as needed).

## Components

| Folder | Role | Use it to |
|---|---|---|
| `autocode/` | **Main harness.** Python backend (`src/autocode/`) + Rust TUI (`rtui/`). Self-contained (`pyproject.toml`, `Makefile`, `uv.lock`). | Build and change the agent. **All development happens here.** |
| `harness-tester/` | **Validation** (a.k.a. `harness-rig`). Pytest for coding-agent harnesses; treats `autocode` as the system under test. | After each dev iteration, confirm the harness still records prompts/events/tools/diffs/judge artifacts and didn't regress. |
| `benchmarks/` | **Measurement.** Benchmark runners, adapters, and sweeps against `autocode` (requires the LLM gateway up). | Track capability/quality over time. |
| `research-components/` | **Reference corpus.** Read-only clones of other agents (codex, claude-code, aider, goose, opencode, …) + `wiki/` crate sources. References, **not dependencies**. | Compare patterns and mine ideas when planning new features. Do not cargo-cult. |
| `tui-references/` | **TUI design target.** The v9 shell-contract spec + screen PNGs the Rust TUI is graded against. | Conform to it for any TUI work. |
| `training-data/` | Datasets for AutoCode models. | Training/eval data. |
| `video-agent/` | **Spin-off product.** Standalone agentic video editor (implements `lowrescoder/new_plans/PLAN_02_VIDEO_AGENT.md`): proposer/compiler split, typed Change Requests, deterministic FFmpeg render. Isolated — does **not** import or modify `autocode/`. | Edit any video by intent; reuse the CR/compiler pattern. See `video-agent/README.md`. |
| `lowrescoder/` | **Frozen archive** of the pre-split monorepo (`.git` + old planning docs). | History and leftovers only — not part of the loop. |

## Development loop

1. **Build** — make the change in `autocode/`.
2. **Validate** — run `harness-tester/` to catch harness regressions.
3. **Measure** — run `benchmarks/` (gateway up) to track quality.
4. **Plan** — when designing new work, draw patterns from `research-components/`;
   for TUI changes, conform to `tui-references/`.

## Commands

```sh
# Build / run the harness
cd autocode && uv sync && uv run autocode      # launch (bare `autocode`, not `autocode chat`)
make test && make lint                          # autocode tests + lint
make tui-build                                  # build the Rust TUI binary

# Validate the harness
cd harness-tester && scripts/00-preflight.sh && scripts/01-run-deterministic-tests.sh

# Run benchmarks (needs the LLM gateway running)
cd benchmarks && ./run_all_benchmarks.sh
```

> **Caveat:** `benchmarks/` scripts still hardcode the old
> `/home/bs01763/projects/ai/lowrescoder` path — update those paths before
> running benchmarks from this layout.

Each component carries its own deeper docs (`autocode/TESTING.md`,
`harness-tester/README.md`, `research-components/MANIFEST.md`,
`tui-references/…shell_contract.md`).
