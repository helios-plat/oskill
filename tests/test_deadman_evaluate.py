"""Tests for oskill.deadman_evaluate (aegis DESIGN §3.1/§6)."""

from __future__ import annotations

from datetime import datetime, timedelta

from oskill.deadman_evaluate import DeadmanVerdict, deadman_evaluate

_NOW = datetime(2026, 7, 4, 12, 0, 0)


class TestDeadmanEvaluate:
    def test_fresh_not_silent(self):
        r = deadman_evaluate(
            subject="cron.hevi",
            last_seen=_NOW - timedelta(seconds=30),
            expected_interval_seconds=60,
            now=_NOW,
        )
        assert isinstance(r, DeadmanVerdict)
        assert r.ever_seen is True
        assert r.silent is False
        assert r.overdue_seconds < 0

    def test_overdue_silent(self):
        r = deadman_evaluate(
            subject="cron.hevi",
            last_seen=_NOW - timedelta(seconds=200),
            expected_interval_seconds=60,
            now=_NOW,
        )
        assert r.silent is True
        assert r.overdue_seconds > 0  # 200 - 60 = 140s 超期

    def test_never_seen_silent(self):
        r = deadman_evaluate(
            subject="collector.helivex",
            last_seen=None,
            expected_interval_seconds=60,
            now=_NOW,
        )
        assert r.ever_seen is False
        assert r.silent is True
        assert r.overdue_seconds == 0.0

    def test_grace_extends_deadline(self):
        # 70s 前 + 60s 间隔 = 超期 10s,但 grace=30s → 未静默
        r = deadman_evaluate(
            subject="x",
            last_seen=_NOW - timedelta(seconds=70),
            expected_interval_seconds=60,
            now=_NOW,
            grace_seconds=30,
        )
        assert r.silent is False

    def test_exactly_at_deadline_not_silent(self):
        r = deadman_evaluate(
            subject="x",
            last_seen=_NOW - timedelta(seconds=60),
            expected_interval_seconds=60,
            now=_NOW,
        )
        assert r.overdue_seconds == 0.0
        assert r.silent is False  # overdue > 0 严格,恰好到点不算静默
