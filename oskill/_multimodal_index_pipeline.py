"""oskill.multimodal_index_pipeline — index multimodal items into a vector store."""

from __future__ import annotations

from typing import Any, Callable


def multimodal_index_pipeline(
    *,
    items: list[dict[str, Any]],
    embed_fn: Callable[[dict[str, Any]], Any] | None = None,
    store: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Embed and index multimodal items.

    items: list of {id, text?, image_path?, code?, metadata?}
    embed_fn: callable(item) -> vector (sync or async not supported; sync only)
    store: optional mutable list to append to.
    Returns list of indexed records {id, vector, metadata}.
    """
    if store is None:
        store = []
    indexed = []
    for it in items or []:
        vec = None
        if embed_fn is not None:
            try:
                vec = embed_fn(it)
            except Exception:
                vec = None
        if vec is None:
            # fallback zero vector
            vec = []
        rec = {"id": it.get("id"), "vector": vec, "metadata": {k: v for k, v in it.items() if k not in ("id",)}}
        store.append(rec)
        indexed.append(rec)
    return indexed
