"""Tests for oskill.resolve_claim_status."""

from __future__ import annotations

import pytest

from oskill._resolve_claim_status import resolve_claim_status


class TestResolveClaimStatus:
    def test_empty_events_is_pending(self):
        assert resolve_claim_status([]) == "pending"

    def test_last_event_wins(self):
        events = [{"type": "pending"}, {"type": "approved"}]
        assert resolve_claim_status(events) == "approved"

    def test_rejected(self):
        events = [{"type": "pending"}, {"type": "rejected"}]
        assert resolve_claim_status(events) == "rejected"

    def test_canceled(self):
        events = [{"type": "pending"}, {"type": "canceled"}]
        assert resolve_claim_status(events) == "canceled"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown event type"):
            resolve_claim_status([{"type": "bogus"}])
