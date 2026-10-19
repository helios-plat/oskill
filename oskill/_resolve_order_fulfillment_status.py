"""oskill.resolve_order_fulfillment_status — 由多笔履约记录推导订单整体履约状态。

按 Medusa fulfillment_status 语义建模三级递进关系:
delivered ⊂ shipped ⊂ fulfilled(已发货必然已履约拣货,已送达必然已发货)。
"""

from __future__ import annotations

_SHIPPED_OR_BEYOND = {"shipped", "delivered"}


def resolve_order_fulfillment_status(fulfillments: list, *, total_qty: int) -> str:
    """推导订单整体履约状态。

    Args:
        fulfillments: 履约记录列表,每项须含 ``status``
            (``fulfilled`` / ``shipped`` / ``delivered`` / ``canceled``) 与 ``qty``。
        total_qty: 订单总需求量(全部行项目数量之和)。

    Returns:
        ``not_fulfilled`` / ``canceled`` / ``partially_fulfilled`` / ``fulfilled`` /
        ``partially_shipped`` / ``shipped`` / ``partially_delivered`` / ``delivered``。
    """
    if not fulfillments:
        return "not_fulfilled"

    statuses = {f["status"] for f in fulfillments}
    if statuses == {"canceled"}:
        return "canceled"

    fulfilled_qty = sum(f["qty"] for f in fulfillments if f["status"] != "canceled")
    shipped_qty = sum(f["qty"] for f in fulfillments if f["status"] in _SHIPPED_OR_BEYOND)
    delivered_qty = sum(f["qty"] for f in fulfillments if f["status"] == "delivered")

    if delivered_qty >= total_qty and total_qty > 0:
        return "delivered"
    if delivered_qty > 0:
        return "partially_delivered"
    if shipped_qty >= total_qty and total_qty > 0:
        return "shipped"
    if shipped_qty > 0:
        return "partially_shipped"
    if fulfilled_qty >= total_qty and total_qty > 0:
        return "fulfilled"
    if fulfilled_qty > 0:
        return "partially_fulfilled"

    return "not_fulfilled"
