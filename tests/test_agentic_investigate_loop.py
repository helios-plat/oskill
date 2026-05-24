import sys
from unittest.mock import MagicMock, patch
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
import json
from oskill.agentic_investigate_loop import agentic_investigate_loop, InvestigationOutcome, InvestigationStep
from oskill._signal import Signal
from obase.tool_registry import ToolRegistry, register_tool

def test_agentic_investigate_loop_confidence_stop():
    """Test stopping when confidence threshold is reached."""
    mock_llm = MagicMock()
    mock_llm.side_effect = [
        {
            "content": "I need to check logs. tool_use: oprim__docker_container_logs",
            "stop_reason": "tool_use",
            "tool_calls": [{"id": "1", "name": "oprim__docker_container_logs", "input": {"container_id": "c1"}}]
        },
        {
            "content": "Root Cause Hypothesis: Memory leak. Confidence: 0.9",
            "stop_reason": "end_turn",
            "tool_calls": []
        }
    ]
    
    def mock_logs(*, container_id: str):
        return {"logs": "out of memory"}
    mock_logs.__name__ = "docker_container_logs"
    mock_logs.__module__ = "oprim"

    ToolRegistry.clear()
    ToolRegistry.register(mock_logs, permission="read")

    signal = Signal(source="test", severity="critical")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=["oprim.docker_container_logs"],
        llm=mock_llm,
        confidence_threshold=0.8
    )
    
    assert result.stopped_reason == "llm_decided_stop"
    assert result.steps_taken == 1
    assert result.final_conclusion["confidence"] == 0.9
    assert "Memory leak" in result.final_conclusion["root_cause_hypothesis"]

def test_agentic_investigate_loop_max_steps():
    """Test reaching max steps."""
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "content": "Still investigating...",
        "stop_reason": "tool_use",
        "tool_calls": [{"id": "1", "name": "oprim__dummy_tool", "input": {}}]
    }
    
    def dummy_tool():
        return {}
    dummy_tool.__name__ = "dummy_tool"
    dummy_tool.__module__ = "oprim"

    ToolRegistry.clear()
    ToolRegistry.register(dummy_tool, permission="read")

    signal = Signal(source="test", severity="info")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=["oprim.dummy_tool"],
        llm=mock_llm,
        max_steps=3
    )
    
    assert result.stopped_reason == "max_steps"
    assert result.steps_taken == 3

def test_agentic_investigate_loop_llm_error():
    """Test LLM call error."""
    mock_llm = MagicMock(side_effect=Exception("API Error"))
    
    signal = Signal(source="test", severity="warning")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=[],
        llm=mock_llm
    )
    
    assert result.stopped_reason == "error"
    assert "API Error" in result.final_conclusion["error"]

def test_agentic_investigate_loop_tool_not_found():
    """Test calling a tool that is not in the registry."""
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "content": "Calling missing tool",
        "stop_reason": "tool_use",
        "tool_calls": [{"id": "1", "name": "missing_tool", "input": {}}]
    }
    
    signal = Signal(source="test", severity="warning")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=["missing_tool"],
        llm=mock_llm,
        max_steps=1
    )
    
    assert result.steps[0].tool_output["error"] == "Tool missing_tool not found"

def test_agentic_investigate_loop_tool_exception():
    """Test tool execution error."""
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "content": "Calling failing tool",
        "stop_reason": "tool_use",
        "tool_calls": [{"id": "1", "name": "oprim__fail_tool", "input": {}}]
    }
    
    def fail_tool():
        raise ValueError("Tool crash")
    fail_tool.__name__ = "fail_tool"
    fail_tool.__module__ = "oprim"

    ToolRegistry.clear()
    ToolRegistry.register(fail_tool, permission="read")

    signal = Signal(source="test", severity="warning")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=["oprim.fail_tool"],
        llm=mock_llm,
        max_steps=1
    )
    
    assert result.steps[0].tool_output["error"] == "Tool crash"

def test_agentic_investigate_loop_on_step_callback():
    """Test on_step callback."""
    mock_llm = MagicMock()
    mock_llm.side_effect = [
        {
            "content": "Check something",
            "stop_reason": "tool_use",
            "tool_calls": [{"id": "1", "name": "oprim__t1", "input": {}}]
        },
        {
            "content": "Done",
            "stop_reason": "end_turn",
            "tool_calls": []
        }
    ]
    
    def t1():
        return {"ok": True}
    t1.__name__ = "t1"
    t1.__module__ = "oprim"

    ToolRegistry.clear()
    ToolRegistry.register(t1, permission="read")

    callback_steps = []
    def on_step(step):
        callback_steps.append(step)

    signal = Signal(source="test", severity="warning")
    agentic_investigate_loop(
        signal=signal,
        available_tool_names=["oprim.t1"],
        llm=mock_llm,
        on_step=on_step
    )
    
    assert len(callback_steps) == 1
    assert callback_steps[0]["tool_called"] == "oprim.t1"

def test_extract_confidence_edge_cases():
    """Test confidence extraction from various formats."""
    from oskill._utils import extract_confidence
    assert extract_confidence("Confidence: 0.85") == 0.85
    assert extract_confidence("I am 1.0 certain") == 1.0
    assert extract_confidence("no confidence mentioned") == 0.5
    assert extract_confidence("Confidence: high") == 0.5

def test_parse_final_conclusion_edge_cases():
    """Test parsing conclusion from text."""
    from oskill.agentic_investigate_loop import _parse_final_conclusion
    text = "Some chatter. Root Cause Hypothesis: CPU spike due to cron job. Confidence: 0.9"
    c = _parse_final_conclusion(text)
    assert c["root_cause_hypothesis"] == "CPU spike due to cron job."
    assert c["confidence"] == 0.9

def test_agentic_investigate_loop_no_available_tools():
    """Test loop with no tools available."""
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "content": "I have no tools to use. Root Cause Hypothesis: Unknown.",
        "stop_reason": "end_turn",
        "tool_calls": []
    }
    
    signal = Signal(source="test", severity="warning")
    result = agentic_investigate_loop(
        signal=signal,
        available_tool_names=["non_existent_tool"],
        llm=mock_llm
    )
    assert result.stopped_reason == "llm_decided_stop"
