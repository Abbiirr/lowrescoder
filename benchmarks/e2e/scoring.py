"""Generic scoring for E2E benchmark scenarios.

Provides acceptance-check execution, file-existence verification,
and default scoring logic. Scenarios can override scoring via
a custom scoring_function in the manifest.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

from e2e.scenario_contract import ScenarioManifest


def run_acceptance_checks(sandbox: Path, manifest: ScenarioManifest) -> list[dict]:
    """Run each AcceptanceCheck in the manifest and return results.

    Each result dict contains:
        name, command, passed, exit_code, stdout, stderr, timed_out, output_match
    """
    results: list[dict] = []
    use_shell = sys.platform == "win32"

    for check in manifest.acceptance_checks:
        entry: dict = {
            "name": check.name,
            "command": check.command,
            "required": check.required,
            "passed": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "output_match": None,
        }

        try:
            proc = subprocess.run(
                check.command,
                shell=True,  # noqa: S602
                cwd=sandbox,
                capture_output=True,
                text=True,
                timeout=check.timeout_s,
                check=False,
            )
            entry["exit_code"] = proc.returncode
            entry["stdout"] = proc.stdout[:5000]
            entry["stderr"] = proc.stderr[:5000]

            code_ok = proc.returncode == check.expect_exit_code

            output_ok = True
            if check.expect_output is not None:
                match = re.search(check.expect_output, proc.stdout)
                entry["output_match"] = bool(match)
                output_ok = bool(match)

            entry["passed"] = code_ok and output_ok

        except subprocess.TimeoutExpired:
            entry["timed_out"] = True
            entry["stderr"] = f"Timed out after {check.timeout_s}s"

        except Exception as e:
            entry["stderr"] = f"Error: {e}"

        results.append(entry)

    return results


def check_required_files(sandbox: Path, manifest: ScenarioManifest) -> list[str]:
    """Return list of missing required artifact paths."""
    missing = []
    for rel_path in manifest.required_artifacts:
        if not (sandbox / rel_path).exists():
            missing.append(rel_path)
    return missing


def score_scenario(
    sandbox: Path,
    manifest: ScenarioManifest,
    check_results: list[dict],
) -> dict[str, int]:
    """Score a scenario run. Returns dict with category scores and 'total'.

    Default scoring: 80% from acceptance check pass rate, 20% from file existence.
    Delegates to manifest.scoring_function if set.
    """
    if manifest.scoring_function:
        return _run_custom_scorer(sandbox, manifest, check_results)

    max_score = manifest.max_score

    # Acceptance checks: 80% of max score
    check_weight = int(max_score * 0.8)
    if check_results:
        passed = sum(1 for c in check_results if c["passed"])
        check_score = int(check_weight * passed / len(check_results))
    else:
        check_score = 0

    # File existence: 20% of max score
    file_weight = max_score - check_weight
    missing = check_required_files(sandbox, manifest)
    total_required = len(manifest.required_artifacts)
    if total_required > 0:
        present = total_required - len(missing)
        file_score = int(file_weight * present / total_required)
    else:
        file_score = file_weight  # No requirements = full marks

    total = check_score + file_score

    return {
        "acceptance_checks": check_score,
        "file_existence": file_score,
        "total": total,
        "max_score": max_score,
        "missing_files": missing,
    }


def _run_custom_scorer(
    sandbox: Path,
    manifest: ScenarioManifest,
    check_results: list[dict],
) -> dict[str, int]:
    """Import and call a custom scoring function by dotted path."""
    assert manifest.scoring_function is not None
    module_path, func_name = manifest.scoring_function.rsplit(".", 1)
    module = importlib.import_module(module_path)
    scorer = getattr(module, func_name)
    return scorer(sandbox, manifest, check_results)
