"""oskill.resolve_order_payment_status — 由多笔支付记录推导订单整体支付状态。

SPEC 未给出精确状态机,以下优先级顺序是本次自由裁量设计(向 Medusa 的
payment_status 语义靠拢),按代码顺序自上而下匹配:
1. 任一笔 requires_action -> "requires_action"(需要额外操作,如 3DS)。
2. 全部笔都是 canceled/failed -> 有 canceled 则 "canceled",否则 "not_paid"。
3. 全部笔都是 refunded -> "refunded"。
4. 同时存在"退款类"(refunded/partially_refunded)与"有效扣款类"
   (authorized/captured) -> "partially_refunded"。
5. 仅存在退款类(且不满足 3,即并非全部退款——理论上不会走到这支,兜底) -> "refunded"。
6. 存在 captured -> "captured"。
7. 存在 authorized(未 captured) -> "awaiting"。
8. 其余(如混合 failed/canceled 但无有效扣款) -> "not_paid"。
"""

from __future__ import annotations

_NOT_PAID_TERMINAL = {"canceled", "failed"}
_REFUND_LIKE = {"refunded", "partially_refunded"}
_ACTIVE_PAYMENT = {"authorized", "captured"}


def resolve_order_payment_status(payments: list) -> str:
    """推导订单整体支付状态。

    Args:
        payments: 支付记录列表,每项须含 ``status``,取值范围:
            ``requires_action`` / ``authorized`` / ``captured`` /
            ``partially_refunded`` / ``refunded`` / ``canceled`` / ``failed``。

    Returns:
        ``not_paid`` / ``requires_action`` / ``awaiting`` / ``captured`` /
        ``partially_refunded`` / ``refunded`` / ``canceled`` 之一。
    """
    if not payments:
        return "not_paid"

    statuses = {p["status"] for p in payments}

    if "requires_action" in statuses:
        return "requires_action"

    if statuses <= _NOT_PAID_TERMINAL:
        return "canceled" if "canceled" in statuses else "not_paid"

    if statuses == {"refunded"}:
        return "refunded"

    has_refund = bool(statuses & _REFUND_LIKE)
    has_active = bool(statuses & _ACTIVE_PAYMENT)
    if has_refund and has_active:
        return "partially_refunded"
    if has_refund:
        return "refunded"

    if "captured" in statuses:
        return "captured"
    if "authorized" in statuses:
        return "awaiting"

    return "not_paid"
