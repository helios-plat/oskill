"""oskill.embedding_service — Embedding 服务 (Dify embedding 机制 3O 内化)。

embedding 提供者注册 + 缓存 + 批处理 (Dify embedding 服务机制层):
  * **EmbeddingProvider** — 声明 (id/维度/批大小/提供者);
  * **EmbeddingService** — 提供者注册/文本嵌入 (缓存复用)/批量嵌入;
  * 与 rag_pipeline.RagIndex 组合 (doc_extractors → embedding → 检索)。
零 veya 反向依赖: 嵌入函数注入 (openai/huggingface/local 由调用方提供)。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

EmbedFn = Callable[[str], list[float]]
"""单条文本嵌入: (text) → 向量。"""


@dataclass
class EmbeddingProvider:
    """一个 embedding 提供者。"""

    id: str
    embed: EmbedFn
    dimension: int = 0
    batch_size: int = 16

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "dimension": self.dimension, "batch_size": self.batch_size}


class EmbeddingService:
    """embedding 服务: 提供者注册 + 缓存 + 批处理。"""

    def __init__(self) -> None:
        self.providers: dict[str, EmbeddingProvider] = {}
        self._cache: dict[tuple[str, str], list[float]] = {}

    def register(self, provider: EmbeddingProvider) -> None:
        self.providers[provider.id] = provider

    def embed(self, text: str, *, provider_id: str | None = None) -> list[float]:
        """嵌入单条文本 (缓存复用)。"""
        provider = self._resolve(provider_id)
        key = (provider.id, text)
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)
        vector = provider.embed(text)
        self._cache[key] = vector
        return vector

    def embed_batch(self, texts: list[str], *, provider_id: str | None = None) -> list[list[float]]:
        """批量嵌入 (按 provider 批大小分批, 缓存复用)。"""
        provider = self._resolve(provider_id)
        results: list[list[float]] = []
        for i in range(0, len(texts), provider.batch_size):
            batch = texts[i : i + provider.batch_size]
            for text in batch:
                results.append(self.embed(text, provider_id=provider.id))
        return results

    def stats(self) -> dict[str, Any]:
        """缓存统计。"""
        return {
            "providers": list(self.providers),
            "cached_vectors": len(self._cache),
            "cache_bytes_approx": sum(len(v) * 8 for v in self._cache.values()),
        }

    def _resolve(self, provider_id: str | None) -> EmbeddingProvider:
        if provider_id is not None:
            if provider_id not in self.providers:
                raise ValueError(
                    f"provider not found: {provider_id!r}; "
                    f"registered: {list(self.providers)}")
            return self.providers[provider_id]
        if len(self.providers) == 1:
            return next(iter(self.providers.values()))
        raise ValueError(
            f"no provider specified; registered: {list(self.providers)}")


# ── 常见提供者工厂 (嵌入函数由调用方注入) ──────────────────────────


def openai_provider(
    api_key: str, *, model: str = "text-embedding-3-small", base_url: str | None = None
) -> EmbeddingProvider:
    """OpenAI-compatible embedding 提供者 (httpx 调用)。"""
    import urllib.request

    endpoint = (base_url or "https://api.openai.com/v1") + "/embeddings"

    def embed(text: str) -> list[float]:
        body = '{"model": "' + model + '", "input": ' + (
            model,
            __import__("json").dumps(text, ensure_ascii=False),
        )
        req = urllib.request.Request(
            endpoint,
            data=body.encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = __import__("json").loads(resp.read().decode("utf-8"))
        return data["data"][0]["embedding"]

    return EmbeddingProvider(id=f"openai:{model}", embed=embed)


__all__ = ["EmbeddingProvider", "EmbeddingService", "openai_provider"]
