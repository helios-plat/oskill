import sys
from unittest.mock import MagicMock
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
from datetime import datetime, timedelta, timezone
from oskill.event_trail_correlate import event_trail_correlate, CorrelatedEvents

def test_event_trail_correlate_causal_chain():
    """Test explicit causal chain (parent_id/root_cause_id)."""
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "parent_id": "E1", "timestamp": "2026-05-24T10:01:00Z"},
        {"id": "E3", "root_cause_id": "E1", "timestamp": "2026-05-24T10:02:00Z"},
        {"id": "E4", "parent_id": "E2", "timestamp": "2026-05-24T10:03:00Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events)
    assert len(result.causally_related) == 3
    ids = {e["id"] for e in result.causally_related}
    assert ids == {"E2", "E3", "E4"}
    assert result.confidence == 1.0

def test_event_trail_correlate_time_window():
    """Test correlation based on time window only."""
    base_time = datetime.now(timezone.utc)
    events = [
        {"id": "E1", "timestamp": base_time.isoformat()},
        {"id": "E2", "timestamp": (base_time + timedelta(seconds=10)).isoformat()},
        {"id": "E3", "timestamp": (base_time - timedelta(seconds=10)).isoformat()},
        {"id": "E4", "timestamp": (base_time + timedelta(seconds=600)).isoformat()}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events, time_window_sec=30)
    assert len(result.time_window_correlated) == 2
    ids = {e["id"] for e in result.time_window_correlated}
    assert ids == {"E2", "E3"}
    assert result.confidence == 0.5

def test_event_trail_correlate_circular_reference():
    """Test circular references in causal chain."""
    events = [
        {"id": "E1", "parent_id": "E2", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "parent_id": "E1", "timestamp": "2026-05-24T10:00:01Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events)
    assert len(result.causally_related) == 1
    assert result.causally_related[0]["id"] == "E2"

def test_event_trail_correlate_ancestors():
    """Test finding ancestors in causal chain."""
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "parent_id": "E1", "timestamp": "2026-05-24T10:01:00Z"},
        {"id": "E3", "parent_id": "E2", "timestamp": "2026-05-24T10:02:00Z"}
    ]
    result = event_trail_correlate(target_event_id="E3", all_events=events)
    assert len(result.causally_related) == 2
    ids = {e["id"] for e in result.causally_related}
    assert ids == {"E1", "E2"}

def test_event_trail_correlate_empty_events():
    """Test empty event list."""
    with pytest.raises(ValueError, match="not found"):
        event_trail_correlate(target_event_id="E1", all_events=[])

def test_event_trail_correlate_no_timestamp():
    """Test events without timestamps."""
    events = [
        {"id": "E1"},
        {"id": "E2", "parent_id": "E1"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events)
    assert len(result.causally_related) == 1
    assert len(result.time_window_correlated) == 0

def test_event_trail_correlate_custom_keys():
    """Test custom causal keys."""
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "caused_by": "E1", "timestamp": "2026-05-24T10:01:00Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events, causal_keys=("caused_by",))
    assert len(result.causally_related) == 1
    assert result.causally_related[0]["id"] == "E2"

def test_event_trail_correlate_malformed_iso():
    """Test malformed ISO timestamps."""
    events = [
        {"id": "E1", "timestamp": "invalid"},
        {"id": "E2", "timestamp": "2026-05-24T10:00:00Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events, time_window_sec=10)
    assert len(result.time_window_correlated) == 0

def test_event_trail_correlate_no_correlation():
    """Test no causal or time correlation."""
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "timestamp": "2026-05-24T11:00:00Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events, time_window_sec=10)
    assert len(result.causally_related) == 0
    assert len(result.time_window_correlated) == 0
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# 变更邻近度加权 (aegis DESIGN #14 扩展, §10.2)
# ---------------------------------------------------------------------------

_CHANGE_EVENTS = [
    {"id": "E1", "timestamp": "2026-07-04T12:00:00Z"},  # target
    {"id": "D1", "type": "deploy", "timestamp": "2026-07-04T11:59:30Z"},  # 30s 前
    {"id": "D2", "type": "deploy", "timestamp": "2026-07-04T11:58:00Z"},  # 120s 前
    {"id": "N1", "type": "metric", "timestamp": "2026-07-04T11:59:00Z"},  # 非变更
]


def test_change_proximity_collected_and_sorted():
    r = event_trail_correlate(
        target_event_id="E1",
        all_events=_CHANGE_EVENTS,
        time_window_sec=300,
        change_event_types=("deploy",),
    )
    ids = [e["id"] for e in r.change_correlated]
    assert ids == ["D1", "D2"]  # 按邻近度升序,D1(30s)在 D2(120s)前
    assert r.confidence == 0.7  # 无因果链但有邻近变更 → 抬高


def test_change_event_type_key_variant():
    events = [
        {"id": "E1", "timestamp": "2026-07-04T12:00:00Z"},
        {"id": "U1", "event_type": "upgrade", "timestamp": "2026-07-04T11:59:50Z"},
    ]
    r = event_trail_correlate(
        target_event_id="E1", all_events=events, change_event_types=("upgrade",)
    )
    assert [e["id"] for e in r.change_correlated] == ["U1"]


def test_backward_compat_no_change_param():
    # 不给 change_event_types → change_correlated 空,confidence 同原实现(纯时间窗 0.5)
    r = event_trail_correlate(
        target_event_id="E1", all_events=_CHANGE_EVENTS, time_window_sec=300
    )
    assert r.change_correlated == []
    assert r.confidence == 0.5


def test_causal_chain_still_wins_over_change():
    events = [
        {"id": "E1", "parent_id": "R1", "timestamp": "2026-07-04T12:00:00Z"},
        {"id": "R1", "timestamp": "2026-07-04T11:59:00Z"},
        {"id": "D1", "type": "deploy", "timestamp": "2026-07-04T11:59:40Z"},
    ]
    r = event_trail_correlate(
        target_event_id="E1", all_events=events, change_event_types=("deploy",)
    )
    assert r.confidence == 1.0  # 有因果链,confidence 仍 1.0(因果优先于变更)


def test_change_confidence_injectable():
    # 默认 0.7,可注入覆盖(六口径 ④:confidence 做可注入参数)
    r = event_trail_correlate(
        target_event_id="E1",
        all_events=_CHANGE_EVENTS,
        change_event_types=("deploy",),
        change_confidence=0.85,
    )
    assert r.confidence == 0.85
