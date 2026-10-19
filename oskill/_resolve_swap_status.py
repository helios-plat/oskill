"""oskill.resolve_swap_status — 由事件时间线推导换货(swap)当前状态。

同 resolve_claim_status:取最后一个事件的 type,不做状态转移合法性校验。
两者刻意各自独立实现(取值范围不同,且 oskill 层同层互调深度限制下没有
必要为 8 行逻辑抽公共 helper)。
"""

from __future__ import annotations

_VALID_STATUSES = {"pending", "processing", "completed", "canceled", "requires_action"}


def resolve_swap_status(events: list) -> str:
    """推导换货当前状态:取事件列表最后一项的 type,空列表视为 pending。

    Args:
        events: 按时间顺序排列的事件列表,每项须含 ``type``,取值范围:
            ``pending`` / ``processing`` / ``completed`` / ``canceled`` /
            ``requires_action``。

    Returns:
        最后一个事件的 type;``events`` 为空时返回 ``"pending"``。

    Raises:
        ValueError: 最后一个事件的 type 不在合法取值范围内。
    """
    if not events:
        return "pending"

    status = events[-1]["type"]
    if status not in _VALID_STATUSES:
        raise ValueError(f"resolve_swap_status: unknown event type {status!r}")

    return status
