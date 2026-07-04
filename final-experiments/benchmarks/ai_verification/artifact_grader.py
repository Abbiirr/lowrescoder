"""Artifact grader for AI verification harness.

Deterministic grader that checks diff and file artifacts against scenario
artifact assertions: required changes, forbidden changes, non-empty diff,
must-contain, and must-remove text checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArtifactAssertionResult:
    assertion: str
    passed: bool
    detail: str = ""


@dataclass
class ArtifactReport:
    passed: bool
    results: list[ArtifactAssertionResult] = field(default_factory=list)

    @property
    def failures(self) -> list[ArtifactAssertionResult]:
        return [r for r in self.results if not r.passed]


def grade_artifacts(
    diff_patch: str,
    changed_files: list[str],
    sandbox: Path | None = None,
    assertions: dict | None = None,
) -> ArtifactReport:
    assertions = assertions or {}
    results: list[ArtifactAssertionResult] = []

    if assertions.get("require_non_empty_diff"):
        if diff_patch.strip() and diff_patch.strip() != "(no changes from seed commit)":
            results.append(ArtifactAssertionResult(
                assertion="require_non_empty_diff",
                passed=True,
            ))
        else:
            results.append(ArtifactAssertionResult(
                assertion="require_non_empty_diff",
                passed=False,
                detail="diff is empty or unchanged from seed",
            ))

    if assertions.get("forbid_noop_pass"):
        if not changed_files:
            results.append(ArtifactAssertionResult(
                assertion="forbid_noop_pass",
                passed=False,
                detail="no files changed — agent did nothing",
            ))
        else:
            results.append(ArtifactAssertionResult(
                assertion="forbid_noop_pass",
                passed=True,
            ))

    must_change = assertions.get("must_change_files", [])
    if must_change:
        missing = [f for f in must_change if f not in changed_files]
        if missing:
            results.append(ArtifactAssertionResult(
                assertion="must_change_files",
                passed=False,
                detail=f"files not changed: {missing}",
            ))
        else:
            results.append(ArtifactAssertionResult(
                assertion="must_change_files",
                passed=True,
            ))

    must_not_change = assertions.get("must_not_change_files", [])
    if must_not_change:
        forbidden = [f for f in must_not_change if f in changed_files]
        if forbidden:
            results.append(ArtifactAssertionResult(
                assertion="must_not_change_files",
                passed=False,
                detail=f"forbidden files changed: {forbidden}",
            ))
        else:
            results.append(ArtifactAssertionResult(
                assertion="must_not_change_files",
                passed=True,
            ))

    must_remove = assertions.get("must_remove_text", [])
    if must_remove and sandbox and sandbox.is_dir():
        for spec in must_remove:
            if isinstance(spec, dict):
                file_path = spec.get("file", "")
                text = spec.get("text", "")
            else:
                file_path = ""
                text = spec
            if file_path:
                target = sandbox / file_path
                if target.is_file():
                    content = target.read_text(errors="replace")
                    if text in content:
                        results.append(ArtifactAssertionResult(
                            assertion=f"must_remove_text({file_path}, {text!r})",
                            passed=False,
                            detail=f"text still present in final file {file_path}",
                        ))
                    else:
                        results.append(ArtifactAssertionResult(
                            assertion=f"must_remove_text({file_path}, {text!r})",
                            passed=True,
                        ))
                else:
                    results.append(ArtifactAssertionResult(
                        assertion=f"must_remove_text({file_path}, {text!r})",
                        passed=True,
                        detail=f"file {file_path} no longer exists — text removed",
                    ))
            else:
                _check_text_removed_from_all_files(sandbox, text, results)

    must_contain = assertions.get("must_contain_text", {})
    if must_contain and sandbox and sandbox.is_dir():
        for file_path, required_texts in must_contain.items():
            target = sandbox / file_path
            if not target.is_file():
                results.append(ArtifactAssertionResult(
                    assertion=f"must_contain_text({file_path})",
                    passed=False,
                    detail=f"file {file_path} not found",
                ))
                continue
            content = target.read_text(errors="replace")
            for text in required_texts:
                if text in content:
                    results.append(ArtifactAssertionResult(
                        assertion=f"must_contain_text({file_path}, {text!r})",
                        passed=True,
                    ))
                else:
                    results.append(ArtifactAssertionResult(
                        assertion=f"must_contain_text({file_path}, {text!r})",
                        passed=False,
                        detail=f"text not found in {file_path}",
                    ))

    all_passed = all(r.passed for r in results)
    return ArtifactReport(passed=all_passed, results=results)


def _check_text_removed_from_all_files(
    sandbox: Path, text: str, results: list[ArtifactAssertionResult],
) -> None:
    for py_file in sorted(sandbox.rglob("*.py")):
        try:
            content = py_file.read_text(errors="replace")
        except OSError:
            continue
        if text in content:
            rel = py_file.relative_to(sandbox)
            results.append(ArtifactAssertionResult(
                assertion=f"must_remove_text({text!r})",
                passed=False,
                detail=f"text still present in {rel}",
            ))
            return
    results.append(ArtifactAssertionResult(
        assertion=f"must_remove_text({text!r})",
        passed=True,
    ))


def extract_changed_files(diff_patch: str) -> list[str]:
    files = []
    for line in diff_patch.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" b/")
            if len(parts) >= 2:
                path = parts[-1].strip()
                if not _is_generated_artifact_noise(path):
                    files.append(path)
    return files


def _is_generated_artifact_noise(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.endswith(".pyc")
        or "/__pycache__/" in f"/{normalized}"
        or normalized.endswith(".pyo")
    )
