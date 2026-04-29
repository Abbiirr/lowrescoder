"""Rust Language Server Protocol adapter."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from autocode.layer2.lsp_client import LSPServerConfig
from autocode.layer2.lsp_servers import LSPAdapter


class RustLSPAdapter(LSPAdapter):
    """Adapter for Rust files through `rust-analyzer`."""

    language_id = "rust"
    extensions = (".rs",)
    command = ("rust-analyzer",)

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        root = _path_from_file_uri(root_uri)
        config_files = ["Cargo.toml"] if (root / "Cargo.toml").exists() else []
        return LSPServerConfig(
            language_id=self.language_id,
            command=self.server_command,
            root_uri=root_uri,
            initialization_options={
                "autocode": {
                    "config_files": config_files,
                    "project_local_symbols_only": True,
                    "rust_clippy_diagnostics": True,
                }
            },
            request_timeout_s=30.0,
        )

    def doctor_check(self) -> dict[str, object]:
        command = self.server_command[0] if self.server_command else ""
        server_path = shutil.which(command) if command else None
        runtime_path = shutil.which("rustup")
        return {
            "language": self.language_id,
            "available": server_path is not None and runtime_path is not None,
            "command": command,
            "path": server_path,
            "runtime": "rustup",
            "runtime_available": runtime_path is not None,
            "runtime_path": runtime_path,
            "component": "rust-analyzer",
        }


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path))
