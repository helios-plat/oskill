"""Tests for crypto fusion scorer oskills."""

from oskill.crypto_fusion_scorers import (
    derivatives_score,
    flow_score,
    macro_score,
    onchain_score,
    sentiment_score,
    support_resistance_score,
    trend_score,
)


class TestTrendScore:
    def test_basic(self):
        r = trend_score(ma200_score=0.5, ma50_slope_score=0.3, ma_arrangement_score=0.8)
        assert -100 <= r["value"] <= 100
        assert len(r["contributors"]) >= 3

    def test_with_cross_asset(self):
        r = trend_score(
            ma200_score=0.5,
            ma50_slope_score=0.3,
            ma_arrangement_score=0.8,
            cross_asset_signal={"available": True, "value": 1.0},
        )
        assert (
            r["value"]
            != trend_score(ma200_score=0.5, ma50_slope_score=0.3, ma_arrangement_score=0.8)["value"]
        )

    def test_all_negative(self):
        r = trend_score(ma200_score=-1.0, ma50_slope_score=-1.0, ma_arrangement_score=-1.0)
        assert r["value"] < 0

    def test_all_zero(self):
        r = trend_score(ma200_score=0, ma50_slope_score=0, ma_arrangement_score=0)
        assert r["value"] == 0


class TestFlowScore:
    def test_basic(self):
        r = flow_score(stablecoin_score=0.3, etf_score=0.5, cex_balance_score=-0.2)
        assert -100 <= r["value"] <= 100

    def test_with_event(self):
        r = flow_score(
            stablecoin_score=0.3,
            etf_score=0.5,
            cex_balance_score=0.2,
            stablecoin_event={"available": True, "value": -1.0, "signal": "burn"},
        )
        assert (
            r["value"]
            < flow_score(stablecoin_score=0.3, etf_score=0.5, cex_balance_score=0.2)["value"]
        )

    def test_weight_modifier(self):
        r1 = flow_score(
            stablecoin_score=0, etf_score=1.0, cex_balance_score=0, etf_weight_modifier=1.0
        )
        r2 = flow_score(
            stablecoin_score=0, etf_score=1.0, cex_balance_score=0, etf_weight_modifier=0.3
        )
        assert r1["value"] >= r2["value"]


class TestSentimentScore:
    def test_basic(self):
        r = sentiment_score(funding_rate_score=0.2, basis_score=-0.1)
        assert -100 <= r["value"] <= 100

    def test_with_fgi(self):
        r = sentiment_score(funding_rate_score=0, basis_score=0, fear_greed_index=80)
        assert r["value"] > 0

    def test_extreme_fear(self):
        r = sentiment_score(funding_rate_score=0, basis_score=0, fear_greed_index=10)
        assert r["value"] < 0


class TestOnchainScore:
    def test_basic(self):
        r = onchain_score(mvrv_score=0.5, active_addr_score=0.2, lth_score=0.1)
        assert r["value"] > 0

    def test_all_negative(self):
        r = onchain_score(mvrv_score=-0.5, active_addr_score=-0.3, lth_score=-0.2)
        assert r["value"] < 0


class TestDerivativesScore:
    def test_basic(self):
        r = derivatives_score(options_skew_score=0.3, max_pain_score=-0.2, oi_change_score=0.5)
        assert -100 <= r["value"] <= 100

    def test_with_funding(self):
        r = derivatives_score(
            options_skew_score=0, max_pain_score=0, oi_change_score=0, funding_rate_score=1.0
        )
        assert r["value"] > 0


class TestMacroScore:
    def test_basic(self):
        r = macro_score(indicators={"dxy": -0.5, "vix": 1.2, "sp500": 0.3})
        assert -100 <= r["value"] <= 100
        assert r["confidence"] > 0

    def test_empty(self):
        r = macro_score(indicators={})
        assert r["value"] == 0
        assert r["confidence"] == 0.0

    def test_single_indicator(self):
        r = macro_score(indicators={"sp500": 2.0})
        assert r["value"] > 0


class TestSupportResistanceScore:
    def test_basic(self):
        r = support_resistance_score(resistance_score=-0.3, support_score=0.5, vpvr_score=0.2)
        assert -100 <= r["value"] <= 100

    def test_all_positive(self):
        r = support_resistance_score(resistance_score=1.0, support_score=1.0, vpvr_score=1.0)
        assert r["value"] == 100
