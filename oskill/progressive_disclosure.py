"""Compatibility alias — progressive context disclosure 已并入 oskill.context_compact.

WAVE H 的渐进式上下文披露 (rank_context_items / select_context_window /
compact_context / expand_item / ContextItem / LAYER_ORDER) 是 existing context
engineering 元素的内部扩展, canonical 实现位于 oskill.context_compact。

本模块仅为跨库 import 路径兼容而保留 (re-export, 无独立实现, 不新增能力)。
新代码请直接从 oskill.context_compact 导入。
"""

from __future__ import annotations

from oskill.context_compact import (
    LAYER_ORDER,
    ContextItem,
    compact_context,
    expand_item,
    rank_context_items,
    select_context_window,
)

__all__ = [
    "ContextItem",
    "rank_context_items",
    "select_context_window",
    "compact_context",
    "expand_item",
    "LAYER_ORDER",
]
