"""JavaScript Language Server Protocol adapter."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from autocode.layer2.lsp_client import LSPServerConfig
from autocode.layer2.lsp_servers import LSPAdapter


class TypeScriptLanguageServerAdapter(LSPAdapter):
    """Shared adapter substrate for `typescript-language-server`."""

    command = ("typescript-language-server", "--stdio")
    config_file_names = ("tsconfig.json", "jsconfig.json")

    def config_for_root(self, root_uri: str) -> LSPServerConfig:
        root = _path_from_file_uri(root_uri)
        options = {
            "config_files": [name for name in self.config_file_names if (root / name).exists()],
            "project_local_symbols_only": True,
        }
        options.update(self._extra_autocode_options())
        return LSPServerConfig(
            language_id=self.language_id,
            command=self.server_command,
            root_uri=root_uri,
            initialization_options={"autocode": options},
        )

    def doctor_check(self) -> dict[str, object]:
        command = self.server_command[0] if self.server_command else ""
        server_path = shutil.which(command) if command else None
        peer_path = shutil.which("typescript")
        return {
            "language": self.language_id,
            "available": server_path is not None and peer_path is not None,
            "command": command,
            "path": server_path,
            "peer_dependency": "typescript",
            "peer_available": peer_path is not None,
            "peer_path": peer_path,
        }

    def _extra_autocode_options(self) -> dict[str, object]:
        return {}


class JavaScriptLSPAdapter(TypeScriptLanguageServerAdapter):
    """Adapter for JavaScript files through `typescript-language-server`."""

    language_id = "javascript"
    extensions = (".js", ".jsx", ".mjs")
    config_file_names = ("jsconfig.json", "tsconfig.json")


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path))
