"""LanceDB-backed code index with incremental updates.

Indexes code chunks from project files, tracks file hashes for
incremental re-indexing, respects gitignore, and caps at max_files.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import time
from pathlib import Path

from autocode.config import Layer2Config
from autocode.core.types import CodeChunk
from autocode.layer2.chunker import ASTChunker
from autocode.layer2.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)


def _load_gitignore_patterns(project_root: Path) -> list[str]:
    """Load patterns from .gitignore if it exists."""
    gitignore = project_root / ".gitignore"
    patterns: list[str] = []
    if gitignore.exists():
        try:
            for line in gitignore.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except OSError:
            pass
    # Always ignore common non-code directories
    patterns.extend([
        ".git", "__pycache__", "*.pyc", ".venv", "venv",
        "node_modules", ".mypy_cache", ".ruff_cache", "*.egg-info",
        ".tox", "dist", "build",
    ])
    return patterns


def _should_ignore(path: Path, root: Path, patterns: list[str]) -> bool:
    """Check if a path matches any gitignore pattern."""
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return True

    for pattern in patterns:
        # Match against file name
        if fnmatch.fnmatch(path.name, pattern):
            return True
        # Match against relative path
        if fnmatch.fnmatch(rel, pattern):
            return True
        # Match directory patterns
        if pattern.endswith("/") and fnmatch.fnmatch(rel + "/", pattern):
            return True
        # Match any path component
        for part in Path(rel).parts:
            if fnmatch.fnmatch(part, pattern.rstrip("/")):
                return True
    return False


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except OSError:
        return ""
    return h.hexdigest()


class CodeIndex:
    """LanceDB-backed code index with incremental updates.

    Scans project files, chunks via ASTChunker, embeds via EmbeddingEngine,
    and stores in LanceDB for hybrid search.
    """

    def __init__(
        self,
        config: Layer2Config | None = None,
        chunker: ASTChunker | None = None,
        embeddings: EmbeddingEngine | None = None,
    ) -> None:
        self._config = config or Layer2Config()
        self._chunker = chunker or ASTChunker()
        self._embeddings = embeddings or EmbeddingEngine(
            model_name=self._config.embedding_model,
        )
        self._db: object | None = None
        self._table: object | None = None
        self._file_hashes: dict[str, str] = {}
        self._chunks: list[CodeChunk] = []

    @property
    def chunk_count(self) -> int:
        """Number of indexed chunks."""
        return len(self._chunks)

    @property
    def file_count(self) -> int:
        """Number of indexed files."""
        return len(self._file_hashes)

    def build(self, project_root: str | Path) -> dict[str, int]:
        """Build or update the code index for a project.

        Args:
            project_root: Path to the project root directory.

        Returns:
            Dict with stats: files_scanned, files_indexed, chunks_created, time_ms.
        """
        root = Path(project_root).resolve()
        start = time.monotonic()

        ignore_patterns = _load_gitignore_patterns(root)

        # Collect Python files (respecting gitignore and max_files)
        py_files: list[Path] = []
        for fpath in root.rglob("*.py"):
            if _should_ignore(fpath, root, ignore_patterns):
                continue
            py_files.append(fpath)
            if len(py_files) >= self._config.max_files:
                break

        files_scanned = len(py_files)

        # Determine which files need re-indexing
        new_hashes: dict[str, str] = {}
        files_to_index: list[Path] = []

        for fpath in py_files:
            key = str(fpath)
            h = _file_hash(fpath)
            new_hashes[key] = h
            if self._file_hashes.get(key) != h:
                files_to_index.append(fpath)

        # Remove chunks for deleted/changed files
        changed_files = {str(f) for f in files_to_index}
        deleted_files = set(self._file_hashes.keys()) - set(new_hashes.keys())
        remove_files = changed_files | deleted_files

        self._chunks = [c for c in self._chunks if c.file_path not in remove_files]

        # Chunk new/changed files
        new_chunks: list[CodeChunk] = []
        for fpath in files_to_index:
            try:
                chunks = self._chunker.chunk_file(fpath)
                new_chunks.extend(chunks)
            except Exception as e:
                logger.warning("Failed to chunk %s: %s", fpath, e)

        # Generate embeddings for new chunks
        if new_chunks and self._embeddings.available:
            texts = [c.content for c in new_chunks]
            embeddings = self._embeddings.embed(texts)
            for chunk, emb in zip(new_chunks, embeddings):
                chunk.embedding = emb

        self._chunks.extend(new_chunks)
        self._file_hashes = new_hashes

        # Try to persist to LanceDB
        self._persist_to_lancedb()

        elapsed_ms = int((time.monotonic() - start) * 1000)

        stats = {
            "files_scanned": files_scanned,
            "files_indexed": len(files_to_index),
            "chunks_created": len(new_chunks),
            "total_chunks": len(self._chunks),
            "time_ms": elapsed_ms,
        }
        logger.info("Index build: %s", stats)
        return stats

    def get_chunks(self) -> list[CodeChunk]:
        """Return all indexed chunks."""
        return list(self._chunks)

    def _persist_to_lancedb(self) -> None:
        """Persist chunks to LanceDB (best-effort)."""
        try:
            import lancedb  # type: ignore[import-untyped]

            db_path = Path(self._config.db_path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)

            db = lancedb.connect(str(db_path))

            records = []
            for chunk in self._chunks:
                record = {
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "language": chunk.language,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "scope_chain": "|".join(chunk.scope_chain),
                }
                if chunk.embedding:
                    record["vector"] = chunk.embedding
                records.append(record)

            if records:
                # Check if any records have embeddings
                has_vectors = any("vector" in r for r in records)
                if has_vectors:
                    db.create_table("code_chunks", data=records, mode="overwrite")
                    self._db = db
                    self._table = db.open_table("code_chunks")
                    logger.info("Persisted %d chunks to LanceDB", len(records))
                else:
                    logger.info("No embeddings available, skipping LanceDB persistence")

        except ImportError:
            logger.debug("LanceDB not installed, using in-memory index only")
        except Exception as e:
            logger.warning("Failed to persist to LanceDB: %s", e)
