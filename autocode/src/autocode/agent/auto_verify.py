"""Post-edit verification using registered LSP adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from autocode.layer2.lsp_client import LSPClient
from autocode.layer2.lsp_servers import get_adapter_for_path

DiagnosticProvider = Callable[[Path, Path], Awaitable[list[dict[str, Any]]] | list[dict[str, Any]]]


@dataclass(frozen=True)
class AutoVerifyConfig:
    """Runtime settings for post-edit verification."""

    enabled: bool = True
    max_iterations: int = 3
    on_failure: Literal["surface_to_user", "rollback", "continue"] = "surface_to_user"
    languages: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class VerificationDiagnostic:
    """A normalized diagnostic emitted by an LSP server."""

    path: Path
    line: int
    column: int
    severity: str
    message: str

    def format(self, *, project_root: Path | None = None) -> str:
        try:
            display = self.path.relative_to(project_root) if project_root else self.path
        except ValueError:
            display = self.path
        return f"{display}:{self.line}:{self.column} [{self.severity}] {self.message}"


@dataclass(frozen=True)
class VerificationResult:
    """Result of checking edited files."""

    checked_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    diagnostics: list[VerificationDiagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(diag.severity == "error" for diag in self.diagnostics)

    def to_system_message(self, *, project_root: Path | None = None) -> str:
        if self.ok:
            checked = len(self.checked_files)
            return f"Verification passed: {checked} file{'s' if checked != 1 else ''} checked."
        lines = ["Verification failed:"]
        lines.extend(f"- {diag.format(project_root=project_root)}" for diag in self.diagnostics)
        lines.append("Fix these diagnostics before completing the task.")
        return "\n".join(lines)


async def verify_after_edit(
    edited_files: Iterable[str | Path],
    *,
    project_root: str | Path,
    config: AutoVerifyConfig | None = None,
    diagnostic_provider: DiagnosticProvider | None = None,
) -> VerificationResult:
    """Run diagnostics for edited files with registered LSP adapters.

    Missing adapters are treated as skipped, not failures, so unsupported
    languages do not block editing.
    """
    cfg = config or AutoVerifyConfig()
    if not cfg.enabled:
        return VerificationResult(skipped_files=[Path(path) for path in edited_files])

    root = Path(project_root).resolve()
    enabled_languages = {language.lower() for language in cfg.languages}
    checked: list[Path] = []
    skipped: list[Path] = []
    diagnostics: list[VerificationDiagnostic] = []

    for raw_path in edited_files:
        path = Path(raw_path)
        resolved = path if path.is_absolute() else root / path
        adapter = get_adapter_for_path(resolved)
        if adapter is None:
            skipped.append(resolved)
            continue
        if enabled_languages and adapter.language_id.lower() not in enabled_languages:
            skipped.append(resolved)
            continue
        checked.append(resolved)
        raw_diagnostics = await _diagnostics_for_path(
            resolved,
            root,
            diagnostic_provider=diagnostic_provider,
        )
        diagnostics.extend(
            _normalize_diagnostic(resolved, item)
            for item in raw_diagnostics
        )

    return VerificationResult(
        checked_files=checked,
        skipped_files=skipped,
        diagnostics=diagnostics,
    )


async def _diagnostics_for_path(
    path: Path,
    root: Path,
    *,
    diagnostic_provider: DiagnosticProvider | None,
) -> list[dict[str, Any]]:
    if diagnostic_provider is not None:
        result = diagnostic_provider(path, root)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        return list(result)  # type: ignore[arg-type]

    adapter = get_adapter_for_path(path)
    if adapter is None:
        return []
    client = LSPClient(adapter.config_for_root(root.as_uri()))
    await client.start()
    try:
        response = await client.diagnostics(path.as_uri())
    finally:
        await client.stop()
    if isinstance(response, dict):
        items = response.get("items", [])
        return list(items) if isinstance(items, list) else []
    return []


def _normalize_diagnostic(path: Path, item: dict[str, Any]) -> VerificationDiagnostic:
    start = ((item.get("range") or {}).get("start") or {})
    return VerificationDiagnostic(
        path=path,
        line=int(start.get("line", 0)) + 1,
        column=int(start.get("character", 0)) + 1,
        severity=_severity_name(item.get("severity")),
        message=str(item.get("message", "diagnostic")),
    )


def _severity_name(value: Any) -> str:
    return {
        1: "error",
        2: "warning",
        3: "info",
        4: "hint",
    }.get(value, "warning")
