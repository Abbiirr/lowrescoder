"""Kotlin Language Server Protocol adapter."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from autocode.layer2.lsp_client import LSPServerConfig
from autocode.layer2.lsp_servers import LSPAdapter


class KotlinLSPAdapter(LSPAdapter):
    """Adapter for Kotlin files through `kotlin-language-server`."""

    language_id = "kotlin"
    extensions = (".kt", ".kts")
    command = ("kotlin-language-server",)

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        root = _path_from_file_uri(root_uri)
        build_files = [
            name
            for name in ("build.gradle.kts", "build.gradle", "pom.xml")
            if (root / name).exists()
        ]
        return LSPServerConfig(
            language_id=self.language_id,
            command=self.server_command,
            root_uri=root_uri,
            initialization_options={
                "autocode": {
                    "build_files": build_files,
                    "project_local_symbols_only": True,
                }
            },
            request_timeout_s=30.0,
        )

    def doctor_check(self) -> dict[str, object]:
        command = self.server_command[0] if self.server_command else ""
        server_path = shutil.which(command) if command else None
        runtime_path = shutil.which("java")
        return {
            "language": self.language_id,
            "available": server_path is not None and runtime_path is not None,
            "command": command,
            "path": server_path,
            "runtime": "java",
            "runtime_available": runtime_path is not None,
            "runtime_path": runtime_path,
        }


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path))
