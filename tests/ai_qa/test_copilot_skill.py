"""Tests for AI Q&A oskill."""
from oskill.ai_qa.copilot_skill import answer_financial_query

def test_copilot_query():
    res = answer_financial_query("What is the price of BTC?", {"target": "BTC", "price": 69000.0})
    assert "BTC" in res["answer"]
    assert res["confidence"] > 0.9
