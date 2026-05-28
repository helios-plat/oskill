"""Tests for crypto environ processor oskills."""

import pytest

from oskill.crypto_environ_processors import (
    derivatives_agg_compute,
    dex_truth_compute,
    dex_truth_dydx_compute,
    dex_truth_gmx_compute,
    etf_flow_compute,
    etf_flow_per_ticker_compute,
    exchange_netflow_compute,
    macro_environ_compute,
    onchain_aggregate_compute,
    options_environ_compute,
)


@pytest.mark.asyncio
async def test_derivatives_agg_basic():
    r = await derivatives_agg_compute(
        external_data={"oi": {"zscore": 1.5}, "funding": {"rate": 0.02}}
    )
    assert r["oi_zscore"] == 1.5
    assert r["funding_label"] == "long_crowded"


@pytest.mark.asyncio
async def test_derivatives_agg_empty():
    r = await derivatives_agg_compute(external_data={})
    assert r["available"] is False


@pytest.mark.asyncio
async def test_dex_truth_basic():
    r = await dex_truth_compute(external_data={"assets": [{"symbol": "BTC", "oi": 100}]})
    assert r["available"] is True
    assert "BTC" in r["heatmap"]


@pytest.mark.asyncio
async def test_dex_truth_empty():
    r = await dex_truth_compute(external_data={"assets": []})
    assert r["available"] is False


@pytest.mark.asyncio
async def test_dex_truth_dydx():
    r = await dex_truth_dydx_compute(external_data={"funding_1h": 0.001})
    assert r["funding_8h"] == pytest.approx(0.008)


@pytest.mark.asyncio
async def test_dex_truth_gmx():
    r = await dex_truth_gmx_compute(external_data={"long_oi": 100, "short_oi": 80})
    assert r["oi_skew"] == pytest.approx(0.1111, abs=0.001)


@pytest.mark.asyncio
async def test_dex_truth_gmx_zero():
    r = await dex_truth_gmx_compute(external_data={"long_oi": 0, "short_oi": 0})
    assert r["available"] is False


@pytest.mark.asyncio
async def test_etf_flow_basic():
    r = await etf_flow_compute(external_data={"flows": [100, -50, 200]})
    assert r["net_flow_7d"] == 250


@pytest.mark.asyncio
async def test_etf_flow_empty():
    r = await etf_flow_compute(external_data={"flows": []})
    assert r["available"] is False


@pytest.mark.asyncio
async def test_etf_flow_per_ticker():
    r = await etf_flow_per_ticker_compute(external_data={"tickers": {"IBIT": 100}})
    assert r["per_ticker"]["IBIT"] == 100


@pytest.mark.asyncio
async def test_macro_environ():
    r = await macro_environ_compute(external_data={"dxy": [104, 103, 105, 104.5]})
    assert "dxy_zscore" in r


@pytest.mark.asyncio
async def test_macro_environ_empty():
    r = await macro_environ_compute(external_data={})
    assert r["available"] is False


@pytest.mark.asyncio
async def test_onchain_aggregate():
    r = await onchain_aggregate_compute(external_data={"tvl": [100, 105], "stablecoin": [50, 52]})
    assert r["tvl_momentum"] == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_exchange_netflow():
    r = await exchange_netflow_compute(external_data={"BTC": {"ethereum": -100, "tron": -50}})
    assert r["flows"]["BTC"]["net"] == -150
    assert r["flows"]["BTC"]["bearish"] is True


@pytest.mark.asyncio
async def test_options_environ():
    r = await options_environ_compute(external_data={"iv_history": [0.5, 0.55, 0.6]})
    assert r["available"] is True
    assert r["iv_trend"] == "rising"


@pytest.mark.asyncio
async def test_options_environ_insufficient():
    r = await options_environ_compute(external_data={"iv_history": [0.5]})
    assert r["available"] is False
