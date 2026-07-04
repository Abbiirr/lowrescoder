"""TypeScript Language Server Protocol adapter."""

from __future__ import annotations

from autocode.layer2.lsp_servers.javascript import TypeScriptLanguageServerAdapter


class TypeScriptLSPAdapter(TypeScriptLanguageServerAdapter):
    """Adapter for TypeScript files through `typescript-language-server`."""

    language_id = "typescript"
    extensions = (".ts", ".tsx", ".d.ts")
    config_file_names = ("tsconfig.json", "jsconfig.json")

    def _extra_autocode_options(self) -> dict[str, object]:
        return {"typescript_type_diagnostics": True}
