"""oskill.rag_pipeline — RAG 数据源管线 (Dify knowledge 机制 3O 内化)。

知识库文档处理管线: 加载 (datasource) → 清洗 (cleaner) → 切分 (chunking)
→ 索引 (embedding 注入) → 检索 (rrf_retrieval 组合):
  * **load_document** — 文件/文本/URL 加载;
  * **clean_document** — 确定性清洗 (空行折叠/重复段落/噪声标记);
  * **chunk_text** — 确定性切分 (max_chars + overlap, 段落边界优先);
  * **RagIndex** — chunk 注册 + 向量注入 + 检索 (BM25 或注入向量)。
零 veya 反向依赖: 纯文本处理 + 注入。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EmbedFn = Callable[[str], list[float]]
"""文本嵌入: (text) → 向量 (注入)。"""


@dataclass(frozen=True)
class Chunk:
    """一个文档切片。"""

    id: str
    text: str
    source: str = ""
    offset: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text[:200],
            "source": self.source,
            "offset": self.offset,
        }


# ── 加载 ─────────────────────────────────────────────────────────────


def load_document(source: str | Path, *, encoding: str = "utf-8") -> str:
    """加载文档: 文件路径 / 文本 / URL (http 拉取)。"""
    if isinstance(source, Path):
        return source.read_text(encoding=encoding)
    text = str(source)
    if "\n" not in text and Path(text).exists():
        return Path(text).read_text(encoding=encoding)
    if text.startswith(("http://", "https://")):
        import urllib.request

        with urllib.request.urlopen(text, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    return text


# ── 清洗 ─────────────────────────────────────────────────────────────

_DEFAULT_NOISE = re.compile(
    r"^(?:---+|===+|~~~+|\*\*\*+|\*\*\* )\s*$|"
    r"^\[\d+\]$|"  # 孤立引用编号
    r"^\!\[.*\]\(.*\)\s*$",  # 裸图语法行
    re.MULTILINE,
)


def clean_document(text: str, *, fold_blank_lines: bool = True) -> str:
    """确定性清洗: 空行折叠/噪声标记/重复段落去重。

    Args:
        text: 原始文档。
        fold_blank_lines: 连续空行折叠为单个。

    Returns:
        清洗后文本。
    """
    text = _DEFAULT_NOISE.sub("", text)
    lines: list[str] = []
    seen_paragraphs: set[str] = set()
    prev_blank = True
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if not prev_blank and fold_blank_lines:
                lines.append("")
            prev_blank = True
            continue
        prev_blank = False
        # 重复段落去重 (长段落)
        if len(line) > 40 and line in seen_paragraphs:
            continue
        seen_paragraphs.add(line)
        lines.append(line)
    cleaned = "\n".join(lines)
    return cleaned.strip()


# ── 切分 ─────────────────────────────────────────────────────────────


def chunk_text(
    text: str,
    *,
    max_chars: int = 800,
    overlap: int = 100,
) -> list[Chunk]:
    """确定性切分: 段落边界优先, 超长按字符切, 带 overlap。

    Args:
        text: 清洗后文本。
        max_chars: 块最大字符。
        overlap: 相邻块重叠字符。

    Returns:
        Chunk 列表。

    Example:
        >>> len(chunk_text("a" * 2000, max_chars=800, overlap=0)) >= 3
        True
    """
    chunks: list[Chunk] = []
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    current = ""
    current_start = 0
    offset = 0
    idx = 0
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue
        if current:
            chunks.append(Chunk(f"chunk_{idx}", current.strip(), offset=current_start))
            idx += 1
            # overlap: 保留当前尾部 overlap 字符
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
            current_start = offset - len(tail)
        else:
            # 单段超长: 按字符切
            for start in range(0, len(paragraph), max_chars - overlap):
                chunk_text_part = paragraph[start : start + max_chars]
                chunks.append(Chunk(f"chunk_{idx}", chunk_text_part.strip(), offset=offset + start))
                idx += 1
            current = ""
        offset = 0
    if current:
        chunks.append(Chunk(f"chunk_{idx}", current.strip(), offset=current_start))
    return chunks


# ── 索引 ─────────────────────────────────────────────────────────────


class RagIndex:
    """检索索引: chunk 注册 + BM25 检索 (向量注入可选)。"""

    def __init__(self) -> None:
        self.chunks: dict[str, Chunk] = {}
        self.embeddings: dict[str, list[float]] = {}

    def add_chunks(self, chunks: list[Chunk], *, embed_fn: EmbedFn | None = None) -> None:
        """注册 chunk (可选嵌入)。"""
        for chunk in chunks:
            self.chunks[chunk.id] = chunk
            if embed_fn is not None:
                self.embeddings[chunk.id] = embed_fn(chunk.text)

    def bm25_retrieve(self, query: str, *, top_k: int = 3) -> list[Chunk]:
        """BM25 检索 (复用 rrf_retrieval)。"""
        from oskill.rrf_retrieval import bm25_score, tokenize

        query_tokens = tokenize(query)
        doc_tokens = [tokenize(c.text) for c in self.chunks.values()]
        df: dict[str, int] = {}
        for tokens in doc_tokens:
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1
        n_docs = max(len(doc_tokens), 1)
        avg_dl = sum(len(t) for t in doc_tokens) / n_docs
        scored = [
            (bm25_score(query_tokens, tokens, df=df, n_docs=n_docs, avg_dl=avg_dl), chunk)
            for chunk, tokens in zip(self.chunks.values(), doc_tokens)
        ]
        scored.sort(key=lambda x: -x[0])
        return [chunk for score, chunk in scored[:top_k] if score > 0]

    def vector_retrieve(self, query: str, embed_fn: EmbedFn, *, top_k: int = 3) -> list[Chunk]:
        """向量检索 (余弦, 注入嵌入函数)。"""
        import math

        query_vec = embed_fn(query)

        def cosine(a, b):  # noqa: ANN001
            if not a or not b:
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        scored = [
            (cosine(query_vec, vec), chunk)
            for chunk_id, vec in self.embeddings.items()
            if (chunk := self.chunks.get(chunk_id)) is not None
        ]
        scored.sort(key=lambda x: -x[0])
        return [chunk for score, chunk in scored[:top_k]]

    def stats(self) -> dict[str, Any]:
        return {"chunks": len(self.chunks), "embedded": len(self.embeddings)}


def build_rag_pipeline(
    sources: list[str | Path],
    *,
    max_chars: int = 800,
    overlap: int = 100,
    embed_fn: EmbedFn | None = None,
) -> tuple[list[Chunk], RagIndex]:
    """一站式: 加载 → 清洗 → 切分 → 索引。

    Returns:
        (chunks, index)。
    """
    index = RagIndex()
    all_chunks: list[Chunk] = []
    for source in sources:
        text = load_document(source)
        cleaned = clean_document(text)
        chunks = chunk_text(cleaned, max_chars=max_chars, overlap=overlap)
        all_chunks.extend(chunks)
    index.add_chunks(all_chunks, embed_fn=embed_fn)
    return all_chunks, index


__all__ = [
    "Chunk",
    "RagIndex",
    "build_rag_pipeline",
    "chunk_text",
    "clean_document",
    "load_document",
]
