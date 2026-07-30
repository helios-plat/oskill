"""oskill.calculate_inventory_availability — 由库存与已预留量推导可售量。"""

from __future__ import annotations


def calculate_inventory_availability(stock: int, *, reserved: int) -> int:
    """可售量 = 库存 - 已预留,下限为 0(不返回负数)。

    Args:
        stock: 当前库存量(``inventory_batch.stock_qty``),非负。
        reserved: 已预留量(``inventory_batch.reserved_qty``),非负。

    Returns:
        ``max(0, stock - reserved)``。允许 ``reserved > stock`` 这种瞬时超卖态
        (调用方自行决定是否视为异常),此函数只负责推导,不拒绝。

    Raises:
        ValueError: stock 或 reserved 为负。
    """
    if stock < 0:
        raise ValueError("calculate_inventory_availability: stock must be non-negative")
    if reserved < 0:
        raise ValueError("calculate_inventory_availability: reserved must be non-negative")

    return max(0, stock - reserved)
