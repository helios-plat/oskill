"""oskill.compute_cart_subtotal — 购物车小计（分）。纯内存算法。"""

from __future__ import annotations


def compute_cart_subtotal(items: list[dict]) -> int:
    """Σ line_total_cents。

    Args:
        items: 每项须含 line_total_cents（由调用方按 unit_price_cents * quantity 算好，
            批次场景下 unit_price_cents 取自 inventory_batch.retail_price_cents）。

    Returns:
        小计金额（分）。
    """
    return sum(item.get("line_total_cents", 0) for item in items)
