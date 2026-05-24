import sys
from unittest.mock import MagicMock
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

from unittest.mock import MagicMock, patch

import pytest
from datetime import datetime, timezone, timedelta
from oskill import (
    container_health_aggregate,
    metric_baseline_compare,
    structured_log_anomaly_cluster,
    event_trail_correlate,
)

# === container_health_aggregate tests ===

def test_container_health_aggregate_all_healthy():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        with patch("oskill.container_health_aggregate.http_health_probe") as mock_probe:
            mock_inspect.return_value = {"State": {"Running": True, "Health": {"Status": "healthy"}}}
            mock_probe.return_value = {"healthy": True, "elapsed_ms": 10, "status_code": 200}
            
            result = container_health_aggregate(container_id="test", check_endpoints=["http://localhost:8080"])
            assert result.overall_status == "healthy"
            assert len(result.passing_checks) == 1
            assert result.aggregate_health_score == 1.0

def test_container_health_aggregate_degraded():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        with patch("oskill.container_health_aggregate.http_health_probe") as mock_probe:
            mock_inspect.return_value = {"State": {"Running": True}}
            mock_probe.side_effect = [
                {"healthy": True, "elapsed_ms": 10, "status_code": 200},
                {"healthy": False, "elapsed_ms": 0, "status_code": 500, "error": "Internal Error"}
            ]
            
            result = container_health_aggregate(container_id="test", check_endpoints=["http://ok", "http://fail"])
            assert result.overall_status == "degraded"
            assert len(result.passing_checks) == 1
            assert len(result.failing_checks) == 1
            assert result.aggregate_health_score == 0.5

def test_container_health_aggregate_down():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        mock_inspect.return_value = {"State": {"Running": False}}
        
        result = container_health_aggregate(container_id="test", check_endpoints=["http://localhost"])
        assert result.overall_status == "down"
        assert result.aggregate_health_score == 0.0

def test_container_health_aggregate_unhealthy_internal():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        with patch("oskill.container_health_aggregate.http_health_probe") as mock_probe:
            mock_inspect.return_value = {"State": {"Running": True, "Health": {"Status": "unhealthy"}}}
            mock_probe.return_value = {"healthy": True, "elapsed_ms": 10, "status_code": 200}
            
            result = container_health_aggregate(container_id="test", check_endpoints=["http://localhost:8080"])
            assert result.overall_status == "degraded"
            assert any(f.endpoint == "docker-internal-healthcheck" for f in result.failing_checks)

def test_container_health_aggregate_probe_exception():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        with patch("oskill.container_health_aggregate.http_health_probe") as mock_probe:
            mock_inspect.return_value = {"State": {"Running": True}}
            mock_probe.side_effect = Exception("Probe failed")
            
            result = container_health_aggregate(container_id="test", check_endpoints=["http://error"])
            assert result.overall_status == "degraded"
            assert result.failing_checks[0].error == "Probe failed"

def test_container_health_aggregate_no_endpoints():
    with patch("oskill.container_health_aggregate.docker_container_inspect") as mock_inspect:
        mock_inspect.return_value = {"State": {"Running": True}}
        
        result = container_health_aggregate(container_id="test", check_endpoints=[])
        assert result.overall_status == "healthy"
        assert result.aggregate_health_score == 1.0

# === metric_baseline_compare tests ===

def test_metric_baseline_compare_no_common():
    result = metric_baseline_compare(current_metrics={"a": 1}, baseline_metrics={"b": 1})
    assert result.verdict == "healthy"
    assert result.overall_health_score == 1.0

def test_metric_baseline_compare_higher_is_better():
    current = {"success_rate": 0.8}
    baseline = {"success_rate": 0.9} # -11% decrease
    result = metric_baseline_compare(
        current_metrics=current, 
        baseline_metrics=baseline, 
        degradation_threshold=0.1,
        metric_directions={"success_rate": "higher_is_better"}
    )
    assert result.verdict == "degraded"

def test_metric_baseline_compare_zero_baseline():
    result = metric_baseline_compare(current_metrics={"errors": 10}, baseline_metrics={"errors": 0})
    assert result.verdict == "critical" # 100% degradation assumed

