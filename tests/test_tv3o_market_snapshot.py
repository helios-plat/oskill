from oskill.tradingview_market_snapshot import tradingview_market_snapshot

def success(data=None): return lambda: {"status": "success", "source": "tradingview", "data": data or {}}
def test_composes_four_independent_sources():
    called=[]
    fetchers={k:(lambda k=k: called.append(k) or {"status":"success","data":{}}) for k in ("technicals","markets","news","community")}
    out=tradingview_market_snapshot("BINANCE:BTCUSDT",fetchers=fetchers)
    assert out["status"]=="success" and set(called)==set(fetchers)
def test_requires_exchange_prefixed_symbol():
    called=[]; out=tradingview_market_snapshot("BTCUSDT",fetchers={"x":lambda:called.append(1)})
    assert out["status"]=="failed" and not called
def test_keeps_upstream_recommendation_unmodified():
    raw={"Recommend.All":.4212}; out=tradingview_market_snapshot("BINANCE:BTCUSDT",fetchers={"technicals":success(raw)})
    assert out["external_signals"]["technicals"]["data"]==raw
def test_community_text_is_not_converted_to_score():
    raw={"results":[{"text":"bullish narrative"}]}; out=tradingview_market_snapshot("BINANCE:BTCUSDT",fetchers={"community":success(raw)})
    assert out["external_signals"]["community"]["data"]==raw and "sentiment_score" not in out
def test_exception_is_isolated_per_source():
    out=tradingview_market_snapshot("BINANCE:ETHUSDT",fetchers={"ok":success(),"broken":lambda:(_ for _ in ()).throw(OSError("offline"))})
    assert out["status"]=="success" and out["external_signals"]["broken"]["status"]=="failed"
def test_all_sources_failed_is_explicit():
    failure=lambda:{"status":"failed","data":None,"error":{"type":"Offline"}}
    out=tradingview_market_snapshot("BINANCE:BTCUSDT",fetchers={"a":failure,"b":failure})
    assert out["status"]=="failed" and out["fusion_integrated"] is False
def test_base_currency_is_derived_for_pair_lookup():
    seen=[]; fetchers={"markets":lambda:seen.append("BTC") or {"status":"success","data":{}}}
    tradingview_market_snapshot("BINANCE:BTCUSDT",fetchers=fetchers)
    assert seen==["BTC"]
def test_out_of_range_limit_fails_before_provider_calls():
    called=[]; out=tradingview_market_snapshot("BINANCE:BTCUSDT",market_limit=999,fetchers={"x":lambda:called.append(1)})
    assert out["status"]=="failed" and not called
