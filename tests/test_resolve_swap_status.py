"""Tests for oskill.resolve_swap_status."""

from __future__ import annotations

import pytest

from oskill._resolve_swap_status import resolve_swap_status


class TestResolveSwapStatus:
    def test_empty_events_is_pending(self):
        assert resolve_swap_status([]) == "pending"

    def test_last_event_wins(self):
        events = [{"type": "pending"}, {"type": "processing"}]
        assert resolve_swap_status(events) == "processing"

    def test_completed(self):
        events = [{"type": "processing"}, {"type": "completed"}]
        assert resolve_swap_status(events) == "completed"

    def test_requires_action(self):
        events = [{"type": "processing"}, {"type": "requires_action"}]
        assert resolve_swap_status(events) == "requires_action"

    def test_canceled(self):
        events = [{"type": "pending"}, {"type": "canceled"}]
        assert resolve_swap_status(events) == "canceled"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown event type"):
            resolve_swap_status([{"type": "bogus"}])
