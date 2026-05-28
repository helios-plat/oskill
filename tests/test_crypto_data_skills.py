"""Tests for crypto data/alert/collect oskills."""

import pytest

from oskill.crypto_data_skills import (
    collect_cycle,
    collect_sectors,
    collect_sentiment,
    collect_write_event,
    compute_signal_quality,
    dex_cex_check,
    evaluate_stale,
    get_30d_returns_stddev,
    get_etf_inflow_7d,
    get_symbol_basis,
    get_symbol_daily_klines,
    get_symbol_max_pain,
    get_symbol_onchain_metrics,
    get_symbol_options_skew,
    proxy_check_and_notify,
    stale_check_and_notify,
    store_market,
)


@pytest.mark.asyncio
async def test_get_symbol_basis():
    r = await get_symbol_basis(spot_price=50000, perp_price=50100)
    assert r["basis"] == pytest.approx(0.002)
    assert r["available"] is True


@pytest.mark.asyncio
async def test_get_symbol_basis_zero_spot():
    r = await get_symbol_basis(spot_price=0, perp_price=50100)
    assert r["available"] is False


@pytest.mark.asyncio
async def test_get_symbol_daily_klines_cache():
    r = await get_symbol_daily_klines(cache_data=[{"close": 50000}])
    assert len(r) == 1


@pytest.mark.asyncio
async def test_get_symbol_daily_klines_fallback():
    r = await get_symbol_daily_klines(db_data=[{"close": 49000}])
    assert r[0]["close"] == 49000


@pytest.mark.asyncio
async def test_get_symbol_daily_klines_empty():
    r = await get_symbol_daily_klines()
    assert r == []


@pytest.mark.asyncio
async def test_get_symbol_onchain_metrics():
    r = await get_symbol_onchain_metrics(metrics={"mvrv": 2.1}, symbol="BTC")
    assert r["mvrv"] == 2.1
    assert r["symbol"] == "BTC"


@pytest.mark.asyncio
async def test_get_symbol_options_skew():
    r = await get_symbol_options_skew(iv_data={"put_25d_iv": 0.6, "call_25d_iv": 0.5})
    assert r == 10.0


@pytest.mark.asyncio
async def test_get_symbol_options_skew_none():
    r = await get_symbol_options_skew(iv_data={})
    assert r is None


@pytest.mark.asyncio
async def test_get_symbol_max_pain():
    r = await get_symbol_max_pain(strikes={"50000": 100, "55000": 200})
    assert r == 55000.0


@pytest.mark.asyncio
async def test_get_symbol_max_pain_empty():
    r = await get_symbol_max_pain(strikes={})
    assert r is None


@pytest.mark.asyncio
async def test_get_etf_inflow_7d():
    assert await get_etf_inflow_7d(environ_value=500.0) == 500.0
    assert await get_etf_inflow_7d(fallback_value=300.0) == 300.0
    assert await get_etf_inflow_7d() is None


@pytest.mark.asyncio
async def test_get_30d_returns_stddev():
    prices = [100 + i for i in range(31)]
    r = await get_30d_returns_stddev(prices=prices)
    assert r is not None and r > 0


@pytest.mark.asyncio
async def test_get_30d_returns_stddev_insufficient():
    r = await get_30d_returns_stddev(prices=[100, 101])
    assert r is None


@pytest.mark.asyncio
async def test_dex_cex_check_no_alert():
    r = await dex_cex_check(dex_price=50050, cex_price=50000)
    assert r["alert"] is False


@pytest.mark.asyncio
async def test_dex_cex_check_alert():
    r = await dex_cex_check(dex_price=51000, cex_price=50000, threshold=0.01)
    assert r["alert"] is True


@pytest.mark.asyncio
async def test_proxy_check_healthy():
    r = await proxy_check_and_notify(probe_results=[{"ok": True}, {"ok": True}])
    assert r["state"] == "healthy"


@pytest.mark.asyncio
async def test_proxy_check_degraded():
    r = await proxy_check_and_notify(probe_results=[{"ok": True}, {"ok": True}, {"ok": False}])
    assert r["state"] == "degraded"


@pytest.mark.asyncio
async def test_evaluate_stale():
    import time

    r = await evaluate_stale(
        sources={"fresh": time.time(), "stale": time.time() - 7200}, max_age_seconds=3600
    )
    assert "stale" in r
    assert "fresh" not in r


@pytest.mark.asyncio
async def test_stale_check_and_notify():
    import time

    r = await stale_check_and_notify(sources={"x": time.time() - 7200}, max_age_seconds=3600)
    assert r["alert_sent"] is True


@pytest.mark.asyncio
async def test_compute_signal_quality():
    r = await compute_signal_quality(
        predictions=[{"direction": "up"}, {"direction": "down"}], actuals=[1.0, -1.0]
    )
    assert r["hit_rate"] == 1.0


@pytest.mark.asyncio
async def test_compute_signal_quality_empty():
    r = await compute_signal_quality(predictions=[], actuals=[])
    assert r["sample_size"] == 0


@pytest.mark.asyncio
async def test_collect_cycle():
    r = await collect_cycle(klines=[{"close": 50000}], month=10)
    assert r["month"] == 10


@pytest.mark.asyncio
async def test_collect_sectors():
    r = await collect_sectors(btc_dom=55.0, eth_btc=0.05)
    assert r["btc_dominance"] == 55.0


@pytest.mark.asyncio
async def test_collect_sentiment():
    r = await collect_sentiment(fgi=72, stablecoin_mcap=150e9)
    assert r["fear_greed"] == 72


@pytest.mark.asyncio
async def test_store_market():
    r = await store_market(snapshots=[{"symbol": "BTC", "price": 50000}])
    assert r == 1


@pytest.mark.asyncio
async def test_collect_write_event():
    r = await collect_write_event(event_type="earnings", data={"title": "AAPL"})
    assert r == "ok"
