"""Guard tests for the restored B15-B29 benchmark assets."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.adapters.base import load_manifest
from benchmarks.benchmark_runner import LANE_CONFIGS, MANIFEST_DIR


EXPECTED_MANIFESTS = {
    "B15": "b15-intake-mutation-subset.json",
    "B16": "b16-requirements-feature-subset.json",
    "B17": "b17-long-horizon-subset.json",
    "B18": "b18-heldout-prototype-subset.json",
    "B19": "b19-multilingual-subset.json",
    "B20": "b20-terminal-ops-subset.json",
    "B21": "b21-regression-contract-subset.json",
    "B22": "b22-corruption-subset.json",
    "B23": "b23-sync-subset.json",
    "B24": "b24-security-subset.json",
    "B25": "b25-managerial-subset.json",
    "B26": "b26-economic-value-subset.json",
    "B27": "b27-efficiency-subset.json",
    "B28": "b28-repeatability-subset.json",
    "B29": "b29-fault-resilience-subset.json",
}


def test_b15_b29_lane_configs_reference_expected_manifests():
    for lane, manifest_name in EXPECTED_MANIFESTS.items():
        assert LANE_CONFIGS[lane]["manifest"] == manifest_name


def test_b15_b29_manifests_load_and_have_existing_fixtures():
    total_tasks = 0

    for lane, manifest_name in EXPECTED_MANIFESTS.items():
        manifest_path = MANIFEST_DIR / manifest_name
        assert manifest_path.exists(), f"{lane} manifest missing: {manifest_path}"

        meta, tasks = load_manifest(manifest_path)
        assert meta["comparison_validity"] == "prototype-only"
        assert tasks, f"{lane} has no tasks"
        total_tasks += len(tasks)

        for task in tasks:
            fixture_rel = task.extra.get("fixture_dir")
            assert fixture_rel, f"{lane}/{task.task_id} missing fixture_dir"
            fixture_path = MANIFEST_DIR / fixture_rel
            assert fixture_path.exists(), f"{lane}/{task.task_id} fixture missing"

            if LANE_CONFIGS[lane]["runner"] == "competitive":
                assert (fixture_path / "prompt.md").exists()
                assert (fixture_path / "grader.py").exists()
                assert (fixture_path / "solution.py").exists()

    assert total_tasks == 17


def test_b15_b29_reference_docs_exist():
    docs_dir = Path("docs/plan/agentic-benchmarks")
    required_docs = [
        "portfolio-b15-b29.md",
        "b15-b29-execution-plan.md",
        "b15-b29-feasibility.md",
        "b15-b29-first-run-findings.md",
        "b15-b29-sentinel-rerun-findings.md",
        "b15-b29-second-pass-findings.md",
        "b15-b29-swebench-alias-findings.md",
    ]

    for name in required_docs:
        assert (docs_dir / name).exists(), f"missing benchmark doc: {name}"
