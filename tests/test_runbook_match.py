import sys
from unittest.mock import MagicMock, patch
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
from oskill.runbook_match import runbook_match, RunbookMatchResult

def test_runbook_match_rule_pattern():
    """Test matching by error pattern regex."""
    root_cause = {"root_cause_hypothesis": "Critical: Connection to redis failed"}
    plugins = [
        {"name": "redis_fix", "matcher": {"error_pattern": "redis failed"}},
        {"name": "db_fix", "matcher": {"error_pattern": "db error"}}
    ]
    result = runbook_match(root_cause=root_cause, available_plugins=plugins)
    assert result.matched_plugin["name"] == "redis_fix"
    assert result.match_score == 0.9

def test_runbook_match_service_type():
    """Test matching by service type."""
    root_cause = {"root_cause_hypothesis": "Something went wrong", "service_type": "postgresql"}
    plugins = [
        {"name": "pg_check", "matcher": {"service_type": "postgresql"}},
        {"name": "generic_check", "matcher": {"service_type": "other"}}
    ]
    result = runbook_match(root_cause=root_cause, available_plugins=plugins)
    assert result.matched_plugin["name"] == "pg_check"
    assert result.match_score == 0.8

def test_runbook_match_multiple_hits():
    """Test sorting multiple hits by score."""
    root_cause = {"root_cause_hypothesis": "Redis down", "service_type": "redis"}
    plugins = [
        {"name": "redis_pattern", "matcher": {"error_pattern": "Redis"}}, # 0.9
        {"name": "redis_service", "matcher": {"service_type": "redis"}}  # 0.8
    ]
    result = runbook_match(root_cause=root_cause, available_plugins=plugins)
    assert result.matched_plugin["name"] == "redis_pattern"
    assert len(result.alternative_plugins) == 1
    assert result.alternative_plugins[0]["name"] == "redis_service"

def test_runbook_match_min_score():
    """Test respecting min_match_score."""
    root_cause = {"root_cause_hypothesis": "Vague error"}
    plugins = [
        {"name": "weak_match", "matcher": {"error_pattern": "error"}} # 0.9
    ]
    # If we set min_match_score to 0.95, it shouldn't match
    result = runbook_match(root_cause=root_cause, available_plugins=plugins, min_match_score=0.95)
    assert result.matched_plugin is None

def test_runbook_match_no_plugins():
    """Test with empty plugin list."""
    result = runbook_match(root_cause={"h": "test"}, available_plugins=[])
    assert result.matched_plugin is None

def test_runbook_match_no_matcher():
    """Test plugin without matcher fields."""
    root_cause = {"root_cause_hypothesis": "test"}
    plugins = [{"name": "empty_plugin", "matcher": {}}]
    result = runbook_match(root_cause=root_cause, available_plugins=plugins)
    assert result.matched_plugin is None

def test_runbook_match_hybrid_strategy_placeholder():
    """Test hybrid strategy (currently same as rule-based in impl)."""
    root_cause = {"root_cause_hypothesis": "regex match"}
    plugins = [{"name": "p1", "matcher": {"error_pattern": "regex"}}]
    result = runbook_match(root_cause=root_cause, available_plugins=plugins, matcher_strategy="hybrid")
    assert result.matched_plugin["name"] == "p1"

def test_runbook_match_embedding_strategy_placeholder():
    """Test embedding strategy placeholder."""
    root_cause = {"root_cause_hypothesis": "semantic match"}
    plugins = [{"name": "p1", "matcher": {}}]
    # Currently embedding_fn logic is a placeholder
    result = runbook_match(root_cause=root_cause, available_plugins=plugins, matcher_strategy="embedding", embedding_fn=lambda x: [0.1])
    assert result.matched_plugin is None

def test_runbook_match_malformed_pattern():
    """Test with malformed regex pattern."""
    root_cause = {"root_cause_hypothesis": "test"}
    plugins = [{"name": "p1", "matcher": {"error_pattern": "["}}]
    with pytest.raises(Exception): # re.error
        runbook_match(root_cause=root_cause, available_plugins=plugins)
