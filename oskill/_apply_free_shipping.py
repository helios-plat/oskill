"""oskill.apply_free_shipping — 把运费方式列表里的价格清零。"""

from __future__ import annotations


def apply_free_shipping(shipping_methods: list[dict]) -> list[dict]:
    """返回运费方式列表的副本，每项 ``price_cents`` 归零，其余字段保留。

    Args:
        shipping_methods: 每项须含 ``price_cents``。

    Returns:
        新列表（不修改入参），每项新增/覆盖 ``price_cents=0``。
    """
    return [{**method, "price_cents": 0} for method in shipping_methods]
