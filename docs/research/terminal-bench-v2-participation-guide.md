# Terminal-Bench v2.0 Participation Guide

> **Date:** 2026-04-01
> **Purpose:** Step-by-step guide to running Terminal-Bench v2.0 with AutoCode

## 1. Installation

```bash
# Install Harbor (the official harness for tbench v2.0)
uv tool install harbor
# OR: pip install harbor

# Verify
harbor --version    # Should show 0.3.0+
docker info         # Docker must be running
```

**System Requirements:**
- Python 3.12+
- Docker
- 50-200GB disk (for task Docker images)
- ~8GB RAM for 4 concurrent trials

## 2. Agent Adapter Interface

AutoCode needs an External Agent adapter extending `BaseAgent`:

```python
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

class AutoCodeAgent(BaseAgent):
    SUPPORTS_ATIF: bool = False

    @staticmethod
    def name() -> str:
        return "autocode"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment,
                  context: AgentContext) -> None:
        # Agent loop here
        # Use environment.exec(command="...", timeout_sec=120) to run commands
        # Use environment.upload_file() / download_file() for file ops
        # Set context.n_input_tokens, context.n_output_tokens, context.cost_usd
        pass
```

## 3. Running Tasks

```bash
# Run oracle agent (reference solutions, no LLM) to verify setup
harbor run -d terminal-bench@2.0 -a oracle

# Run single task with custom agent
harbor run -d terminal-bench@2.0 \
    --agent-import-path autocode_harbor_agent:AutoCodeAgent \
    -i "hello-world"

# Run subset (5 tasks)
harbor run -d terminal-bench@2.0 \
    --agent-import-path autocode_harbor_agent:AutoCodeAgent \
    -l 5

# Full benchmark for leaderboard (5 attempts per task, 4 concurrent)
harbor run -d terminal-bench@2.0 \
    --agent-import-path autocode_harbor_agent:AutoCodeAgent \
    -m "your-model" -k 5 -n 4 -o ./results
```

## 4. Leaderboard Submission

Submit via PR to `huggingface.co/datasets/harborframework/terminal-bench-2-leaderboard`:

```
submissions/terminal-bench/2.0/autocode__model-name/
  metadata.yaml
  <job-folder>/
    config.json
    <trial-1>/result.json
    ...
```

**Required `metadata.yaml`:**
```yaml
agent_url: https://github.com/Abbiirr/lowrescoder
agent_display_name: "AutoCode"
agent_org_display_name: "AutoCode"
models:
  - model_name: your-model
    model_provider: provider
    model_display_name: "Model Name"
    model_org_display_name: "Provider"
```

**Validation rules:**
- `timeout_multiplier` must be `1.0`
- No resource overrides
- Minimum 5 trials per task (`-k 5`)

## 5. ATIF Trajectory Format (v1.6)

```json
{
  "schema_version": "ATIF-v1.6",
  "session_id": "unique-id",
  "agent": {"name": "autocode", "version": "0.1.0", "model_name": "model"},
  "steps": [
    {"step_id": 1, "source": "user", "message": "instruction..."},
    {"step_id": 2, "source": "agent", "model_name": "model",
     "message": "I'll do X", "tool_calls": [...], "observation": {...},
     "metrics": {"prompt_tokens": 150, "completion_tokens": 30}}
  ]
}
```

## 6. Time Estimates

- ~100 tasks x 5 attempts = 500 trials
- Per trial: 120s-1800s (task-dependent)
- 4 concurrent locally: 12-48 hours
- Cloud (Daytona, -n 32): 1-4 hours

## 7. Gotchas

1. Use `harbor` CLI, NOT `tb` CLI (that's for v0.x/v1.x)
2. `timeout_multiplier` must be 1.0 for leaderboard
3. Minimum 5 trials per task
4. Docker images consume 50-200GB disk
5. Agent `setup()` and `run()` must be `async def`
6. Some tasks have `allow_internet = false`
7. Import path format: `module.path:ClassName` (colon, not dot)
8. Do NOT assume root in containers
