"""Tests for Channel B — outcome distillation (PLAN_05 §3).

Two branches, gated separately by the registry's ``reuse_scope``:

* :mod:`autocode.anvil.copycat.outcome` — the **eval-oracle branch**
  (``reuse_scope: outcomes``). Always safe; captures verified diffs into the
  ``corpus@v<N>`` corpus.
* :mod:`autocode.anvil.copycat.distill` — the **distillation branch**
  (``reuse_scope: weights`` + recorded ToS check). Renders the corpus as a
  teacher-replayable ``dataset.jsonl`` whose SHA-256 is the deterministic
  fixture-match the PLAN_05 closing gate checks.

All tests are offline: the gateway-backed driver/verifier are replaced by
deterministic fakes via ``unittest.mock.patch``. The PLAN_05 manual check in
TESTING.md ("Channel B (outcome distillation) renders a teacher-replayable form
whose hash matches a fixture") is covered by
:func:`test_distill_dataset_hash_is_deterministic`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from autocode.anvil import paths
from autocode.anvil.copycat import distill as channel_b_distill
from autocode.anvil.copycat import outcome as channel_b_outcome
from autocode.anvil.copycat.distill import DistillError
from autocode.anvil.copycat.outcome import (
    Diff,
    OutcomeError,
    Task,
    VerificationLabel,
)
from autocode.anvil.registry import RegistryError
from autocode.cli import app

runner = CliRunner()


REGISTRY_OUTCOMES = """\
targets:
  - id: gateway-thinking-alias
    channel: [outcome]
    source: "gateway thinking/big alias (mocked for tests)"
    license: "review-before-use"
    reuse_scope: outcomes
    rate_limit: {runs_per_day: 50}
    notes: "Channel B eval-oracle test fixture."
"""

REGISTRY_OUTCOMES_TIGHT_LIMIT = """\
targets:
  - id: gateway-thinking-alias
    channel: [outcome]
    source: "x"
    license: "x"
    reuse_scope: outcomes
    rate_limit: {runs_per_day: 2}
"""

REGISTRY_WEIGHTS_NO_TOS = """\
targets:
  - id: frontier-distill
    channel: [outcome]
    source: "x"
    license: "x"
    reuse_scope: weights
    notes: "weights scope but no ToS check recorded."
"""

REGISTRY_WEIGHTS_WITH_TOS = """\
targets:
  - id: frontier-distill
    channel: [outcome]
    source: "x"
    license: "x"
    reuse_scope: weights
    tos_check:
      provider: anthropic
      reviewed_on: "2026-06-22"
      clause_summary: "outputs may be used for non-competing local training"
    notes: "weights scope with recorded per-provider ToS check."
"""

REGISTRY_STRUCTURAL_ONLY = """\
targets:
  - id: puku-cli
    channel: [structural]
    source: "x"
    license: "x"
    reuse_scope: structure_only
