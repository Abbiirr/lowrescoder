"""Language-server adapter registry."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Iterable, Sequence

from autocode.layer2.lsp_client import LSPClient, LSPServerConfig


class LSPAdapter:
    """Base class for per-language LSP adapters."""

    language_id: ClassVar[str] = ""
    extensions: ClassVar[tuple[str, ...]] = ()
    command: ClassVar[tuple[str, ...]] = ()

    def __init__(self, *, command: Sequence[str] | None = None) -> None:
        self._command_override = tuple(command) if command is not None else None

    @property
    def server_command(self) -> tuple[str, ...]:
        return self._command_override or self.command

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        return LSPServerConfig(
            language_id=self.language_id,
            command=self.server_command,
            root_uri=root_uri,
        )

    def create_client(self, root_uri: str) -> LSPClient:
        return LSPClient(self.config_for_root(root_uri))

    def doctor_check(self) -> dict[str, object]:
        """Return a non-spawning readiness record for this adapter."""
        import shutil

        executable = self.server_command[0] if self.server_command else ""
        path = shutil.which(executable) if executable else None
        return {
            "language": self.language_id,
            "available": path is not None,
            "command": executable,
            "path": path,
        }


def registered_adapters() -> list[LSPAdapter]:
    """Return built-in adapters. Language slices populate this list."""
    from autocode.layer2.lsp_servers.c import CLSPAdapter
    from autocode.layer2.lsp_servers.go import GoLSPAdapter
    from autocode.layer2.lsp_servers.javascript import JavaScriptLSPAdapter
    from autocode.layer2.lsp_servers.java import JavaLSPAdapter
    from autocode.layer2.lsp_servers.kotlin import KotlinLSPAdapter
    from autocode.layer2.lsp_servers.python import PythonLSPAdapter
    from autocode.layer2.lsp_servers.rust import RustLSPAdapter
    from autocode.layer2.lsp_servers.typescript import TypeScriptLSPAdapter

    return [
        JavaLSPAdapter(),
        JavaScriptLSPAdapter(),
        TypeScriptLSPAdapter(),
        CLSPAdapter(),
        KotlinLSPAdapter(),
        PythonLSPAdapter(),
        GoLSPAdapter(),
        RustLSPAdapter(),
    ]


def get_adapter_for_path(
    path: str | Path,
    *,
    adapters: Iterable[LSPAdapter] | None = None,
) -> LSPAdapter | None:
    """Resolve an adapter by file extension."""
    suffix = Path(path).suffix
    for adapter in adapters if adapters is not None else registered_adapters():
        if suffix in adapter.extensions:
            return adapter
    return None


def lsp_doctor_checks(
    *,
    adapters: Iterable[LSPAdapter] | None = None,
) -> list[dict[str, object]]:
    """Return non-spawning readiness checks for registered LSP servers."""
    checks: list[dict[str, object]] = []
    for adapter in adapters if adapters is not None else registered_adapters():
        checks.append(adapter.doctor_check())
    return checks
