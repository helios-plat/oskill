from __future__ import annotations

from datetime import datetime, timezone

import pytest

from oskill.market_evidence_review import review_market_evidence

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


def _source(source_id="exchange-a", **kwargs):
    data = {
        "source_id": source_id,
        "source_type": "primary_exchange",
        "source_uri": f"https://exchange.example/data/{source_id}",
        "retrieved_at_utc": "2026-10-22T11:00:00Z",
        "content_sha256": (source_id.encode().hex() * 64)[:64],
        "directness": 1.0,
    }
    data.update(kwargs)
    return data


def test_current_primary_source_reviews_without_promoting_score_to_truth():
    result = review_market_evidence({"sources": [_source()], "claims": []}, now_utc=NOW)
    assert result["status"] == "reviewed"
    assert result["summary"]["independent_current_source_count"] == 1
    assert result["summary"]["quality_scores_are_probabilities"] is False


def test_empty_evidence_is_unverified():
    result = review_market_evidence({}, now_utc=NOW)
    assert result["status"] == "unverified"
    assert result["summary"]["independent_current_source_count"] == 0


def test_identical_content_hash_does_not_count_twice():
    first = _source("a", content_sha256="a" * 64)
    second = _source("b", content_sha256="a" * 64, source_uri="https://mirror.example/data")
    result = review_market_evidence({"sources": [first, second]}, now_utc=NOW)
    assert result["summary"]["duplicate_source_count"] == 1
    assert result["summary"]["independent_current_source_count"] == 1


def test_identical_uri_does_not_count_twice():
    first = _source("a", source_uri="HTTPS://EXCHANGE.EXAMPLE:443/ohlcv#section", content_sha256=None)
    second = _source("b", source_uri="https://exchange.example/ohlcv", content_sha256=None)
    result = review_market_evidence({"sources": [first, second]}, now_utc=NOW)
    assert result["summary"]["duplicate_source_count"] == 1


def test_stale_source_produces_reviewed_with_stale_status():
    result = review_market_evidence({"sources": [_source(retrieved_at_utc="2026-10-19T00:00:00Z")]}, now_utc=NOW)
    assert result["status"] == "unverified"
    assert result["summary"]["stale_source_count"] == 1


def test_bad_provenance_stays_unverified():
    result = review_market_evidence({"sources": [{"source_id": "bad"}]}, now_utc=NOW)
    assert result["status"] == "unverified"
    assert result["sources"][0]["status"] == "unverified"
    assert result["sources"][0]["score"] == 0


def test_error_source_stays_unverified():
    result = review_market_evidence({"sources": [_source(error="upstream timeout")]}, now_utc=NOW)
    assert result["summary"]["unverified_source_count"] == 1
    assert result["status"] == "unverified"


def test_numeric_claim_conflict_dominates_overall_status():
    claims = [
        {"subject": "BTC-USDT", "predicate": "close", "unit": "USDT", "value": "100", "source_id": "a"},
        {"subject": "btc-usdt", "predicate": "close", "unit": "usdt", "value": "102", "source_id": "b"},
    ]
    result = review_market_evidence({"sources": [_source("a"), _source("b")], "claims": claims}, now_utc=NOW)
    assert result["status"] == "conflict"
    assert result["summary"]["conflict_count"] == 1
    assert result["conflicts"][0]["source_ids"] == ["a", "b"]


def test_claim_values_within_tolerance_are_reviewed():
    claims = [
        {"subject": "A", "predicate": "close", "value": 1.0, "source_id": "a"},
        {"subject": "a", "predicate": "close", "value": 1.01, "source_id": "b"},
    ]
    result = review_market_evidence({"sources": [_source("a"), _source("b")], "claims": claims}, now_utc=NOW, numeric_tolerance=0.02)
    assert result["status"] == "reviewed"
    assert result["summary"]["conflict_count"] == 0


def test_output_source_order_is_deterministic():
    inputs = {"sources": [_source("b", content_sha256="b" * 64), _source("a", content_sha256="a" * 64)]}
    first = review_market_evidence(inputs, now_utc=NOW)
    second = review_market_evidence(inputs, now_utc=NOW)
    assert first == second


@pytest.mark.parametrize("input_data", [None, [], {"sources": {}}, {"claims": {}}, {"sources": [None]}])
def test_invalid_input_shapes_fail_closed(input_data):
    with pytest.raises(ValueError):
        review_market_evidence(input_data, now_utc=NOW)


def test_sources_and_claims_are_bounded():
    with pytest.raises(ValueError, match="500-record"):
        review_market_evidence({"sources": [{}] * 501}, now_utc=NOW)
    with pytest.raises(ValueError, match="1000-claim"):
        review_market_evidence({"claims": [{}] * 1001}, now_utc=NOW)


def test_review_never_claims_to_submit_orders():
    result = review_market_evidence({"sources": [_source()]}, now_utc=NOW)
    assert "No market data is fetched and no trading or order action is performed." in result["limitations"]


def test_claim_with_unknown_source_is_not_promoted_to_supported():
    claim = {"subject": "BTC-USDT", "predicate": "close", "value": 10, "source_id": "missing"}
    result = review_market_evidence({"sources": [_source()], "claims": [claim]}, now_utc=NOW)
    assert result["status"] == "reviewed_with_unverified_claims"
    assert result["summary"]["orphan_claim_count"] == 1
    assert result["claims"][0]["status"] == "unverified"
    assert result["claims"][0]["reason"] == "source_id_not_found"


def test_linked_claim_is_audited_with_source_id():
    claim = {"subject": "BTC-USDT", "predicate": "close", "value": 10, "source_id": "exchange-a"}
    result = review_market_evidence({"sources": [_source("exchange-a")], "claims": [claim]}, now_utc=NOW)
    assert result["claims"][0]["status"] == "supported_by_current_source"
    assert result["claims"][0]["source_id"] == "exchange-a"