"""


def _seed(tmp_path: Path, registry_yaml: str) -> Path:
    root = tmp_path / "anvil"
    (root / "copycat").mkdir(parents=True)
    (root / "copycat" / "registry.yaml").write_text(registry_yaml)
    return root


def _fake_driver(task: Task) -> Diff:
    return Diff(text="--- a.py\n+++ a.py\n@@\n-old\n+new\n", files=("a.py",))


def _fake_verifier_pass(diff: Diff, task: Task) -> VerificationLabel:
    return VerificationLabel(label="verified", returncode=0, summary="1 passed")


def _fake_verifier_fail(diff: Diff, task: Task) -> VerificationLabel:
    return VerificationLabel(label="failed", returncode=1, summary="1 failed")


# ---------------------------------------------------------------------------
# Eval-oracle branch (outcome.py)
# ---------------------------------------------------------------------------


def test_capture_writes_verified_outcome(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    task = Task(
        task_id="add-foo-flag",
        prompt="add a --foo flag",
        check_plan=("tests/test_foo.py",),
    )

    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        oc = channel_b_outcome.capture("gateway-thinking-alias", task, root=root)

    assert oc.verification.label == "verified"
    assert oc.target == "gateway-thinking-alias"
    assert oc.sha256

    f = channel_b_outcome.corpus_dir(root, 1) / "add-foo-flag.json"
    assert f.is_file(), f"expected verified outcome at {f}"
    data = json.loads(f.read_text())
    assert data["task_id"] == "add-foo-flag"
    assert data["target"] == "gateway-thinking-alias"
    assert data["channel"] == "outcome"
    assert data["reuse_scope"] == "outcomes"
    assert data["verification"]["label"] == "verified"
    assert data["sha256"] == oc.sha256
    assert data["corpus_version"] == 1


def test_capture_creates_corpus_v1_when_absent(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    task = Task(task_id="t1", prompt="p", check_plan=())
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture("gateway-thinking-alias", task, root=root)
    assert channel_b_outcome.latest_corpus_version(root) == 1
    assert channel_b_outcome.corpus_dir(root, 1).is_dir()


def test_capture_drops_unverified_diff(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    task = Task(task_id="t1", prompt="p", check_plan=("t.py",))

    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_fail),
    ):
        with pytest.raises(OutcomeError, match="not verified"):
            channel_b_outcome.capture("gateway-thinking-alias", task, root=root)

    # Nothing persisted for an unverified diff.
    assert not (channel_b_outcome.corpus_dir(root, 1) / "t1.json").is_file()


def test_capture_refused_for_unknown_target(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    task = Task(task_id="t1", prompt="p", check_plan=())
    with pytest.raises(RegistryError, match="not in the registry"):
        channel_b_outcome.capture("not-a-target", task, root=root)


def test_capture_refused_when_outcome_channel_not_enabled(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_STRUCTURAL_ONLY)
    task = Task(task_id="t1", prompt="p", check_plan=())
    with pytest.raises(RegistryError, match="channel 'outcome' is not enabled"):
        channel_b_outcome.capture("puku-cli", task, root=root)


def test_capture_refused_when_scope_below_outcomes(tmp_path: Path) -> None:
    # structure_only grants less than outcomes -> Channel B eval-oracle refused.
    reg_yaml = REGISTRY_STRUCTURAL_ONLY.replace(
        "channel: [structural]", "channel: [outcome, structural]"
    )
    root = _seed(tmp_path, reg_yaml)
    task = Task(task_id="t1", prompt="p", check_plan=())
    with pytest.raises(RegistryError, match="reuse_scope"):
        channel_b_outcome.capture("puku-cli", task, root=root)


def test_rate_limit_enforced(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES_TIGHT_LIMIT)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "gateway-thinking-alias", Task(task_id="t1", prompt="p"),
            root=root,
            timestamp="2026-06-22T10:00:00+00:00",
            now=datetime.fromisoformat("2026-06-22T10:00:00+00:00"),
        )
        channel_b_outcome.capture(
            "gateway-thinking-alias", Task(task_id="t2", prompt="p"),
            root=root,
            timestamp="2026-06-22T11:00:00+00:00",
            now=datetime.fromisoformat("2026-06-22T11:00:00+00:00"),
        )
        with pytest.raises(OutcomeError, match="rate limit"):
            channel_b_outcome.capture(
                "gateway-thinking-alias", Task(task_id="t3", prompt="p"),
                root=root,
                timestamp="2026-06-22T12:00:00+00:00",
                now=datetime.fromisoformat("2026-06-22T12:00:00+00:00"),
            )


def test_rate_limit_default_is_50(tmp_path: Path) -> None:
    # A target with no explicit rate_limit uses the 50/day default.
    no_limit = REGISTRY_OUTCOMES.replace("    rate_limit: {runs_per_day: 50}\n", "")
    root = _seed(tmp_path, no_limit)
    from autocode.anvil.registry import load_registry

    reg = load_registry(paths.registry_path(root))
    assert channel_b_outcome._rate_limit_for(reg.get("gateway-thinking-alias")) == 50


def test_rate_limit_resets_per_utc_day(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES_TIGHT_LIMIT)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "gateway-thinking-alias", Task(task_id="t1", prompt="p"),
            root=root,
            timestamp="2026-06-22T10:00:00+00:00",
            now=datetime.fromisoformat("2026-06-22T10:00:00+00:00"),
        )
        channel_b_outcome.capture(
            "gateway-thinking-alias", Task(task_id="t2", prompt="p"),
            root=root,
            timestamp="2026-06-22T11:00:00+00:00",
            now=datetime.fromisoformat("2026-06-22T11:00:00+00:00"),
        )
        # Next UTC day: limit resets.
        channel_b_outcome.capture(
            "gateway-thinking-alias", Task(task_id="t3", prompt="p"),
            root=root,
            timestamp="2026-06-23T00:00:00+00:00",
            now=datetime.fromisoformat("2026-06-23T00:00:00+00:00"),
        )


def test_bump_corpus_increments_version(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    assert channel_b_outcome.latest_corpus_version(root) == 0
    v1 = channel_b_outcome.bump_corpus(root)
    assert v1 == 1
    assert channel_b_outcome.corpus_dir(root, 1).is_dir()
    v2 = channel_b_outcome.bump_corpus(root)
    assert v2 == 2
    assert channel_b_outcome.latest_corpus_version(root) == 2


def test_capture_writes_into_latest_corpus_version(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    channel_b_outcome.bump_corpus(root)  # start at v1 explicitly
    channel_b_outcome.bump_corpus(root)  # now v2
    task = Task(task_id="t1", prompt="p", check_plan=())
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        oc = channel_b_outcome.capture("gateway-thinking-alias", task, root=root)
    assert oc.corpus_version == 2
    assert (channel_b_outcome.corpus_dir(root, 2) / "t1.json").is_file()


def test_outcome_sha256_is_deterministic(tmp_path: Path) -> None:
    """The outcome hash is reproducible: same inputs -> same hash."""
    task = Task(task_id="t1", prompt="p", check_plan=("a.py",))
    diff = Diff(text="x", files=("a.py",))
    h1 = channel_b_outcome._outcome_sha256(task, "tgt", diff)
    h2 = channel_b_outcome._outcome_sha256(task, "tgt", diff)
    assert h1 == h2
    # Different target -> different hash.
    assert h1 != channel_b_outcome._outcome_sha256(task, "other", diff)
    # Different diff -> different hash.
    assert h1 != channel_b_outcome._outcome_sha256(task, "tgt", Diff(text="y", files=("a.py",)))


# ---------------------------------------------------------------------------
# Distillation branch (distill.py)
# ---------------------------------------------------------------------------


def _seed_with_outcome(
    tmp_path: Path,
    registry_yaml: str,
    *,
    target: str,
    task_id: str = "t1",
) -> Path:
    root = _seed(tmp_path, registry_yaml)
    task = Task(task_id=task_id, prompt="add a --foo flag", check_plan=("tests/test_foo.py",))
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(target, task, root=root)
    return root


def test_distill_refused_without_weights_scope(tmp_path: Path) -> None:
    root = _seed_with_outcome(tmp_path, REGISTRY_OUTCOMES, target="gateway-thinking-alias")
    with pytest.raises(DistillError, match="reuse_scope"):
        channel_b_distill.distill("gateway-thinking-alias", root=root)


def test_distill_refused_without_tos_check(tmp_path: Path) -> None:
    root = _seed_with_outcome(tmp_path, REGISTRY_WEIGHTS_NO_TOS, target="frontier-distill")
    with pytest.raises(DistillError, match="ToS"):
        channel_b_distill.distill("frontier-distill", root=root)


def test_distill_refused_when_corpus_empty(tmp_path: Path) -> None:
    # Authorized target, but no outcomes captured yet.
    root = _seed(tmp_path, REGISTRY_WEIGHTS_WITH_TOS)
    with pytest.raises(DistillError, match="no verified outcomes"):
        channel_b_distill.distill("frontier-distill", root=root)


def test_distill_writes_dataset_when_authorized(tmp_path: Path) -> None:
    root = _seed_with_outcome(tmp_path, REGISTRY_WEIGHTS_WITH_TOS, target="frontier-distill")
    dataset = channel_b_distill.distill("frontier-distill", root=root)

    assert dataset.path.is_file()
    assert dataset.line_count == 1
    assert dataset.target == "frontier-distill"

    lines = [json.loads(line) for line in dataset.path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["task_id"] == "t1"
    assert lines[0]["verified"] is True
    assert lines[0]["sha256"]
    assert lines[0]["diff_text"] == _fake_driver(Task("t1")).text


def test_distill_dataset_hash_is_deterministic(tmp_path: Path) -> None:
    """The PLAN_05 manual check: dataset hash matches across runs with identical inputs."""
    task = Task(task_id="t1", prompt="add a --foo flag", check_plan=("tests/test_foo.py",))

    # First corpus.
    root1 = _seed(tmp_path / "first", REGISTRY_WEIGHTS_WITH_TOS)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "frontier-distill", task, root=root1, timestamp="2026-06-22T00:00:00+00:00"
        )
    d1 = channel_b_distill.distill("frontier-distill", root=root1)

    # Second corpus: same task/diff, different timestamp -> identical dataset.
    root2 = _seed(tmp_path / "second", REGISTRY_WEIGHTS_WITH_TOS)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "frontier-distill", task, root=root2, timestamp="2026-06-23T00:00:00+00:00"
        )
    d2 = channel_b_distill.distill("frontier-distill", root=root2)

    assert d1.sha256 == d2.sha256
    assert (
        hashlib.sha256(d1.path.read_bytes()).hexdigest()
        == hashlib.sha256(d2.path.read_bytes()).hexdigest()
    )


def test_distill_dataset_hash_changes_with_content(tmp_path: Path) -> None:
    task1 = Task(task_id="t1", prompt="p1", check_plan=("a.py",))
    task2 = Task(task_id="t2", prompt="p2", check_plan=("b.py",))

    def other_driver(_t: Task) -> Diff:
        return Diff(text="--- b.py\n+++ b.py\n@@\n-x\n+y\n", files=("b.py",))

    root1 = _seed(tmp_path / "first", REGISTRY_WEIGHTS_WITH_TOS)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "frontier-distill", task1, root=root1, timestamp="2026-06-22T00:00:00+00:00"
        )
    d1 = channel_b_distill.distill("frontier-distill", root=root1)

    root2 = _seed(tmp_path / "second", REGISTRY_WEIGHTS_WITH_TOS)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", other_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        channel_b_outcome.capture(
            "frontier-distill", task2, root=root2, timestamp="2026-06-22T00:00:00+00:00"
        )
    d2 = channel_b_distill.distill("frontier-distill", root=root2)

    assert d1.sha256 != d2.sha256


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_outcome_command_captures(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        result = runner.invoke(
            app,
            [
                "anvil",
                "copycat",
                "outcome",
                "gateway-thinking-alias",
                "t1",
                "--prompt",
                "add a --foo flag",
                "--anvil-root",
                str(root),
            ],
        )
    assert result.exit_code == 0, result.output
    assert "verified" in result.output.lower()
    assert (channel_b_outcome.corpus_dir(root, 1) / "t1.json").is_file()


def test_cli_outcome_command_refuses_rate_limit(tmp_path: Path) -> None:
    root = _seed(tmp_path, REGISTRY_OUTCOMES_TIGHT_LIMIT)
    with (
        patch("autocode.anvil.copycat.outcome._default_driver", _fake_driver),
        patch("autocode.anvil.copycat.outcome._default_verifier", _fake_verifier_pass),
    ):
        for tid in ("t1", "t2"):
            runner.invoke(
                app,
                [
                    "anvil", "copycat", "outcome",
                    "gateway-thinking-alias", tid, "--anvil-root", str(root),
                ],
            )
        third = runner.invoke(
            app,
            [
                "anvil", "copycat", "outcome",
                "gateway-thinking-alias", "t3", "--anvil-root", str(root),
            ],
        )
    assert third.exit_code != 0
    assert "rate limit" in third.output.lower()


def test_cli_distill_command_writes_dataset(tmp_path: Path) -> None:
    root = _seed_with_outcome(tmp_path, REGISTRY_WEIGHTS_WITH_TOS, target="frontier-distill")
    result = runner.invoke(
        app, ["anvil", "copycat", "distill", "frontier-distill", "--anvil-root", str(root)]
    )
    assert result.exit_code == 0, result.output
    assert "dataset" in result.output.lower()
    assert "sha256" in result.output.lower()


def test_cli_distill_command_refused_without_tos(tmp_path: Path) -> None:
    root = _seed_with_outcome(tmp_path, REGISTRY_WEIGHTS_NO_TOS, target="frontier-distill")
    result = runner.invoke(
        app, ["anvil", "copycat", "distill", "frontier-distill", "--anvil-root", str(root)]
    )
    assert result.exit_code != 0
    assert "refused" in result.output.lower() or "tos" in result.output.lower()
