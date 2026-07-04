from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel


class CorrelatedEvents(BaseModel):
    target_event_id: str
    causally_related: list[dict[str, Any]]  # 通过 parent_id / root_cause_id 链接
    time_window_correlated: list[dict[str, Any]]  # 时间窗内, 但无显式因果链
    change_correlated: list[dict[str, Any]] = []  # 时间窗内的变更事件, 按邻近度升序(最近在前)
    confidence: float  # 关联可信度


def event_trail_correlate(
    *,
    target_event_id: str,
    all_events: list[dict[str, Any]],
    time_window_sec: int = 300,
    causal_keys: tuple[str, ...] = ("parent_id", "root_cause_id"),
    change_event_types: tuple[str, ...] | None = None,
) -> CorrelatedEvents:
    """按因果链 + 时间窗关联事件, 并对变更事件按邻近度加权.

    纯计算 oskill, 不调外部.

    change_event_types 给定时(如 deploy/upgrade/rollback/policy_change/secret_change),
    时间窗内 type/event_type 命中的事件额外收进 change_correlated(按 |Δt| 升序), 且无因果链
    但有邻近变更时 confidence 提升到 0.7(高于纯时间窗 0.5)—— 业界七八成事故由变更引发,
    确定性地把"变更邻近"作为更强的相关信号(仍停在相关, 不附会因果, DESIGN §10.2/I5)。
    不给该参数时行为与原实现完全一致(向后兼容)。
    """
    event_map = {
        str(e.get("id") or e.get("event_id")): e
        for e in all_events
        if e.get("id") or e.get("event_id")
    }

    target_event = event_map.get(target_event_id)
    if not target_event:
        raise ValueError(f"Target event {target_event_id} not found in all_events")

    causally_related: set[str] = set()

    # 1. Trace causal chain (Ancestors and Descendants)
    to_visit = [target_event_id]
    visited = set()
    while to_visit:
        current_id = to_visit.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        if current_id != target_event_id:
            causally_related.add(current_id)

        # Find descendants (events that point to current as parent/root_cause)
        for eid, e in event_map.items():
            for key in causal_keys:
                if str(e.get(key)) == current_id:
                    to_visit.append(eid)

    # BFS for ancestors
    to_visit = [target_event_id]
    while to_visit:
        current_id = to_visit.pop(0)
        current_event = event_map.get(current_id)
        if not current_event:
            continue

        for key in causal_keys:
            parent_id = cast(str | None, current_event.get(key))
            if parent_id:
                parent_id_str = str(parent_id)
                if parent_id_str in event_map and parent_id_str not in visited:
                    causally_related.add(parent_id_str)
                    visited.add(parent_id_str)
                    to_visit.append(parent_id_str)

    # 2. Time window correlation
    time_window_correlated: set[str] = set()
    target_ts_str = cast(
        str | None, target_event.get("timestamp") or target_event.get("created_at")
    )
    target_ts: datetime | None = None
    if target_ts_str:
        try:
            target_ts = datetime.fromisoformat(target_ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            target_ts = None
    if target_ts is not None:
        for eid, e in event_map.items():
            if eid == target_event_id or eid in causally_related:
                continue
            ts_str = cast(str | None, e.get("timestamp") or e.get("created_at"))
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if abs((ts - target_ts).total_seconds()) <= time_window_sec:
                        time_window_correlated.add(eid)
                except (ValueError, TypeError):
                    pass

    causal_list = [event_map[eid] for eid in causally_related if eid in event_map]
    time_list = [event_map[eid] for eid in time_window_correlated if eid in event_map]

    # 3. Change-proximity weighting (opt-in via change_event_types)。change 事件是时间窗的
    # 子集,额外按 |Δt| 升序收进 change_correlated,并抬高 confidence(变更是更强的相关信号)。
    change_list: list[dict[str, Any]] = []
    if change_event_types and target_ts is not None:
        cset = set(change_event_types)
        scored: list[tuple[float, dict[str, Any]]] = []
        for eid in time_window_correlated:
            e = event_map[eid]
            etype = e.get("type") or e.get("event_type")
            if etype in cset:
                ts_str = cast(str | None, e.get("timestamp") or e.get("created_at"))
                try:
                    ts = datetime.fromisoformat((ts_str or "").replace("Z", "+00:00"))
                    delta = abs((ts - target_ts).total_seconds())
                except (ValueError, TypeError):
                    delta = float("inf")
                scored.append((delta, e))
        scored.sort(key=lambda x: x[0])
        change_list = [e for _, e in scored]

    if causal_list:
        confidence = 1.0
    elif change_list:
        confidence = 0.7
    elif time_list:
        confidence = 0.5
    else:
        confidence = 0.0

    return CorrelatedEvents(
        target_event_id=target_event_id,
        causally_related=causal_list,
        time_window_correlated=time_list,
        change_correlated=change_list,
        confidence=confidence,
    )
