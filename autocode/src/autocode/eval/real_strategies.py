"""Real context packing strategies using actual L1/L2 tools.

Unlike the simulated strategies in context_packer.py, these search
the actual repo filesystem. Gold labels are used ONLY for scoring,
never as the candidate pool.
"""

from __future__ import annotations

import re
from pathlib import Path

from autocode.eval.harness import ContextStrategy, CuratedContext, EvalScenario


def _find_python_files(root: Path, max_files: int = 200) -> list[Path]:
    """Find all Python files under root."""
    files: list[Path] = []
    for f in root.rglob("*.py"):
        if ".venv" in f.parts or "__pycache__" in f.parts:
            continue
        files.append(f)
        if len(files) >= max_files:
            break
    return files


def _extract_symbols(filepath: Path) -> list[str]:
    """Extract def/class symbols from a Python file (L1 simulation)."""
    symbols: list[str] = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "async def ")):
                name = stripped.split("(")[0].split(":")[0]
                name = name.replace("def ", "").replace("class ", "").replace("async ", "")
                symbols.append(name.strip())
    except Exception:
        pass
    return symbols


def _bm25_score(query_words: set[str], doc_words: set[str]) -> float:
    """Simple BM25-like relevance score."""
    if not query_words or not doc_words:
        return 0.0
    overlap = query_words & doc_words
    return len(overlap) / max(len(query_words), 1)


def create_l1_real_strategy(repo_root: Path) -> ContextStrategy:
    """Real L1 strategy: tree-sitter symbol matching against repo files.

    Searches all Python files for symbols mentioned in the task description.
    """
    def curate(scenario: EvalScenario) -> CuratedContext:
        # Extract keywords from description ONLY — no gold labels
        # Gold labels are used ONLY in the scorer, never here
        desc_words = set(
            w.lower() for w in re.findall(r'\w+', scenario.input_description)
            if len(w) > 2
        )
        search_terms = desc_words

        files: list[str] = []
        symbols: list[str] = []
        token_count = 0

        for pyfile in _find_python_files(repo_root):
            file_symbols = _extract_symbols(pyfile)
            sym_set = set(s.lower() for s in file_symbols)
            if sym_set & search_terms:
                rel_path = str(pyfile.relative_to(repo_root))
                files.append(rel_path)
                symbols.extend(
                    s for s in file_symbols if s.lower() in search_terms
                )
                token_count += len(file_symbols) * 20  # ~20 tokens per symbol

        return CuratedContext(
            files=files[:15],
            symbols=symbols[:30],
            token_count=token_count,
        )

    return ContextStrategy(name="real_l1", curate=curate)


def create_l2_real_strategy(repo_root: Path) -> ContextStrategy:
    """Real L2 strategy: BM25 keyword search against repo files.

    Searches file content for terms from the task description.
    """
    def curate(scenario: EvalScenario) -> CuratedContext:
        desc_words = set(
            w.lower() for w in re.findall(r'\w+', scenario.input_description)
            if len(w) > 3
        )

        scored_files: list[tuple[float, str]] = []

        for pyfile in _find_python_files(repo_root):
            try:
                content = pyfile.read_text(encoding="utf-8", errors="ignore")
                doc_words = set(
                    w.lower() for w in re.findall(r'\w+', content)
                )
                score = _bm25_score(desc_words, doc_words)
                if score > 0.1:
                    rel_path = str(pyfile.relative_to(repo_root))
                    scored_files.append((score, rel_path))
            except Exception:
                continue

        # Sort by score descending
        scored_files.sort(reverse=True)
        files = [f for _, f in scored_files[:15]]
        token_count = sum(500 for _ in files)  # ~500 tokens per file

        return CuratedContext(
            files=files,
            symbols=[],
            token_count=token_count,
        )

    return ContextStrategy(name="real_l2", curate=curate)


def create_l1_l2_real_strategy(repo_root: Path) -> ContextStrategy:
    """Real L1+L2 combined strategy."""
    l1 = create_l1_real_strategy(repo_root)
    l2 = create_l2_real_strategy(repo_root)

    def curate(scenario: EvalScenario) -> CuratedContext:
        r1 = l1.curate(scenario)
        r2 = l2.curate(scenario)

        seen: set[str] = set()
        files: list[str] = []
        for f in r1.files + r2.files:
            if f not in seen:
                files.append(f)
                seen.add(f)

        return CuratedContext(
            files=files[:20],
            symbols=list(set(r1.symbols)),
            token_count=r1.token_count + r2.token_count,
        )

    return ContextStrategy(name="real_l1_l2", curate=curate)
