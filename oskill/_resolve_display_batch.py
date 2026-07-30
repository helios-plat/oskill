"""oskill.resolve_display_batch — 从批次候选集中筛出主仓/邻仓在架批次，按距离排序。

纯内存算法：调用方（omodul/oservi）负责把 inventory_batch JOIN stock_location
的原始行拍平成 dict 列表传入；本函数不做任何 DB / 网络 IO。
"""

from __future__ import annotations

import math

_EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """两点球面距离（公里）。"""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def resolve_display_batch(
    batches: list[dict],
    *,
    user_region: str | None = None,
    user_lat: float | None = None,
    user_lng: float | None = None,
    max_distance_km: float = 150.0,
    limit: int = 20,
) -> list[dict]:
    """筛出用户主仓 + 邻仓范围内、当前可售的批次，按“是否主仓→距离”升序排列。

    Args:
        batches: 每项须含 status, inspection_status, stock_qty, reserved_qty,
            location_region, location_lat, location_lng 等字段（调用方已 JOIN 好）。
        user_region: 用户绑定大区，对齐 omodul.set_cart_region。同区批次视为主仓，
            必然入选（不受 max_distance_km 限制）。
        user_lat / user_lng: 用户坐标；用于计算非主仓批次是否落在邻仓半径内。
            两者任一缺失时，非主仓批次一律排除（无法判断距离，不做无依据展示）。
        max_distance_km: 邻仓半径，非主仓且超出此距离的批次被剔除。
        limit: 返回条数上限。

    Returns:
        批次列表，每项附加 available_qty / is_home_location / distance_km。
        distance_km 在坐标缺失时为 None。
    """
    eligible: list[dict] = []

    for b in batches:
        if b.get("status") != "active":
            continue
        if b.get("inspection_status") != "passed":
            continue

        available = b.get("stock_qty", 0) - b.get("reserved_qty", 0)
        if available <= 0:
            continue

        is_home = user_region is not None and b.get("location_region") == user_region

        distance_km = None
        loc_lat, loc_lng = b.get("location_lat"), b.get("location_lng")
        if (
            user_lat is not None
            and user_lng is not None
            and loc_lat is not None
            and loc_lng is not None
        ):
            distance_km = _haversine_km(user_lat, user_lng, loc_lat, loc_lng)

        if not is_home:
            if distance_km is None or distance_km > max_distance_km:
                continue

        eligible.append(
            {
                **b,
                "available_qty": available,
                "is_home_location": is_home,
                "distance_km": distance_km,
            }
        )

    eligible.sort(
        key=lambda b: (
            0 if b["is_home_location"] else 1,
            b["distance_km"] if b["distance_km"] is not None else float("inf"),
        )
    )
    return eligible[:limit]