# === structured_log_anomaly_cluster tests ===

def test_log_anomaly_cluster_empty():
    result = structured_log_anomaly_cluster(log_lines=[])
    assert result.total_lines == 0
    assert result.clusters == []

def test_log_anomaly_cluster_malformed_timestamp():
    logs = [
        {"timestamp": "not-a-date", "event": "Bad date"},
        {"event": "No date"}
    ]
    result = structured_log_anomaly_cluster(log_lines=logs, time_window_sec=3600, min_cluster_size=1)
    assert result.total_lines == 2

# === event_trail_correlate tests ===

def test_event_trail_correlate_not_found():
    with pytest.raises(ValueError, match="not found"):
        event_trail_correlate(target_event_id="E_MISSING", all_events=[])

def test_event_trail_correlate_circular():
    events = [
        {"id": "E1", "parent_id": "E2", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "parent_id": "E1", "timestamp": "2026-05-24T10:00:01Z"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events)
    assert len(result.causally_related) == 1
    assert result.causally_related[0]["id"] == "E2"

def test_metric_baseline_compare_healthy():
    current = {"latency": 100, "error_rate": 0.01}
    baseline = {"latency": 110, "error_rate": 0.02}
    result = metric_baseline_compare(current_metrics=current, baseline_metrics=baseline)
    assert result.verdict == "healthy"
    assert len(result.degraded_metrics) == 0

def test_metric_baseline_compare_degraded():
    current = {"latency": 130} # +30% vs baseline
    baseline = {"latency": 100}
    result = metric_baseline_compare(current_metrics=current, baseline_metrics=baseline, degradation_threshold=0.2)
    assert result.verdict == "degraded"
    assert len(result.degraded_metrics) == 1

def test_metric_baseline_compare_critical():
    current = {"latency": 160} # +60% vs baseline
    baseline = {"latency": 100}
    result = metric_baseline_compare(current_metrics=current, baseline_metrics=baseline, critical_threshold=0.5)
    assert result.verdict == "critical"

# === structured_log_anomaly_cluster tests ===

def test_log_anomaly_cluster_basic():
    logs = [
        {"timestamp": "2026-05-24T10:00:00Z", "event": "User 123 logged in"},
        {"timestamp": "2026-05-24T10:01:00Z", "event": "User 456 logged in"},
        {"timestamp": "2026-05-24T10:02:00Z", "event": "Connection timed out from 192.168.1.1"}
    ]
    result = structured_log_anomaly_cluster(log_lines=logs, min_cluster_size=1)
    assert len(result.clusters) == 2 # "User <NUM> logged in" and "Connection timed out from <IP>"
    assert result.total_lines == 3
    assert result.unique_patterns == 2

def test_log_anomaly_cluster_with_time_window():
    now = datetime.now(timezone.utc)
    logs = [
        {"timestamp": (now - timedelta(minutes=10)).isoformat(), "event": "Recent event"},
        {"timestamp": (now - timedelta(hours=2)).isoformat(), "event": "Old event"}
    ]
    result = structured_log_anomaly_cluster(log_lines=logs, time_window_sec=3600, min_cluster_size=1)
    assert result.total_lines == 1
    assert result.clusters[0].representative_message == "Recent event"

# === event_trail_correlate tests ===

def test_event_trail_correlate_causal():
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "timestamp": "2026-05-24T10:01:00Z", "parent_id": "E1"},
        {"id": "E3", "timestamp": "2026-05-24T10:02:00Z", "root_cause_id": "E1"}
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events)
    assert len(result.causally_related) == 2
    assert result.confidence == 1.0

def test_event_trail_correlate_time_only():
    events = [
        {"id": "E1", "timestamp": "2026-05-24T10:00:00Z"},
        {"id": "E2", "timestamp": "2026-05-24T10:00:05Z"} # 5 seconds later, no causal link
    ]
    result = event_trail_correlate(target_event_id="E1", all_events=events, time_window_sec=10)
    assert len(result.causally_related) == 0
    assert len(result.time_window_correlated) == 1
    assert result.confidence == 0.5
