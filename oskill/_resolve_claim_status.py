"""oskill.resolve_claim_status — 由事件时间线推导售后理赔(claim)当前状态。

设计取向:事件列表按时间顺序(调用方保证),取最后一个事件的 type 即为
当前状态——不做状态转移合法性校验(那属于状态机管理,超出本原子职责)。
"""

from __future__ import annotations

_VALID_STATUSES = {"pending", "approved", "rejected", "canceled"}


def resolve_claim_status(events: list) -> str:
    """推导理赔当前状态:取事件列表最后一项的 type,空列表视为 pending。

    Args:
        events: 按时间顺序排列的事件列表,每项须含 ``type``,取值范围:
            ``pending`` / ``approved`` / ``rejected`` / ``canceled``。

    Returns:
        最后一个事件的 type;``events`` 为空时返回 ``"pending"``。

    Raises:
        ValueError: 最后一个事件的 type 不在合法取值范围内。
    """
    if not events:
        return "pending"

    status = events[-1]["type"]
    if status not in _VALID_STATUSES:
        raise ValueError(f"resolve_claim_status: unknown event type {status!r}")

    return status
