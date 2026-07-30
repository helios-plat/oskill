"""oskill.evaluate_discount_conditions — 筛出一批折扣条件下真正适用的购物车行。

纯内存算法：eligibility(资格) 判定"这张券能不能用"，本函数判定"券生效
时具体打在哪几行上"（SKU/分类限制池）。
"""

from __future__ import annotations


def evaluate_discount_conditions(items: list[dict], *, condition: dict) -> list[dict]:
    """按限制池筛选适用折扣的行。

    Args:
        items: 购物车行，每项须含 ``product_id``（可选 ``category_id``）。
        condition: 限制池定义：
            - ``type``: ``"all"``（不限，默认）/ ``"products"`` / ``"categories"``。
            - ``target_ids``: ``type`` 为 products/categories 时的白名单 id 列表。

    Returns:
        适用本折扣的行子集；``type="all"`` 或未声明 ``type`` 时原样返回全部行。
    """
    condition_type = condition.get("type", "all")
    if condition_type == "all":
        return list(items)

    target_ids = set(condition.get("target_ids", []))
    if condition_type == "products":
        return [item for item in items if item.get("product_id") in target_ids]
    if condition_type == "categories":
        return [item for item in items if item.get("category_id") in target_ids]

    raise ValueError(f"unknown condition type: {condition_type!r}")
