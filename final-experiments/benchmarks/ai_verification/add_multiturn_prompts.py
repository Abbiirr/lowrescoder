#!/usr/bin/env python3
"""Add followup_prompts to all single-prompt canary scenarios.

Skips scenarios that already have followup_prompts (the 4 human-session ones).
Adds 2 followup prompts based on category + language.
"""

from __future__ import annotations

import json
import os
import sys

CANARY_DIR = os.path.join(
    os.path.dirname(__file__), "canary_scenarios"
)

# Test command by language
LANG_TEST_CMDS = {
    "python": "uv run pytest tests/ -q",
    "go": "go test ./...",
    "rust": "cargo test --quiet",
    "typescript": "npm test -- --forceExit",
    "java": "mvn test -q",
}

# Followup templates by category
CATEGORY_TEMPLATES: dict[str, list[str]] = {
    "repo_init": [
        "Run `{test_cmd}` and show me which tests are passing and which are still failing. Fix any failures — pay attention to edge cases like empty input, boundary values, and error conditions.",
        "Final check: run `{test_cmd}` one more time. All tests must be green. If anything is still failing, trace through the failing assertion and fix it now.",
    ],
    "dirty_cleanup": [
        "Run `{test_cmd}` to check the current state. Walk me through what bugs you found and fixed. If any tests are still failing, show me the errors and fix them.",
        "Final verification: run `{test_cmd}` and confirm a completely clean build. Every test must pass — if any are still red, fix them now.",
    ],
    "refactor": [
        "Run `{test_cmd}` to confirm no regressions from your refactor. Also review the code you changed — any remaining duplication, long functions, or unclear names to clean up?",
        "Final pass: run `{test_cmd}` and confirm everything is green. Give me a one-line summary of what changed.",
    ],
    "backend_feature": [
        "Good. Now add input validation and error handling to the feature you just implemented. What should happen with invalid, missing, or malformed inputs? Update the implementation and tests to cover those cases.",
        "Run `{test_cmd}` to verify everything including your new error handling. Fix any failures and confirm the feature is complete.",
    ],
    "migration": [
        "Run `{test_cmd}` to verify the migration is correct. Make sure existing behavior is preserved and the migration handles edge cases safely.",
        "Final verification: run `{test_cmd}` and confirm all tests pass. Is this migration safe to run on real data without data loss or breaking existing clients?",
    ],
    "long_horizon": [
        "Good progress. Run `{test_cmd}` to see where we stand. Continue with the remaining steps, prioritizing the parts the tests depend on most.",
        "Final push: run `{test_cmd}` and fix any remaining failures. Make sure the full implementation is complete and all tests pass.",
    ],
    "frontend_feature": [
        "Good. Now handle edge cases: what does the UI show when data is empty, loading, or an error occurs? Add those states and tests.",
        "Run `{test_cmd}` to verify the complete implementation. Fix any failures and confirm all UI states work correctly.",
    ],
}


def resolve_test_cmd(scenario: dict) -> str:
    """Pick test command: from grading.check_commands.run_tests first, then language fallback."""
    grading = scenario.get("grading", {})
    check_cmds = grading.get("check_commands", {})
    if "run_tests" in check_cmds:
        return check_cmds["run_tests"]
    lang = scenario.get("target_stack", {}).get("language", "python")
    return LANG_TEST_CMDS.get(lang, "uv run pytest tests/ -q")


def make_followup_prompts(scenario: dict) -> list[str]:
    category = scenario.get("category", "repo_init")
    templates = CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["repo_init"])
    test_cmd = resolve_test_cmd(scenario)
    return [t.format(test_cmd=test_cmd) for t in templates]


def process_scenarios() -> None:
    files = sorted(f for f in os.listdir(CANARY_DIR) if f.endswith(".json"))
    skipped = 0
    updated = 0
    errors = []

    for fname in files:
        fpath = os.path.join(CANARY_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                scenario = json.load(fh)
        except Exception as e:
            errors.append(f"{fname}: {e}")
            continue

        task_spec = scenario.get("task_spec", {})
        existing_fp = task_spec.get("followup_prompts", [])
        if existing_fp:
            skipped += 1
            continue

        # Add followup_prompts in-place
        task_spec["followup_prompts"] = make_followup_prompts(scenario)
        scenario["task_spec"] = task_spec

        try:
            with open(fpath, "w", encoding="utf-8") as fh:
                json.dump(scenario, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
        except Exception as e:
            errors.append(f"{fname}: write error: {e}")
            continue

        updated += 1

    print(f"Updated:  {updated} scenarios (followup_prompts added)")
    print(f"Skipped:  {skipped} scenarios (already had followup_prompts)")
    if errors:
        print(f"Errors:   {len(errors)}")
        for err in errors:
            print(f"  - {err}")
    else:
        print("Errors:   0")

    total_with_fp = updated + skipped
    print(f"\nTotal scenarios now with followup_prompts: {total_with_fp}")


if __name__ == "__main__":
    process_scenarios()
