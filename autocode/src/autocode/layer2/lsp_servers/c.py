"""C Language Server Protocol adapter."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from autocode.layer2.lsp_client import LSPServerConfig
from autocode.layer2.lsp_servers import LSPAdapter


class CLSPAdapter(LSPAdapter):
    """Adapter for C files through `clangd`."""

    language_id = "c"
    extensions = (".c", ".h")
    command = ("clangd",)

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        root = _path_from_file_uri(root_uri)
        config_files = ["compile_commands.json"] if (root / "compile_commands.json").exists() else []
        command = self.server_command
        if command and command[0] == "clangd" and config_files:
            command = (*command, "--compile-commands-dir", str(root))
        return LSPServerConfig(
            language_id=self.language_id,
            command=command,
            root_uri=root_uri,
            initialization_options={
                "autocode": {
                    "config_files": config_files,
                    "project_local_symbols_only": True,
                }
            },
        )

    def doctor_check(self) -> dict[str, object]:
        command = self.server_command[0] if self.server_command else ""
        path = shutil.which(command) if command else None
        return {
            "language": self.language_id,
            "available": path is not None,
            "command": command,
            "path": path,
        }


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path))
