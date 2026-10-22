"""Deterministic fallback and optional structured-LLM Gloom 3O routing tests."""

from __future__ import annotations

from typing import Any

import pytest

from oskill.gloom3o_router import GLOOM3O_COMMANDS, route_gloom3o_command


def test_command_names_are_the_canonical_nine_routes() -> None:
    assert GLOOM3O_COMMANDS == (
        "QUOTE", "DES", "GP", "OPX", "KELLY", "RISK", "PORT", "FUSION", "HELP"
    )


def test_no_llm_key_uses_rules_without_calling_an_available_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("GLOOM3O_LLM_API_KEY", "OPENAI_API_KEY", "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    calls = 0

    def llm_caller(**_: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {}

    result = route_gloom3o_command("BTC price", llm_caller=llm_caller)
    assert result.command == "QUOTE"
    assert result.arguments == ("BTC",)
    assert result.source == "rules"
    assert calls == 0


@pytest.mark.parametrize(
    ("query", "command"),
    [
        ("帮助", "HELP"),
        ("ETH option chain", "OPX"),
        ("show my portfolio", "PORT"),
        ("Fusion score for SOL", "FUSION"),
        ("derivatives summary ETH", "DES"),
        ("Gloom profile for BTC", "GP"),
    ],
)
def test_rule_routes_supported_intents(query: str, command: str) -> None:
    assert route_gloom3o_command(query).command == command


def test_opx_route_carries_explicit_symbol_and_exchange() -> None:
    result = route_gloom3o_command("BTC options on OKX")
    assert result.command == "OPX"
    assert result.arguments == ("BTC",)
    assert result.options == {"underlying": "BTC", "exchange": "okx"}


def test_kelly_route_extracts_only_explicit_probability_odds_and_fraction() -> None:
    result = route_gloom3o_command("Kelly calculate p=60% b=2 fraction=0.5")
    assert result.command == "KELLY"
    assert result.options == {"p": "0.6", "b": "2.0", "fraction": "0.5"}


def test_kelly_route_does_not_invent_missing_parameters() -> None:
    result = route_gloom3o_command("帮我算一下 Kelly")
    assert result.command == "KELLY"
    assert result.options == {}


def test_risk_route_preserves_explicit_observations_only() -> None:
    result = route_gloom3o_command("RISK returns=-0.02,0.01,-0.03")
    assert result.command == "RISK"
    assert result.options == {"returns": "-0.02,0.01,-0.03"}


def test_unmatched_query_is_explicit() -> None:
    result = route_gloom3o_command("tell me a joke")
    assert result.command is None
    assert result.source == "rules"


def test_llm_path_requires_key_and_accepts_valid_tool_arguments() -> None:
    captured: dict[str, Any] = {}

    def llm_caller(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        route_json = '{"command":"FUSION","arguments":["ETH"],"options":{}}'
        return {"tool_calls": [{"function": {"arguments": route_json}}]}

    result = route_gloom3o_command("check this", llm_caller=llm_caller, api_key="provided")
    assert result.command == "FUSION"
    assert result.arguments == ("ETH",)
    assert result.source == "llm"
    assert captured["tools"][0]["function"]["name"] == "route_gloom3o_command"


def test_invalid_llm_route_falls_back_to_rules() -> None:
    def llm_caller(**_: Any) -> dict[str, Any]:
        return {"tool_calls": [{"function": {"arguments": '{"command":"SELL_ALL"}'}}]}

    result = route_gloom3o_command("BTC quote", llm_caller=llm_caller, api_key="provided")
    assert result.command == "QUOTE"
    assert result.source == "rules"


def test_llm_failure_falls_back_to_rules() -> None:
    def llm_caller(**_: Any) -> dict[str, Any]:
        raise RuntimeError("provider not reachable")

    result = route_gloom3o_command("ETH price", llm_caller=llm_caller, api_key="provided")
    assert result.command == "QUOTE"
    assert result.source == "rules"


def test_empty_query_returns_unmatched() -> None:
    result = route_gloom3o_command("   ")
    assert result.command is None
    assert result.reason == "query is empty"
