"""detect_trajectory_loop is a pure cycle check."""

from __future__ import annotations

from oskill.loop_detection import detect_trajectory_loop


def test_abab_is_a_loop() -> None:
    assert detect_trajectory_loop(["A", "B", "A", "B"]) is True


def test_aaaa_is_a_loop() -> None:
    assert detect_trajectory_loop(["A", "A", "A", "A"]) is True


def test_short_history_is_not_a_loop() -> None:
    assert detect_trajectory_loop(["A", "B"]) is False


def test_abcd_is_not_a_loop() -> None:
    assert detect_trajectory_loop(["A", "B", "C", "D"]) is False


def test_abcabc_detected_with_larger_window() -> None:
    assert detect_trajectory_loop(["A", "B", "C", "A", "B", "C"], window_size=6) is True
