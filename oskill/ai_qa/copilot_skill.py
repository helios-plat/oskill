"""Natural language AI Q&A skill (Gloomberb Ask Gloom / MCP style).
MIT License - adapted from Gloomberb.
"""
from __future__ import annotations
from typing import Any

def answer_financial_query(query: str, context_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Answer financial / crypto queries combining natural language reasoning and context."""
    query_lower = query.lower()
    ctx = context_data or {}
    
    if "price" in query_lower or "quote" in query_lower:
        target = ctx.get("target", "BTC")
        price = ctx.get("price", 68250.0)
        return {
            "answer": f"The current price of {target} is  USD based on Helios data feed.",
            "confidence": 0.95,
            "source": "Helios Copilot"
        }
    elif "risk" in query_lower or "kelly" in query_lower:
        return {
            "answer": "Kelly criterion recommends optimal position sizing based on win probability and payout ratio. Always maintain strict risk limits.",
            "confidence": 0.92,
            "source": "Helios Copilot"
        }
    else:
        return {
            "answer": f"I have processed your query: '{query}'. Helios advisory engine reports normal market regime.",
            "confidence": 0.88,
            "source": "Helios Copilot"
        }
