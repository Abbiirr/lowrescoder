"""Channel B — eval-oracle branch (PLAN_05 §3.1, §3.2, §3.3).

Drive an authorized target on a task, capture only the observable final artifact
(the diff / file set), keep only the *verified* outcomes, and store them under
``$AUTOCODE_ANVIL_ROOT/copycat/outcomes/corpus@v<N>/<task>.json`` with a
``verification`` block. The verified-outcome corpus is a *weak oracle*: for a
task with no shipped test, the strong model's accepted solution becomes a
reference the verifier can diff against.

Critical discipline (PLAN_05 §3.3): **keep only verified outcomes.** You are not
trusting the teacher — you are trusting the tests. Unverified diffs are dropped
on the floor; nothing is written to disk for them.

Rate-limit (PLAN_05 §5, open question Q3 line 486): default 50 verified-outcome
captures per UTC day per target, tunable via the registry's
``rate_limit.runs_per_day`` field.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autocode.anvil import paths
from autocode.anvil.registry import Registry, Target, load_registry

# Default rate limit per target per UTC day (PLAN_05 §5 / Q3 line 486).
DEFAULT_RATE_LIMIT = 50

# Channel / scope enforced by the eval-oracle branch.
CHANNEL = "outcome"
SCOPE = "outcomes"

Driver = Callable[["Task"], "Diff"]
Verifier = Callable[["Diff", "Task"], "VerificationLabel"]


class OutcomeError(Exception):
    """A Channel B eval-oracle capture was refused."""


@dataclass(frozen=True)
class Task:
    """One Channel B task: an id, a prompt, and a check plan (the oracle)."""

    task_id: str
    prompt: str = ""
    check_plan: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "check_plan": list(self.check_plan),
        }
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d


@dataclass(frozen=True)
class Diff:
    """The observable final artifact a target produced on a task."""

    text: str
    files: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "files": list(self.files)}


@dataclass(frozen=True)
class VerificationLabel:
    """The verifier's verdict on a captured diff.

    The label is one of ``verified`` / ``failed`` / ``skipped``. Only
    ``verified`` outcomes are persisted.
    """

    label: str  # "verified" | "failed" | "skipped"
    returncode: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "returncode": self.returncode,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class Outcome:
    """A verified (target, task, diff) tuple persisted under corpus@v<N>/."""

    task_id: str
    target: str
    diff: Diff
    verification: VerificationLabel
    captured_at: str
    sha256: str
    corpus_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "target": self.target,
            "channel": CHANNEL,
            "reuse_scope": SCOPE,
            "corpus_version": self.corpus_version,
            "diff": self.diff.to_dict(),
            "verification": self.verification.to_dict(),
            "captured_at": self.captured_at,
            "sha256": self.sha256,
        }


def _default_driver(task: Task) -> Diff:
    """Production driver: invoke the gateway's thinking/big alias.

    Not wired here — Channel B is offline-by-default and the operator injects a
    real gateway-backed driver (or a fixture for tests). Calling this default
    raises so a misconfigured run fails loudly instead of silently producing an
    empty corpus.
    """
    raise OutcomeError(
        "no Channel B driver is configured. Pass `driver=` to capture(), "
        "patch `_default_driver`, or wire a gateway-backed driver."
    )


def _default_verifier(diff: Diff, task: Task) -> VerificationLabel:
    """Production verifier: apply the diff and run its check plan.

    The default mirrors :mod:`autocode.anvil.gate` — it shells out to
    ``uv run pytest <check_plan>`` in the repo root and labels the diff
    ``verified`` iff the checks pass. For offline/test runs, inject a fake.
    """
    import subprocess

    if not task.check_plan:
        return VerificationLabel(label="skipped", returncode=0, summary="no check plan")
    cmd = ["uv", "run", "pytest", *task.check_plan, "-q"]
    proc = subprocess.run(  # noqa: S603 - fixed launcher, task-derived test paths
        cmd,
        cwd=str(paths._PACKAGE_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-4000:]
    label = "verified" if proc.returncode == 0 else "failed"
    summary = tail.splitlines()[-1] if tail else ""
    return VerificationLabel(label=label, returncode=proc.returncode, summary=summary)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def outcomes_root(root: Path) -> Path:
    """``<anvil>/copycat/outcomes/`` — the parent of all corpus versions."""
    return paths.copycat_dir(root) / "outcomes"


def corpus_dir(root: Path, version: int) -> Path:
    """``<anvil>/copycat/outcomes/corpus@v<N>/`` for one corpus version."""
    return outcomes_root(root) / f"corpus@v{version}"


def latest_corpus_version(root: Path) -> int:
    """Highest existing corpus version, or 0 if none yet."""
    parent = outcomes_root(root)
    if not parent.is_dir():
        return 0
    versions: list[int] = []
    for child in parent.iterdir():
        m = re.fullmatch(r"corpus@v(\d+)", child.name)
        if child.is_dir() and m:
            versions.append(int(m.group(1)))
    return max(versions) if versions else 0


def bump_corpus(root: Path) -> int:
    """Create the next corpus version dir and return its number.

    Existing outcomes stay where they are (corpus versions are immutable once
    superseded — a new version is a fresh start, not a rewrite).
    """
    anvil = paths.anvil_root(root)
    version = latest_corpus_version(anvil) + 1
    corpus_dir(anvil, version).mkdir(parents=True, exist_ok=True)
    return version


def _active_corpus_dir(root: Path) -> Path:
    """The corpus dir new captures write into (latest, creating v1 if empty)."""
    anvil = paths.anvil_root(root)
    version = latest_corpus_version(anvil)
    if version == 0:
        version = 1
        corpus_dir(anvil, version).mkdir(parents=True, exist_ok=True)
    return corpus_dir(anvil, version)


def _active_corpus_version(root: Path) -> int:
    anvil = paths.anvil_root(root)
    version = latest_corpus_version(anvil)
    return version or 1


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


def _rate_limit_for(target: Target) -> int:
    if isinstance(target.rate_limit, dict):
        try:
            return int(target.rate_limit.get("runs_per_day", DEFAULT_RATE_LIMIT))
        except (TypeError, ValueError):
            return DEFAULT_RATE_LIMIT
    return DEFAULT_RATE_LIMIT


def count_outcomes_on(corpus: Path, *, utc_day: str) -> int:
    """Count outcome files in ``corpus`` captured on the given UTC day (YYYY-MM-DD)."""
    if not corpus.is_dir():
        return 0
    n = 0
    for child in corpus.glob("*.json"):
        try:
            data = json.loads(child.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        captured = str(data.get("captured_at", ""))
        # Match either a full ISO timestamp or a bare date prefix.
        if captured.startswith(utc_day):
            n += 1
    return n


def _enforce_rate_limit(target: Target, corpus: Path, *, now: datetime | None = None) -> None:
    limit = _rate_limit_for(target)
    utc_day = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
    used = count_outcomes_on(corpus, utc_day=utc_day)
    if used >= limit:
        raise OutcomeError(
            f"Channel B rate limit reached for target '{target.id}': "
            f"{used}/{limit} captures on {utc_day}. Raise "
            f"`rate_limit.runs_per_day` in registry.yaml or wait until tomorrow."
        )


# ---------------------------------------------------------------------------
# Hash (deterministic across runs with identical inputs)
# ---------------------------------------------------------------------------


def _outcome_sha256(task: Task, target: str, diff: Diff) -> str:
    """Stable hash over the *content* of a verified outcome.

    Intentionally excludes the capture timestamp so the hash is reproducible:
    the same (target, task_id, prompt, diff.text, diff.files) always hashes to
    the same value. This is what the distillation dataset and the
    snapshot/fixture checks rely on.
    """
    payload = json.dumps(
        {
            "target": target,
            "task_id": task.task_id,
            "prompt": task.prompt,
            "check_plan": list(task.check_plan),
            "diff_text": diff.text,
            "diff_files": list(diff.files),
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(task_id: str) -> str:
    """Collapse a task id into a filesystem-safe stem (keep the dot-suffix out)."""
    stem = _SAFE_RE.sub("_", task_id).strip("._-")
    return stem or "task"


# ---------------------------------------------------------------------------
# The capture driver
# ---------------------------------------------------------------------------


def capture(
    target: str,
    task: Task,
    *,
    driver: Driver | None = None,
    verifier: Verifier | None = None,
    root: Path | str | None = None,
    timestamp: str | None = None,
    registry: Registry | None = None,
    now: datetime | None = None,
) -> Outcome:
    """Drive ``target`` on ``task``, capture the verified diff to the corpus.

    Sequence (PLAN_05 §3.2):

      task -> target (authorized) -> diff -> verifier(diff) -> outcome-pair

    Only ``verified`` diffs are persisted. Unverified diffs raise
    :class:`OutcomeError` and write nothing.

    The registry hard-gate is enforced against channel ``outcome`` and scope
    ``outcomes`` (use :mod:`autocode.anvil.copycat.distill` for the
    ``weights``-scope branch). The per-target per-UTC-day rate limit is enforced
    before the target is driven, so a misconfigured limit cannot burn budget.

    ``now`` overrides the "current" datetime used both for rate-limit accounting
    and as the default for ``captured_at``. Tests pass an explicit ``now`` (and
    typically a matching ``timestamp``) so the rate-limit window is
    deterministic.
    """
    anvil = paths.anvil_root(root)
    reg = registry or load_registry(paths.registry_path(anvil))
    # Hard gate.
    reg.assert_channel_allowed(target, CHANNEL)
    reg.assert_reuse_scope(target, SCOPE)
    target_obj = reg.get(target)

    moment = now or datetime.now(UTC)
    corpus = _active_corpus_dir(anvil)
    _enforce_rate_limit(target_obj, corpus, now=moment)

    drv = driver or _default_driver
    ver = verifier or _default_verifier

    diff = drv(task)
    label = ver(diff, task)
    if label.label != "verified":
        raise OutcomeError(
            f"diff for task '{task.task_id}' from '{target}' was not verified "
            f"(label={label.label}, returncode={label.returncode}): {label.summary}"
        )

    version = _active_corpus_version(anvil)
    outcome = Outcome(
        task_id=task.task_id,
        target=target,
        diff=diff,
        verification=label,
        captured_at=timestamp or moment.isoformat(),
        sha256=_outcome_sha256(task, target, diff),
        corpus_version=version,
    )

    corpus.mkdir(parents=True, exist_ok=True)
    path = corpus / f"{_safe_filename(task.task_id)}.json"
    path.write_text(json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8")
    return outcome


def iter_outcomes(corpus: Path) -> list[Outcome]:
    """Read every ``*.json`` outcome in ``corpus`` (used by the distiller)."""
    if not corpus.is_dir():
        return []
    results: list[Outcome] = []
    for child in sorted(corpus.glob("*.json")):
        try:
            data = json.loads(child.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        diff_raw = data.get("diff") or {}
        ver_raw = data.get("verification") or {}
        results.append(
            Outcome(
                task_id=str(data.get("task_id", "")),
                target=str(data.get("target", "")),
                diff=Diff(
                    text=str(diff_raw.get("text", "")),
                    files=tuple(diff_raw.get("files", []) or []),
                ),
                verification=VerificationLabel(
                    label=str(ver_raw.get("label", "")),
                    returncode=int(ver_raw.get("returncode", 0)),
                    summary=str(ver_raw.get("summary", "")),
                ),
                captured_at=str(data.get("captured_at", "")),
                sha256=str(data.get("sha256", "")),
                corpus_version=int(data.get("corpus_version", 1)),
            )
        )
    return results


# Tuples/dataclasses re-exported for type-checkers that dislike asdict on frozen.
_ = asdict  # kept for future expansion; not on a hot path
