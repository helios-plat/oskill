"""Tests for the compatibility financial-query router."""

from oskill.ai_qa.copilot_skill import answer_financial_query


def test_copilot_routes_quote_without_asserting_a_market_price():
    result = answer_financial_query("What is the price of BTC?", {"price": 12345})
    assert result["status"] == "routed"
    assert result["command"] == "QUOTE"
    assert result["arguments"] == ["BTC"]
    assert "price" not in result


def test_copilot_returns_explicit_unmatched_for_unknown_query():
    result = answer_financial_query("Tell me a joke")
    assert result["status"] == "unmatched"
    assert result["command"] is None
