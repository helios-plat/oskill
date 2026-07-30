"""oskill.stack_discount_allocations — 合并多张折扣各自的行级分摊。"""

from __future__ import annotations


def stack_discount_allocations(allocations: list[dict]) -> dict:
    """把多次 apply_discount_amount/apply_discount_percentage 的输出逐行累加。

    Args:
        allocations: 每项形如
            ``{"allocations": {item_id: cents, ...}, "total_discount_cents": int}``
            （通常来自多张同时生效的折扣）。

    Returns:
        ``{"allocations": {item_id: 累加 cents, ...}, "total_discount_cents": int}``。
        不做"不超过该行小计"的封顶——那需要行级小计信息，属于调用方
        （omodul.apply_discount_to_cart）在写回前的职责。
    """
    merged: dict[str, int] = {}
    for alloc in allocations:
        for item_id, cents in alloc.get("allocations", {}).items():
            merged[item_id] = merged.get(item_id, 0) + cents

    return {"allocations": merged, "total_discount_cents": sum(merged.values())}
