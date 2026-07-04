"""Python Language Server Protocol adapter."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from autocode.agent import lsp_tools
from autocode.layer2.lsp_client import LSPServerConfig
from autocode.layer2.lsp_servers import LSPAdapter


class PythonLSPAdapter(LSPAdapter):
    """Adapter for Python files through `pylsp`, with Jedi fallback retained."""

    language_id = "python"
    extensions = (".py", ".pyi")
    command = ("pylsp",)

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        root = _path_from_file_uri(root_uri)
        config_files = [
            name
            for name in ("pyproject.toml", "setup.cfg", "tox.ini")
            if (root / name).exists()
        ]
        return LSPServerConfig(
            language_id=self.language_id,
            command=self.server_command,
            root_uri=root_uri,
            initialization_options={
                "autocode": {
                    "config_files": config_files,
                    "project_local_symbols_only": True,
                    "jedi_fallback": True,
                    "preferred_server": "pylsp",
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
            "fallback": "jedi",
            "fallback_available": lsp_tools._JEDI_OK,
            "fallback_error": lsp_tools._JEDI_ERR,
        }


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path))
