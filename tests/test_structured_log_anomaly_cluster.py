import sys
from unittest.mock import MagicMock, patch
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
from datetime import datetime, timezone, timedelta
from oskill.structured_log_anomaly_cluster import structured_log_anomaly_cluster, LogCluster, LogAnomalyClusters

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

def test_log_anomaly_cluster_basic():
    logs = [
        {"timestamp": "2026-05-24T10:00:00Z", "event": "User 123 logged in"},
        {"timestamp": "2026-05-24T10:01:00Z", "event": "User 456 logged in"},
        {"timestamp": "2026-05-24T10:02:00Z", "event": "Connection timed out from 192.168.1.1"}
    ]
    result = structured_log_anomaly_cluster(log_lines=logs, min_cluster_size=1)
    # patterns: "User <NUM> logged in" and "Connection timed out from <IP>"
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

def test_log_anomaly_cluster_pattern_extraction():
    message = "Request 0xabc123 failed with status 500 for user-uuid-1234-5678"
    from oskill.structured_log_anomaly_cluster import _extract_pattern_naive
    pattern = _extract_pattern_naive(message)
    assert "<HEX>" in pattern
    assert "<NUM>" in pattern

def test_log_anomaly_cluster_min_size():
    logs = [
        {"event": "E1"},
        {"event": "E1"},
        {"event": "E2"}
    ]
    # min_cluster_size=2 should only return E1 cluster
    result = structured_log_anomaly_cluster(log_lines=logs, min_cluster_size=2)
    assert len(result.clusters) == 1
    assert result.clusters[0].representative_message == "E1"

def test_log_anomaly_cluster_missing_event():
    logs = [{"timestamp": "2026-05-24T10:00:00Z"}]
    result = structured_log_anomaly_cluster(log_lines=logs, min_cluster_size=1)
    assert result.total_lines == 1
    assert len(result.clusters) == 0

def test_log_anomaly_cluster_anomaly_score():
    logs = [
        {"event": "Pattern A"},
        {"event": "Pattern B"},
        {"event": "Pattern C"}
    ]
    result = structured_log_anomaly_cluster(log_lines=logs, min_cluster_size=1)
    assert result.anomaly_score == 1.0 # 3 unique patterns / 3 lines

    logs2 = [{"event": "Same"}] * 10
    result2 = structured_log_anomaly_cluster(log_lines=logs2, min_cluster_size=1)
    assert result2.anomaly_score == 0.1 # 1 unique pattern / 10 lines

def test_log_anomaly_cluster_drain_fallback():
    # Since drain3 is missing, it should use naive
    logs = [{"event": "test"}]
    result = structured_log_anomaly_cluster(log_lines=logs, pattern_extractor="drain", min_cluster_size=1)
    assert len(result.clusters) == 1
