"""oskill.compute_cart_grand_total — 购物车总计（分）。纯内存算法。"""

from __future__ import annotations


def compute_cart_grand_total(
    subtotal: int, *, discount: int = 0, tax: int = 0, shipping: int = 0
) -> int:
    """grand_total = max(subtotal - discount, 0) + tax + shipping。

    运费透传：本函数不计算运费，shipping 由调用方直接传入已知值
    （对齐"不用写跨仓结算，运费直接透传"的范围约定）；tax/discount 同理，
    本轮尚无税费/折扣引擎，调用方传当前 cart 上已有的值（通常为 0）。

    Args:
        subtotal: 小计（分），一般来自 compute_cart_subtotal。
        discount: 折扣金额（分），非负。
        tax: 税费（分），非负。
        shipping: 运费（分），非负，透传值。

    Returns:
        总计金额（分）。

    Raises:
        ValueError: 任一金额为负数。
    """
    if subtotal < 0 or discount < 0 or tax < 0 or shipping < 0:
        raise ValueError("compute_cart_grand_total: all amounts must be non-negative")
    return max(subtotal - discount, 0) + tax + shipping
