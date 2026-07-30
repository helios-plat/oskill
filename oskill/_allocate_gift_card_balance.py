"""oskill.allocate_gift_card_balance — 礼品卡余额抵扣购物车应付金额。"""

from __future__ import annotations


def allocate_gift_card_balance(cart_total: int, *, card_balance: int) -> dict:
    """礼品卡最多抵扣到应付金额为 0，不会倒找钱、不会透支卡余额。

    Args:
        cart_total: 抵扣前的应付金额（分），非负。
        card_balance: 礼品卡当前余额（分），非负。

    Returns:
        ``{"applied_cents": int, "remaining_card_balance_cents": int,
        "remaining_cart_total_cents": int}``。
    """
    if cart_total < 0:
        raise ValueError("allocate_gift_card_balance: cart_total must be non-negative")
    if card_balance < 0:
        raise ValueError("allocate_gift_card_balance: card_balance must be non-negative")

    applied = min(cart_total, card_balance)
    return {
        "applied_cents": applied,
        "remaining_card_balance_cents": card_balance - applied,
        "remaining_cart_total_cents": cart_total - applied,
    }
