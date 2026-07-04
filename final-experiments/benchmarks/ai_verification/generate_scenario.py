"""AI scenario generator (Milestone 4).

Generates a frozen ScenarioSpec JSON using an LLM, seeded from category/difficulty/stack.
Saved to benchmarks/ai_verification/generated/<timestamp>-<scenario_id>.json for reproducibility.

Usage:
  uv run python -m benchmarks.ai_verification.generate_scenario \\
    --category backend_feature --difficulty medium --stack python --seed 42

  uv run python -m benchmarks.ai_verification.generate_scenario \\
    --category dirty_cleanup --difficulty hard --stack go --seed random

Safety rules (enforced by generator):
  - generated scenario always uses an isolated sandbox
  - network is off by default in generated scenarios
  - generated tests are declared in required_artifacts before any agent prompt
  - grading checks are always present (no AI-only grading)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

from benchmarks.ai_verification.schema import (
    Category,
    Difficulty,
    GradingSpec,
    Check,
    RepoSeed,
    SeedMode,
    ScenarioSpec,
    TargetStack,
    TaskSpec,
    scenario_from_dict,
)

GENERATED_DIR = Path("benchmarks/ai_verification/generated")

GENERATION_PROMPT_TEMPLATE = """\
You are a scenario generator for an AI coding-agent verification harness.

Generate a coding scenario as a JSON object matching this schema:
{{
  "title": "string — one concise line",
  "description": "string — 1-2 sentences describing the setup and goal",
  "task_spec": {{
    "prompt": "string — exact prompt to show the agent (be precise about file paths, function signatures, behavior)",
    "required_artifacts": ["list of concrete file/behavior assertions"],
    "success_criteria": ["list of observable criteria for AI reviewer"]
  }},
  "repo_seed": {{
    "mode": "fresh|fixture|mutate",
    "fixture_ref": "fixture dir name or empty string for fresh",
    "injections": [{{"path": "rel/path", "content": "file content"}}],
    "setup_commands": ["shell commands to run in sandbox before agent"]
  }},
  "grading": {{
    "checks": ["run_tests", "lint", "typecheck", "build"],
    "check_commands": {{"check_name": "shell command"}},
    "ai_review_enabled": true,
    "reviewer": "claude"
  }},
  "duration_hint_minutes": integer
}}

Constraints:
- category: {category}
- difficulty: {difficulty}
- language: {language}
- framework: "{framework}"
- seed: {seed}
- The scenario must be solvable by a single agent in one session.
- For dirty_cleanup/repo_init: fixture starts in expected broken/empty state.
- For brownfield (fixture/mutate): include injections that create realistic flaws.
- setup_commands must be minimal (uv sync, go mod download, cargo fetch, npm install).
- Network access: off by default. Do not generate scenarios requiring npm publish, external API calls, etc.
- Required artifacts must include test-file existence and test-passing evidence.

Return ONLY valid JSON with no markdown fences, no prose before or after.
"""


def _seed_int(seed_arg: str) -> int:
    if seed_arg == "random":
        return random.randint(1, 2**31)
    return int(seed_arg)


def _call_llm(prompt: str) -> str:
    """Call the LLM via autocode gateway. Returns raw response text."""
    try:
        import requests
        api_key = (
            os.environ.get("LITELLM_API_KEY")
            or os.environ.get("LITELLM_MASTER_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or ""
        )
        gateway = os.environ.get("LITELLM_GATEWAY_URL", "http://localhost:4000")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "coding",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        resp = requests.post(f"{gateway}/v1/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc


def generate(
    category: str,
    difficulty: str,
    stack: str,
    framework: str = "",
    seed_arg: str = "random",
    dry_run: bool = False,
) -> ScenarioSpec:
    seed = _seed_int(seed_arg)
    random.seed(seed)

    prompt = GENERATION_PROMPT_TEMPLATE.format(
        category=category,
        difficulty=difficulty,
        language=stack,
        framework=framework,
        seed=seed,
    )

    if dry_run:
        print("[generate_scenario] dry-run: skipping LLM call")
        print(f"[generate_scenario] would generate: category={category} difficulty={difficulty} stack={stack} seed={seed}")
        # Return a placeholder spec
        scenario = ScenarioSpec(
            category=Category(category),
            difficulty=Difficulty(difficulty),
            title=f"[DRY RUN] {category}/{difficulty}/{stack}",
            description="Dry-run placeholder — no LLM call made.",
            task_spec=TaskSpec(prompt="[dry run]"),
            target_stack=TargetStack(language=stack, framework=framework),
            repo_seed=RepoSeed(mode=SeedMode.FRESH),
            grading=GradingSpec(checks=[Check.RUN_TESTS]),
            generated_by="claude",
            seed=seed,
        )
    else:
        print(f"[generate_scenario] calling LLM (seed={seed})...")
        raw = _call_llm(prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned non-JSON: {raw[:300]}") from exc

        # Inject fields controlled by CLI args
        data["category"] = category
        data["difficulty"] = difficulty
        data.setdefault("target_stack", {})
        data["target_stack"]["language"] = stack
        data["target_stack"]["framework"] = framework
        data["generated_by"] = "claude"
        data["seed"] = seed

        scenario = scenario_from_dict(data)

    # Save to generated/
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = GENERATED_DIR / f"{ts}-{scenario.scenario_id[:8]}.json"
    scenario.save(out_path)
    print(f"[generate_scenario] saved to {out_path}")
    return scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a verification scenario using LLM")
    parser.add_argument("--category", choices=[c.value for c in Category], required=True)
    parser.add_argument("--difficulty", choices=[d.value for d in Difficulty], default="medium")
    parser.add_argument("--stack", required=True, help="e.g. python, typescript, go, rust")
    parser.add_argument("--framework", default="", help="e.g. fastapi, express, net/http")
    parser.add_argument("--seed", default="random", help="integer or 'random'")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM call, print prompt only")
    args = parser.parse_args()

    generate(
        category=args.category,
        difficulty=args.difficulty,
        stack=args.stack,
        framework=args.framework,
        seed_arg=args.seed,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
