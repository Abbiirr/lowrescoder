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
        assert meta["comparison_validity"] in ("prototype-only", "internal")
        assert tasks, f"{lane} has no tasks"
        total_tasks += len(tasks)

        for task in tasks:
            fixture_rel = task.extra.get("fixture_dir")
            assert fixture_rel, f"{lane}/{task.task_id} missing fixture_dir"
            fixture_path = MANIFEST_DIR / fixture_rel
            assert fixture_path.exists(), f"{lane}/{task.task_id} fixture missing"

            if LANE_CONFIGS[lane].get("runner") == "competitive":
                assert (fixture_path / "prompt.md").exists()
                assert (fixture_path / "grader.py").exists()
                assert (fixture_path / "solution.py").exists()
            else:
                # Standard fixture must have setup.sh and verify.sh
                grading = task.grading_command
                if grading and "verify.sh" in grading:
                    assert (fixture_path / "verify.sh").exists(), (
                        f"{lane}/{task.task_id}: verify.sh missing at {fixture_path}"
                    )
                if task.extra.get("setup_commands"):
                    for cmd in task.extra["setup_commands"]:
                        if "setup.sh" in cmd:
                            assert (fixture_path / "setup.sh").exists(), (
                                f"{lane}/{task.task_id}: setup.sh missing at {fixture_path}"
                            )

    assert total_tasks >= 17  # grows as lanes expand to 5+ tasks


def test_b15_b29_reference_docs_exist():
    docs_dir = PROJECT_ROOT / "docs/plan/agentic-benchmarks"
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


def test_b29_fault_resilience_tasks_force_host_mode():
    """B29 tasks intentionally run on the host instead of Docker bootstrapping."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B29"]
    _, tasks = load_manifest(manifest_path)

    assert tasks
    for task in tasks:
        assert task.extra.get("force_host") is True


def test_b19_setup_heavy_tasks_force_host_mode():
    """B19 tasks that do not need Docker bootstrap should stay on host mode."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B19"]
    _, tasks = load_manifest(manifest_path)
    by_id = {task.task_id: task for task in tasks}

    assert by_id["b19-fix-shell-pipeline"].extra.get("force_host") is True
    assert by_id["b19-fix-dockerfile"].extra.get("force_host") is True
    assert by_id["b19-fix-yaml-config"].extra.get("force_host") is True
    assert by_id["b19-bash-script-fix"].extra.get("force_host") is True
    assert by_id["b19-makefile-fix"].extra.get("force_host") is True
    assert "build_deps_profile" not in by_id["b19-makefile-fix"].extra


def test_b24_weak_password_hashing_stays_on_host_mode():
    """The bcrypt fixture should not spend 900s in the heavy Docker bootstrap."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B24"]
    _, tasks = load_manifest(manifest_path)
    by_id = {task.task_id: task for task in tasks}

    assert by_id["b24-weak-password-hashing"].extra.get("force_host") is True


def test_b28_idempotent_migration_stays_on_host_mode():
    """B28 fixtures are all simple Python tasks and should stay on the host path."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B28"]
    _, tasks = load_manifest(manifest_path)
    by_id = {task.task_id: task for task in tasks}

    assert by_id["b28-atomic-file-write"].extra.get("force_host") is True
    assert by_id["b28-consistent-config"].extra.get("force_host") is True
    assert by_id["b28-deterministic-sort"].extra.get("force_host") is True
    assert by_id["b28-idempotent-migration"].extra.get("force_host") is True
    assert by_id["b28-reproducible-hash"].extra.get("force_host") is True


