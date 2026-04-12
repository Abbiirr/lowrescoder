"""LSP-style code intelligence via Jedi (deep-research-report Phase B Item 3).

The deep-research report calls out LSP-backed navigation as the
**typed, structured alternative** to brittle regex/text-search
heuristics. Text grep misses semantics (false positives, can't resolve
imports, can't tell a call from a definition). An LSP-style engine
gives the agent:

- ``goto_definition(path, line, col)`` — resolve the symbol under a
  cursor position to its definition location (file + line + col).
- ``find_references(path, line, col)`` — every call site of the
  symbol under the cursor.
- ``get_type_hint(path, line, col)`` — the inferred type of the
  symbol as a short string.
- ``lsp_symbols(path)`` — a summary of top-level symbols in a file
  (functions, classes, imports).

The backend is `jedi <https://github.com/davidhalter/jedi>`_ — a pure
Python static-analysis engine that covers the Python case cheaply
without needing a persistent LSP server. This is the Phase 5 "Python
Semantics" plan from CLAUDE.md promoted into Phase B.

Contract:

- Every function returns a structured dataclass with an ``error``
  field. When Jedi is unavailable (import fails) the tool returns a
  clean "Jedi not installed" error rather than raising.
- All paths are treated as project-relative when ``project_root`` is
  set; absolute paths are used as-is otherwise.
- Line/column are 1-based in the API surface (common IDE convention)
  but converted to 0-based internally when talking to Jedi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


try:
    import jedi  # type: ignore

    _JEDI_OK = True
    _JEDI_ERR = ""
except Exception as exc:  # noqa: BLE001
    _JEDI_OK = False
    _JEDI_ERR = f"jedi import failed: {exc}"


@dataclass
class LspLocation:
    """A single result from goto_definition / find_references."""

    path: str
    line: int  # 1-based
    column: int  # 1-based
    name: str = ""
    context: str = ""  # the matched line of source code


@dataclass
class LspResult:
    """Structured wrapper for every LSP-style tool return value."""

    locations: list[LspLocation] = field(default_factory=list)
    type_hint: str = ""
    symbols: list[str] = field(default_factory=list)
    error: str = ""

    def to_text(self) -> str:
        if self.error:
            return f"lsp error: {self.error}"
        parts: list[str] = []
        if self.type_hint:
            parts.append(f"type: {self.type_hint}")
        if self.symbols:
            parts.append("symbols:")
            for name in self.symbols[:40]:
                parts.append(f"  {name}")
            if len(self.symbols) > 40:
                parts.append(f"  ... and {len(self.symbols) - 40} more")
        if self.locations:
            parts.append(f"locations ({len(self.locations)}):")
            for loc in self.locations[:40]:
                ctx = f"  {loc.context}" if loc.context else ""
                parts.append(
                    f"  {loc.path}:{loc.line}:{loc.column}  {loc.name}{ctx}"
                )
            if len(self.locations) > 40:
                parts.append(f"  ... and {len(self.locations) - 40} more")
        return "\n".join(parts) or "(no results)"


def _resolve(path: str, project_root: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    root = Path(project_root) if project_root else Path.cwd()
    return (root / p).resolve()


def _load_source(path: Path) -> tuple[str, str]:
    """Return (source, error). On success error == ''."""
    try:
        return path.read_text(encoding="utf-8"), ""
    except (OSError, UnicodeDecodeError) as exc:
        return "", f"cannot read {path}: {exc}"


def _make_script(
    path: str, project_root: str
) -> tuple[object, str]:
    """Build a Jedi Script for ``path``. Returns (script, error)."""
    if not _JEDI_OK:
        return None, _JEDI_ERR
    resolved = _resolve(path, project_root)
    if not resolved.exists():
        return None, f"file does not exist: {resolved}"
    source, err = _load_source(resolved)
    if err:
        return None, err
    try:
        project = jedi.Project(project_root) if project_root else None
        script = jedi.Script(code=source, path=str(resolved), project=project)
    except Exception as exc:  # noqa: BLE001
        return None, f"jedi.Script failed: {exc}"
    return script, ""


def goto_definition(
    path: str,
    line: int,
    column: int,
    *,
    project_root: str = "",
) -> LspResult:
    """Resolve the symbol at ``(line, column)`` in ``path`` to definitions.

    Line/column are 1-based on the API boundary (IDE convention).
    """
    script, err = _make_script(path, project_root)
    if err:
        return LspResult(error=err)
    try:
        defs = script.goto(line=line, column=max(0, column - 1))
    except Exception as exc:  # noqa: BLE001
        return LspResult(error=f"jedi.goto failed: {exc}")

    out = LspResult()
    for d in defs:
        if not getattr(d, "line", None):
            continue
        src_line = ""
        try:
            if d.module_path:
                # Pull the line context for readability
                all_src = Path(d.module_path).read_text(encoding="utf-8")
                lines = all_src.splitlines()
                if 0 < d.line <= len(lines):
                    src_line = lines[d.line - 1].strip()
        except Exception:  # noqa: BLE001
            pass
        out.locations.append(
            LspLocation(
                path=str(d.module_path) if d.module_path else path,
                line=int(d.line),
                column=int(d.column) + 1,
                name=d.name or "",
                context=src_line,
            )
        )
    return out


def find_references(
    path: str,
    line: int,
    column: int,
    *,
    project_root: str = "",
) -> LspResult:
    """Find every reference to the symbol at ``(line, column)``."""
    script, err = _make_script(path, project_root)
    if err:
        return LspResult(error=err)
    try:
        refs = script.get_references(line=line, column=max(0, column - 1))
    except Exception as exc:  # noqa: BLE001
        return LspResult(error=f"jedi.get_references failed: {exc}")

    out = LspResult()
    for r in refs:
        if not getattr(r, "line", None):
            continue
        out.locations.append(
            LspLocation(
                path=str(r.module_path) if r.module_path else path,
                line=int(r.line),
                column=int(r.column) + 1,
                name=r.name or "",
            )
        )
    return out


def get_type_hint(
    path: str,
    line: int,
    column: int,
    *,
    project_root: str = "",
) -> LspResult:
    """Return the inferred type of the symbol at ``(line, column)``."""
    script, err = _make_script(path, project_root)
    if err:
        return LspResult(error=err)
    try:
        inferred = script.infer(line=line, column=max(0, column - 1))
    except Exception as exc:  # noqa: BLE001
        return LspResult(error=f"jedi.infer failed: {exc}")

    out = LspResult()
    if inferred:
        first = inferred[0]
        # Prefer full_name / description — both are cheap to compute
        type_str = ""
        try:
            type_str = first.full_name or first.description or first.name or ""
        except Exception:  # noqa: BLE001
            type_str = first.name or ""
        out.type_hint = type_str
    return out


def list_symbols(path: str, *, project_root: str = "") -> LspResult:
    """List top-level defined symbols in ``path``."""
    script, err = _make_script(path, project_root)
    if err:
        return LspResult(error=err)
    try:
        names = script.get_names(all_scopes=False, definitions=True, references=False)
    except Exception as exc:  # noqa: BLE001
        return LspResult(error=f"jedi.get_names failed: {exc}")

    out = LspResult()
    for n in names:
        kind = getattr(n, "type", "") or ""
        out.symbols.append(f"{kind}  {n.name}  line {n.line}")
    return out


# --- Tool handler entry points (called from tools.py registry) ---


def _handle_lsp_goto_definition(
    path: str = "",
    line: int = 1,
    column: int = 1,
    project_root: str = "",
) -> str:
    if not path:
        return "lsp_goto_definition error: path is required"
    return goto_definition(
        path, line=line, column=column, project_root=project_root
    ).to_text()


def _handle_lsp_find_references(
    path: str = "",
    line: int = 1,
    column: int = 1,
    project_root: str = "",
) -> str:
    if not path:
        return "lsp_find_references error: path is required"
    return find_references(
        path, line=line, column=column, project_root=project_root
    ).to_text()


def _handle_lsp_get_type(
    path: str = "",
    line: int = 1,
    column: int = 1,
    project_root: str = "",
) -> str:
    if not path:
        return "lsp_get_type error: path is required"
    return get_type_hint(
        path, line=line, column=column, project_root=project_root
    ).to_text()


def _handle_lsp_symbols(path: str = "", project_root: str = "") -> str:
    if not path:
        return "lsp_symbols error: path is required"
    return list_symbols(path, project_root=project_root).to_text()
