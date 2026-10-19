"""oskill.workspace_rag — AST-indexed codebase semantic search skill.

3O layer: oskill (composite skill over oprim ast/vector/cosine atoms).
Composes:
  - oprim._ast_chunk.ast_chunk_python   (function/class-level chunking)
  - oprim._vector_encode.vector_encode  (embedding via ProviderRegistry)
  - oprim._distance.cosine_similarity_batch (batch KNN retrieval)
  - obase.rag_index_store               (persistent index restore)

Self-healing incremental indexing: file adds/modifies/deletes are detected
on search and re-indexed automatically. The host registers an embedding
provider with obase.ProviderRegistry; falls back to a deterministic stub.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from obase.rag_index_store import RAGIndexStore
from oprim._ast_chunk import ast_chunk_python, code_tokens
from oprim._distance import cosine_similarity_batch
from oprim._vector_encode import vector_encode

_log = logging.getLogger(__name__)

# 检索结果上下文行数(返回给大模型时附带)
_CONTEXT_LINES = 8
# 每个文件最多 chunk 数(巨型文件保护)
_MAX_CHUNKS_PER_FILE = 200


class WorkspaceRAGSkill:
    """Codebase semantic search engine: AST chunks -> vectors -> KNN."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        index_store: RAGIndexStore | None = None,
        persist_index: bool = True,
        restore_on_start: bool = True,
    ):
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self._index_store = index_store or RAGIndexStore()
        self._persist_index = persist_index
        # chunk_id -> chunk(含 content/metadata)
        self._chunks: dict[str, dict[str, Any]] = {}
        # chunk_id -> 向量
        self._vectors: dict[str, np.ndarray] = {}
        # 相对路径 -> mtime(增量索引)
        self._file_mtimes: dict[str, float] = {}

        if restore_on_start:
            chunks, mtimes = self._index_store.load()
            if chunks:
                self._chunks = dict(chunks)
                self._file_mtimes = dict(mtimes)
                for cid, chunk in self._chunks.items():
                    self._vectors[cid] = self._embed_chunk(chunk)
                _log.info("workspace_rag: restored %d chunks from index store", len(chunks))

        _log.info("workspace_rag: engine ready at %s", self.workspace_root)
        self.reindex_workspace()

    # ── 索引 ─────────────────────────────────────────────────────────
    def _python_files(self) -> list[Path]:
        excluded = {
            "__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache",
            ".pytest_cache", ".ruff_cache", "dist", "build", "site",
        }
        files = []
        for p in sorted(self.workspace_root.rglob("*.py")):
            if any(part in excluded for part in p.parts):
                continue
            files.append(p)
        return files

    def _embed_chunk(self, chunk: dict) -> np.ndarray:
        text = " ".join(code_tokens(chunk["content"]))
        return vector_encode(texts=[text])[0]

    def reindex_workspace(self, force: bool = False) -> str:
        """Full/incremental index update: mtime-changed files re-chunked."""
        new_mtimes: dict[str, float] = {}
        for filepath in self._python_files():
            try:
                mtime = filepath.stat().st_mtime
            except OSError:
                continue
            rel = str(filepath)
            new_mtimes[rel] = mtime
            if not force and self._file_mtimes.get(rel) == mtime and rel in self._chunks:
                continue  # unchanged — incremental skip
            for cid in [c for c in self._chunks if c.startswith(rel + ":")]:
                self._chunks.pop(cid, None)
                self._vectors.pop(cid, None)
            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for chunk in ast_chunk_python(
                source=source, filepath=rel, max_chunks=_MAX_CHUNKS_PER_FILE
            ):
                self._chunks[chunk["chunk_id"]] = chunk
                self._vectors[chunk["chunk_id"]] = self._embed_chunk(chunk)

        # 清理已删除文件的索引
        for rel in list(self._file_mtimes):
            if rel not in new_mtimes:
                for cid in [c for c in self._chunks if c.startswith(rel + ":")]:
                    self._chunks.pop(cid, None)
                    self._vectors.pop(cid, None)

        self._file_mtimes = new_mtimes
        if self._persist_index:
            self._index_store.save(self._chunks, self._file_mtimes)
        _log.info(
            "workspace_rag: index updated — %d chunks, %d files",
            len(self._chunks),
            len(new_mtimes),
        )
        return f"✅ 工作区索引更新完毕, 已将 {len(self._chunks)} 个函数/类结构映射为向量嵌入。"

    def _ensure_fresh(self) -> None:
        """Self-healing: add/modify/delete detected on next search."""
        current = {str(p) for p in self._python_files()}
        if set(self._file_mtimes) != current:
            self.reindex_workspace()
            return
        stale = False
        for filepath in self._python_files():
            try:
                mtime = filepath.stat().st_mtime
            except OSError:
                continue
            rel = str(filepath)
            if self._file_mtimes.get(rel) != mtime:
                stale = True
                break
        if stale:
            self.reindex_workspace()

    # ── 语义检索 ─────────────────────────────────────────────────────
    def search_context(self, query: str, top_k: int = 3) -> str:
        """Semantic KNN search over the codebase; returns ranked code blocks."""
        self._ensure_fresh()
        _log.info("workspace_rag: semantic search '%s'", query)

        if not self._chunks:
            return "(索引为空, 工作区没有可检索的 Python 文件)"

        query_vec = vector_encode(texts=[" ".join(code_tokens(query))])[0]
        matrix = np.vstack(list(self._vectors.values()))
        ids = list(self._vectors.keys())
        scores, indices = cosine_similarity_batch(query_vec[None, :], matrix, top_k=top_k)
        if scores.ndim == 2:
            scores, indices = scores[0], indices[0]

        lines = []
        for rank, (score, idx) in enumerate(zip(scores, indices, strict=False), start=1):
            cid = ids[int(idx)]
            chunk = self._chunks[cid]
            meta = chunk["metadata"]
            lines.append(
                f"[检索结果 {rank}] 文件: `{meta['file']}` "
                f"({meta['type']} {meta.get('name', '')} @ "
                f"L{meta['start_line']}-{meta['end_line']}, 匹配度: {float(score):.2f})"
            )
            lines.append("```python")
            lines.append(self._with_context(chunk))
            lines.append("```")
        return "\n".join(lines)

    def _with_context(self, chunk: dict) -> str:
        """Attach surrounding source lines to help the LLM locate edits."""
        meta = chunk["metadata"]
        try:
            source_lines = Path(meta["file"]).read_text(encoding="utf-8").splitlines()
        except OSError:
            return chunk["content"]
        start = max(0, meta["start_line"] - 1)
        end = min(len(source_lines), meta["end_line"] + _CONTEXT_LINES)
        return "\n".join(source_lines[start:end])

    # ── 元信息 ───────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        return {
            "workspace_root": str(self.workspace_root),
            "chunks": len(self._chunks),
            "files": len(self._file_mtimes),
            "types": {
                t: sum(1 for c in self._chunks.values() if c["metadata"]["type"] == t)
                for t in ("function", "class")
            },
        }
