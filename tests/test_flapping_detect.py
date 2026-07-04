"""Tests for oskill.flapping_detect (aegis DESIGN §5.3)."""

from __future__ import annotations

from datetime import datetime, timedelta

from oskill.flapping_detect import FlapVerdict, flapping_detect

_NOW = datetime(2026, 7, 4, 12, 0, 0)


def _ago(minutes: int) -> datetime:
    return _NOW - timedelta(minutes=minutes)


class TestFlappingDetect:
    def test_two_in_window_is_flapping(self):
        r = flapping_detect(target="c1", heal_history=[_ago(5), _ago(20)], now=_NOW)
        assert isinstance(r, FlapVerdict)
        assert r.heals_in_window == 2
        assert r.is_flapping is True

    def test_one_in_window_not_flapping(self):
        r = flapping_detect(target="c1", heal_history=[_ago(5)], now=_NOW)
        assert r.heals_in_window == 1
        assert r.is_flapping is False

    def test_old_heals_excluded(self):
        r = flapping_detect(target="c1", heal_history=[_ago(5), _ago(40)], now=_NOW)
        assert r.heals_in_window == 1  # 40min 前超出 30min 窗口
        assert r.is_flapping is False

    def test_custom_threshold_injectable(self):
        r = flapping_detect(
            target="c1", heal_history=[_ago(1), _ago(2), _ago(3)], now=_NOW, threshold=3
        )
        assert r.threshold == 3
        assert r.is_flapping is True

    def test_custom_window_injectable(self):
        r = flapping_detect(target="c1", heal_history=[_ago(40)], now=_NOW, window_seconds=3600)
        assert r.window_seconds == 3600
        assert r.heals_in_window == 1

    def test_empty_history(self):
        r = flapping_detect(target="c1", heal_history=[], now=_NOW)
        assert r.heals_in_window == 0
        assert r.is_flapping is False
