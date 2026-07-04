"""Tests for oskill.alert_suppress (aegis DESIGN §3.2)."""

from __future__ import annotations

from oskill.alert_suppress import SuppressVerdict, alert_suppress


class TestAlertSuppress:
    def test_parent_down_suppresses(self):
        r = alert_suppress(
            alert={"name": "container_down", "parent": "sf1"},
            parent_states={"sf1": "down"},
        )
        assert isinstance(r, SuppressVerdict)
        assert r.suppressed is True
        assert "sf1" in r.reason

    def test_parent_up_not_suppressed(self):
        r = alert_suppress(
            alert={"parent": "sf1"},
            parent_states={"sf1": "up"},
        )
        assert r.suppressed is False
        assert r.reason is None

    def test_no_parent_key_not_suppressed(self):
        r = alert_suppress(alert={"name": "x"}, parent_states={"sf1": "down"})
        assert r.suppressed is False

    def test_unknown_parent_not_suppressed(self):
        r = alert_suppress(alert={"parent": "ghost"}, parent_states={"sf1": "down"})
        assert r.suppressed is False

    def test_custom_down_states_injectable(self):
        r = alert_suppress(
            alert={"parent": "sf1"},
            parent_states={"sf1": "draining"},
            down_states=["draining", "maintenance"],
        )
        assert r.suppressed is True

    def test_default_down_states_cover_common(self):
        for state in ("down", "unreachable", "dead", "offline"):
            r = alert_suppress(alert={"parent": "p"}, parent_states={"p": state})
            assert r.suppressed is True, state
