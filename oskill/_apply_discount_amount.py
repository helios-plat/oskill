"""oskill.apply_discount_amount — 把一笔固定金额折扣按行占比分摊。

纯内存算法：largest-remainder 分摊法，保证各行分摊之和恰好等于实际生效
折扣额（不会因取整产生偏差），且总折扣不超过参与行的小计之和。
"""

from __future__ import annotations


def apply_discount_amount(items: list[dict], *, amount: int) -> dict:
    """按 ``line_total_cents`` 占比把 ``amount`` 分摊到各行。

    Args:
        items: 适用本折扣的购物车行（通常是 evaluate_discount_conditions 的
            输出），每项须含 ``id`` 与 ``line_total_cents``。
        amount: 折扣金额（分），非负。超过参与行小计之和时按小计之和封顶
            （不会把折扣打成负数总价）。

    Returns:
        ``{"allocations": {item_id: discount_cents, ...}, "total_discount_cents": int}``。
        空 items 或 amount<=0 时返回空分摊。
    """
    if amount < 0:
        raise ValueError("apply_discount_amount: amount must be non-negative")

    total_line = sum(item.get("line_total_cents", 0) for item in items)
    if not items or total_line <= 0 or amount == 0:
        return {"allocations": {}, "total_discount_cents": 0}

    capped = min(amount, total_line)

    shares = []
    for item in items:
        line_total = item.get("line_total_cents", 0)
        raw = capped * line_total / total_line
        shares.append([item["id"], int(raw), raw - int(raw)])

    allocated = sum(s[1] for s in shares)
    remainder = capped - allocated
    # Largest-remainder method: hand out leftover cents to the biggest fractional shares.
    for s in sorted(shares, key=lambda s: s[2], reverse=True)[:remainder]:
        s[1] += 1

    allocations = {item_id: cents for item_id, cents, _ in shares}
    return {"allocations": allocations, "total_discount_cents": sum(allocations.values())}
