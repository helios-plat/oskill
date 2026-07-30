"""oskill.verify_stock_threshold — 校验扣减 qty 后是否仍满足最低安全库存。"""

from __future__ import annotations


def verify_stock_threshold(qty: int, *, available: int, limit: int) -> bool:
    """判断从 `available` 扣减 `qty` 后是否仍 >= 安全库存下限 `limit`。

    典型用途:VIP/预售场景要求扣减后仓位至少保留 `limit` 件安全库存,
    而不是简单判断 `qty <= available`。

    Args:
        qty: 拟扣减的数量,非负。
        available: 当前可售量(如 `calculate_inventory_availability` 的输出)。
        limit: 允许扣减后剩余的最低库存下限(通常为 0 或正数)。

    Returns:
        ``available - qty >= limit``。

    Raises:
        ValueError: qty 为负。
    """
    if qty < 0:
        raise ValueError("verify_stock_threshold: qty must be non-negative")

    return available - qty >= limit