def test_b17_tasks_that_require_test_rewrites_allow_test_file_edits():
    """B17 includes two legitimate test-rewrite tasks."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B17"]
    _, tasks = load_manifest(manifest_path)
    by_id = {task.task_id: task for task in tasks}

    for task in by_id.values():
        assert task.extra.get("force_host") is True
    assert by_id["b17-rename-module"].extra.get("allow_test_file_edits") is True
    assert by_id["b17-split-test-file"].extra.get("allow_test_file_edits") is True


def test_b28_idempotent_migration_task_md_mentions_sqlite_lock_safety():
    """The task prompt should mention repeated-process SQLite lock safety."""
    task_md = (
        MANIFEST_DIR
        / "fixtures/b28/b28-idempotent-migration/task.md"
    ).read_text(encoding="utf-8")

    assert "same Python process" in task_md
    assert "database is locked" in task_md
    assert "Do not delete, recreate, or hand-edit `project/app.db`" in task_md


def test_b28_idempotent_migration_protects_database_file():
    """The agent should fix migrate.py, not mutate the seeded database."""
    manifest_path = MANIFEST_DIR / EXPECTED_MANIFESTS["B28"]
    _, tasks = load_manifest(manifest_path)
    by_id = {task.task_id: task for task in tasks}

    assert by_id["b28-idempotent-migration"].extra.get("protected_paths") == [
        "project/app.db",
    ]


def test_b17_split_test_file_task_md_mentions_source_bug_and_test_edits():
    """The split fixture should acknowledge the exposed source bug and allowed test edits."""
    task_md = (
        MANIFEST_DIR
        / "fixtures/b17/b17-split-test-file/task.md"
    ).read_text(encoding="utf-8")

    assert "small real bug" in task_md
    assert "allowed to edit `test_all.py`" in task_md


def test_b17_rename_module_task_md_mentions_test_import_updates():
    """The rename-module fixture must explicitly allow the required test import rewrite."""
    task_md = (
        MANIFEST_DIR
        / "fixtures/b17/b17-rename-module/task.md"
    ).read_text(encoding="utf-8")

    assert "including `test_app.py`" in task_md
    assert "allowed and expected to edit `test_app.py`" in task_md


def test_b17_split_test_file_verifier_handles_empty_test_all_and_correct_count():
    """The verifier should treat a tombstoned test_all.py cleanly and expect all 34 tests."""
    verify_sh = (
        MANIFEST_DIR
        / "fixtures/b17/b17-split-test-file/verify.sh"
    ).read_text(encoding="utf-8")

    assert "TEST_CLASSES=${TEST_CLASSES:-0}" in verify_sh
    assert "TEST_DEFS=${TEST_DEFS:-0}" in verify_sh
    assert "ORIGINAL_TEST_COUNT=34" in verify_sh


def test_b29_corrupt_data_task_md_matches_verifier_contract():
    """The corrupt-data task prompt must not contradict tests/verifier return type."""
    task_md = (
        MANIFEST_DIR
        / "fixtures/b29/b29-handle-corrupt-data/task.md"
    ).read_text(encoding="utf-8")

    assert "return both the parsed data and a count of skipped rows" not in task_md
    assert "return a list of row dicts" in task_md


def test_b29_disk_full_task_md_matches_exception_contract():
    """The disk-full task prompt must match the tests' non-OSError expectation."""
    task_md = (
        MANIFEST_DIR
        / "fixtures/b29/b29-handle-disk-full/task.md"
    ).read_text(encoding="utf-8")

    assert "Do not propagate a bare `OSError`" in task_md


def test_b29_network_timeout_setup_uses_python_module_pip():
    """The network-timeout fixture should not depend on a bare pip binary."""
    setup_sh = (
        MANIFEST_DIR
        / "fixtures/b29/b29-handle-network-timeout/setup.sh"
    ).read_text(encoding="utf-8")

    assert "python -m pip install requests" in setup_sh


def test_b29_permission_denied_setup_does_not_precreate_unreadable_file():
    """Permission trap must be created at test time, not before baseline commit."""
    setup_sh = (
        MANIFEST_DIR
        / "fixtures/b29/b29-handle-permission-denied/setup.sh"
    ).read_text(encoding="utf-8")

    assert "chmod 000 denied.txt" not in setup_sh
