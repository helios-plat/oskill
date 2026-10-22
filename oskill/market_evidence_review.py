"""Compose pure evidence-quality primitives into an explainable research review.

This workflow is advisory only. It evaluates supplied evidence records; it does
not fetch data, generate trading signals, or place/modify/cancel orders.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from oprim.market_evidence_quality import detect_claim_conflicts, score_evidence_source

_MAX_SOURCES = 500
_MAX_CLAIMS = 1_000


def _record_key(source: Mapping[str, Any]) -> str:
    explicit_hash = source.get("content_sha256") or source.get("payload_sha256")
    if isinstance(explicit_hash, str) and len(explicit_hash) == 64:
        return f"sha256:{explicit_hash.lower()}"
    uri = source.get("source_uri") or source.get("url")
    if isinstance(uri, str) and uri.strip():
        parts = urlsplit(uri.strip())
        if parts.scheme.lower() in {"https", "http"} and parts.hostname:
            host = parts.hostname.lower()
            port = parts.port
            if port and not ((parts.scheme.lower() == "https" and port == 443) or (parts.scheme.lower() == "http" and port == 80)):
                host = f"{host}:{port}"
            canonical_uri = f"{parts.scheme.lower()}://{host}{parts.path or '/'}"
            if parts.query:
                canonical_uri += f"?{parts.query}"
            return f"uri:{canonical_uri}"
    try:
        canonical = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError):
        canonical = repr(sorted((str(k), repr(v)) for k, v in source.items()))
    return "record:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def review_market_evidence(
    input_data: dict[str, Any],
    *,
    now_utc: datetime | None = None,
    stale_after_hours: float = 24.0,
    numeric_tolerance: float = 0.0,
) -> dict[str, Any]:
    """Review source quality and contradictory claims with deterministic output.

    Args:
        input_data: Mapping-like dict with bounded ``sources`` and ``claims`` lists.
        now_utc: Optional timezone-aware clock for deterministic tests/replays.
        stale_after_hours: Freshness window used by oprim's explainable scorer.
        numeric_tolerance: Maximum numeric disagreement tolerated for like-for-like
            claims with the same subject, predicate, and unit.

    Returns a summary, per-source assessments, conflicts, and independent-source
    counts. A quality score is only a heuristic index, never a probability that a
    statement is true. Missing or malformed provenance is not silently promoted.
    """
    if not isinstance(input_data, dict):
        raise ValueError("input_data must be a dict")
    raw_sources = input_data.get("sources", [])
    raw_claims = input_data.get("claims", [])
    if not isinstance(raw_sources, list):
        raise ValueError("sources must be a list")
    if not isinstance(raw_claims, list):
        raise ValueError("claims must be a list")
    if len(raw_sources) > _MAX_SOURCES:
        raise ValueError(f"sources exceeds the {_MAX_SOURCES}-record limit")
    if len(raw_claims) > _MAX_CLAIMS:
        raise ValueError(f"claims exceeds the {_MAX_CLAIMS}-claim limit")

    source_assessments: list[dict[str, Any]] = []
    known_source_ids: set[str] = set()
    source_status_by_id: dict[str, str] = {}
    seen_keys: set[str] = set()
    duplicate_count = 0
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, dict):
            raise ValueError(f"source at index {index} must be a dict")
        source = dict(raw_source)
        source_id = str(source.get("source_id") or source.get("evidence_id") or f"source-{index + 1}").strip()
        if not source_id:
            source_id = f"source-{index + 1}"
        known_source_ids.add(source_id)
        if isinstance(source.get("evidence_id"), str) and source["evidence_id"].strip():
            known_source_ids.add(source["evidence_id"].strip())
        identity = _record_key(source)
        duplicate = identity in seen_keys
        seen_keys.add(identity)
        assessment = score_evidence_source(
            source,
            now_utc=now_utc,
            stale_after_hours=stale_after_hours,
        )
        source_status_by_id[source_id] = assessment.get("status", "unverified")
        if isinstance(source.get("evidence_id"), str) and source["evidence_id"].strip():
            source_status_by_id[source["evidence_id"].strip()] = assessment.get("status", "unverified")
        source_assessments.append({
            "source_id": source_id,
            "source_uri": source.get("source_uri") or source.get("url"),
            **assessment,
            "duplicate_content_or_uri": duplicate,
            "independent_support": not duplicate and assessment.get("status") == "current" and bool(assessment.get("score", 0)),
        })
        if duplicate:
            duplicate_count += 1

    # Validate every claim's shape first, then only compare claims whose source
    # references resolve to a supplied provenance record. Orphan claims remain
    # visible and cannot be promoted to supported merely because values agree.
    detect_claim_conflicts(raw_claims, numeric_tolerance=numeric_tolerance)
    linked_claims = [
        claim for claim in raw_claims
        if str(claim.get("source_id", "")).strip() in known_source_ids
    ]
    orphan_claims = [
        claim for claim in raw_claims
        if str(claim.get("source_id", "")).strip() not in known_source_ids
    ]
    conflicts = detect_claim_conflicts(linked_claims, numeric_tolerance=numeric_tolerance)
    conflict_keys = {
        (item["subject"].strip().casefold(), item["predicate"].strip().casefold(), item.get("unit", "").strip().casefold())
        for item in conflicts
    }
    claim_audits = []
    for claim in raw_claims:
        source_id = str(claim["source_id"]).strip()
        key = (str(claim["subject"]).strip().casefold(), str(claim["predicate"]).strip().casefold(), str(claim.get("unit", "")).strip().casefold())
        source_status = source_status_by_id.get(source_id)
        if source_status is None:
            claim_status = "unverified"
            reason = "source_id_not_found"
        elif key in conflict_keys:
            claim_status = "conflict"
            reason = "peer_claims_disagree"
        elif source_status != "current":
            claim_status = "unverified"
            reason = f"source_{source_status}"
        else:
            claim_status = "supported_by_current_source"
            reason = "source_link_resolved"
        claim_audits.append({
            "subject": str(claim["subject"]).strip(),
            "predicate": str(claim["predicate"]).strip(),
            "unit": str(claim.get("unit", "")).strip(),
            "source_id": source_id,
            "status": claim_status,
            "reason": reason,
        })

    unique_current = sum(1 for row in source_assessments if row["independent_support"])
    stale_count = sum(1 for row in source_assessments if row.get("status") == "stale")
    unverified_count = sum(1 for row in source_assessments if row.get("status") == "unverified")
    unverified_claim_count = sum(1 for row in claim_audits if row["status"] == "unverified")

    if conflicts:
        overall_status = "conflict"
    elif not source_assessments or unique_current == 0:
        overall_status = "unverified"
    elif unverified_claim_count:
        overall_status = "reviewed_with_unverified_claims"
    elif stale_count or unverified_count:
        overall_status = "reviewed_with_stale_or_unverified_sources"
    else:
        overall_status = "reviewed"

    # Stable sort makes review output and downstream fingerprints reproducible.
    source_assessments.sort(key=lambda row: (
        row["status"] != "current",
        -float(row.get("score", 0.0)),
        str(row.get("source_uri") or ""),
        row["source_id"],
    ))
    return {
        "status": overall_status,
        "summary": {
            "source_count": len(source_assessments),
            "independent_current_source_count": unique_current,
            "stale_source_count": stale_count,
            "unverified_source_count": unverified_count,
            "duplicate_source_count": duplicate_count,
            "claim_count": len(raw_claims),
            "linked_claim_count": len(linked_claims),
            "orphan_claim_count": len(orphan_claims),
            "unverified_claim_count": unverified_claim_count,
            "conflict_count": len(conflicts),
            "quality_scores_are_probabilities": False,
        },
        "sources": source_assessments,
        "claims": claim_audits,
        "orphan_claims": [
            {"subject": str(claim["subject"]).strip(), "predicate": str(claim["predicate"]).strip(), "source_id": str(claim["source_id"]).strip()}
            for claim in orphan_claims
        ],
        "conflicts": conflicts,
        "limitations": [
            "Source authority and freshness are heuristic indexes, not proof of truth.",
            "A review does not establish that sources are independent unless provenance/content identifiers distinguish them.",
            "No market data is fetched and no trading or order action is performed.",
        ],
    }
