"""oskill.apply_discount_percentage — 按百分比给每行打折。"""

from __future__ import annotations


def apply_discount_percentage(items: list[dict], *, percent: float) -> dict:
    """每行独立按 ``percent`` 打折（四舍五入到分），互不依赖其他行。

    Args:
        items: 适用本折扣的购物车行，每项须含 ``id`` 与 ``line_total_cents``。
        percent: 折扣百分比，``0 <= percent <= 100``。

    Returns:
        ``{"allocations": {item_id: discount_cents, ...}, "total_discount_cents": int}``。
    """
    if percent < 0 or percent > 100:
        raise ValueError("apply_discount_percentage: percent must be within [0, 100]")

    allocations = {}
    for item in items:
        line_total = item.get("line_total_cents", 0)
        allocations[item["id"]] = round(line_total * percent / 100)

    return {"allocations": allocations, "total_discount_cents": sum(allocations.values())}
