"""Compose external TradingView data sources without merging them into Helios scoring."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
from oprim._tv_transport import TVTransport
from oprim.tv_fetch_technicals import fetch_tv_technicals
from oprim.tv_fetch_symbol_markets import fetch_tv_symbol_markets
from oprim.tv_fetch_minds import fetch_tv_minds
from oprim.tv_fetch_news import fetch_tv_news

__oskill_layer__ = "composite"
__oskill_exports__ = ["tradingview_market_snapshot"]

def tradingview_market_snapshot(symbol: str, *, quote: str = "USDT", market_limit: int = 20,
                                community_limit: int = 10, news_limit: int = 10,
                                transport: TVTransport | None = None,
                                fetchers: dict[str, Callable[[], dict]] | None = None) -> dict:
    """Fetch technicals, listings, news, and Minds independently, preserving per-source status/data.

    Minds/community content is left raw: this skill does not derive a sentiment score or
    modify Fusion Score dimensions, weights, alerts, or trading state.
    """
    if not isinstance(symbol, str) or ":" not in symbol:
        return {"status": "failed", "symbol": symbol,
                "error": {"type": "ValueError", "message": "symbol must include exchange prefix"},
                "fusion_integrated": False, "trading_enabled": False}
    exchange, ticker = (part.strip().upper() for part in symbol.split(":", 1))
    if not exchange or not ticker:
        return {"status": "failed", "symbol": symbol,
                "error": {"type": "ValueError", "message": "symbol must be EXCHANGE:TICKER"},
                "fusion_integrated": False, "trading_enabled": False}
    if not 1 <= market_limit <= 200 or not 1 <= community_limit <= 100 or not 1 <= news_limit <= 100:
        return {"status": "failed", "symbol": symbol,
                "error": {"type": "ValueError", "message": "limits are out of bounds"},
                "fusion_integrated": False, "trading_enabled": False}
    base = ticker
    for suffix in ("USDT", "USDC", "BUSD", "USD"):
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[:-len(suffix)]
            break
    fns = fetchers or {
        "technicals": lambda: fetch_tv_technicals(exchange, ticker, transport=transport),
        "markets": lambda: fetch_tv_symbol_markets(base, quote=quote, limit=market_limit, transport=transport),
        "news": lambda: fetch_tv_news(exchange, ticker, limit=news_limit, transport=transport),
        "community": lambda: fetch_tv_minds(f"{exchange}:{ticker}", limit=community_limit, transport=transport),
    }
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(fns))), thread_name_prefix="tv-market") as pool:
        futures = {name: pool.submit(call) for name, call in fns.items()}
        for name, future in futures.items():
            try:
                value = future.result()
                if not isinstance(value, dict) or value.get("status") not in {"success", "degraded", "failed"}:
                    value = {"status": "failed", "data": None,
                             "error": {"type": "ProviderContractError", "message": "invalid provider result"}}
                results[name] = value
            except Exception as exc:
                results[name] = {"status": "failed", "source": "tradingview", "data": None,
                                 "error": {"type": type(exc).__name__, "message": str(exc)[:300]}}
    successes = sum(item.get("status") in {"success", "degraded"} for item in results.values())
    return {"status": "success" if successes else "failed",
            "error": None if successes else {"type": "ProviderUnavailable", "message": "all external TV sources failed"},
            "symbol": f"{exchange}:{ticker}", "external_signals": results,
            "fusion_integrated": False, "trading_enabled": False, "source": "tradingview"}
