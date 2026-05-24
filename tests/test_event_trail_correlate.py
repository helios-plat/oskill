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
