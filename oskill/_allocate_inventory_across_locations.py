"""oskill.allocate_inventory_across_locations — 按仓位优先级贪心分摊需求量。

不做仓位排序决策(按距离/优先级排 stock_map 是调用方职责,本函数只按传入的
dict 迭代顺序贪心取货)。
"""

from __future__ import annotations


def allocate_inventory_across_locations(qty: int, *, stock_map: dict) -> dict:
    """按 `stock_map` 的迭代顺序,从每个仓位贪心取货直到凑够 `qty`。

    Args:
        qty: 需要分摊的总需求量,非负。
        stock_map: ``{location_id: available_qty}``,按调用方期望的优先级
            顺序传入(如已按距离/成本排序)。

    Returns:
        ``{"allocations": {location_id: qty_taken, ...}, "fully_allocated": bool,
        "unallocated_qty": int}``。``allocations`` 只含实际分配 >0 的仓位。

    Raises:
        ValueError: qty 为负。
    """
    if qty < 0:
        raise ValueError("allocate_inventory_across_locations: qty must be non-negative")

    allocations: dict[str, int] = {}
    remaining = qty
    for location_id, available in stock_map.items():
        if remaining <= 0:
            break
        if available <= 0:
            continue
        take = min(remaining, available)
        allocations[location_id] = take
        remaining -= take

    return {
        "allocations": allocations,
        "fully_allocated": remaining == 0,
        "unallocated_qty": remaining,
    }
