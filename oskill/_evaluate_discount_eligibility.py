"""oskill.evaluate_discount_eligibility — 判断一张折扣是否可用于当前购物车。

纯内存算法：只做资格判定（金额门槛/时间窗/区域/使用次数上限），不判定
"哪些行适用"（那是 evaluate_discount_conditions 的职责）。
"""

from __future__ import annotations

from datetime import UTC, datetime


def _parse_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def evaluate_discount_eligibility(cart: dict, *, rule: dict) -> bool:
    """折扣资格判定。所有存在的约束项都必须满足；缺省字段视为不限制。

    Args:
        cart: 须含 ``subtotal_cents``；可选 ``region_code``。
        rule: 折扣规则，均为可选键：
            - ``min_subtotal_cents``: 购物车小计门槛（含等于）。
            - ``valid_from`` / ``valid_until``: ISO-8601 时间字符串，判定当前
              UTC 时间是否落在窗口内（闭区间）。
            - ``region_codes``: 允许的区域码列表；cart 无 region_code 或不在
              列表内则不合格。
            - ``max_uses`` + ``uses_count``: 用满即不合格（``uses_count >= max_uses``）。

    Returns:
        是否符合全部已声明的约束。
    """
    if "min_subtotal_cents" in rule:
        if cart.get("subtotal_cents", 0) < rule["min_subtotal_cents"]:
            return False

    now = datetime.now(UTC)
    if rule.get("valid_from"):
        if now < _parse_utc(rule["valid_from"]):
            return False
    if rule.get("valid_until"):
        if now > _parse_utc(rule["valid_until"]):
            return False

    if rule.get("region_codes"):
        if cart.get("region_code") not in rule["region_codes"]:
            return False

    if "max_uses" in rule:
        if rule.get("uses_count", 0) >= rule["max_uses"]:
            return False

    return True
