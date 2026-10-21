"""Tests for test_stability (Cypress 三机制 3O 内化)。"""

from __future__ import annotations

from oskill.test_stability import (
    ACTIONABLE_ANIMATION_STABLE,
    ACTIONABLE_VISIBLE,
    expect_eventually,
    retry_until,
    wait_actionable,
)

# ── 命令自动重试 (retry-ability) ─────────────────────────────────────


def test_retry_succeeds_eventually():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("not ready yet")
        return "done"

    result = retry_until(flaky, timeout=2.0, interval=0.01)
    assert result.ok is True
    assert result.value == "done"
    assert result.attempts == 3
    assert len(result.trace) == 2  # 两次失败轨迹


def test_retry_times_out():
    result = retry_until(lambda: None, timeout=0.2, interval=0.02)
    assert result.ok is False
    assert result.timed_out is True
    assert result.attempts > 1


def test_retry_error_exhausted():
    """异常型失败超出 error_retries → 立即失败 (非超时)。"""
    result = retry_until(
        lambda: (_ for _ in ()).throw(ValueError("boom")),
        error_retries=1,
        timeout=2.0,
        interval=0.01,
    )
    assert result.ok is False
    assert result.timed_out is False
    assert "boom" in result.error


def test_run_result_to_dict():
    result = retry_until(lambda: None, timeout=0.1, interval=0.01)
    data = result.to_dict()
    assert set(data) >= {"ok", "attempts", "trace", "timed_out"}


# ── Actionability 等待 ───────────────────────────────────────────────


def test_wait_actionable_all_pass():
    result = wait_actionable(lambda name: True, require=("visible", "clickable"))
    assert result.ok is True
    assert result.attempts == 1


def test_wait_actionable_eventually_stable():
    state = {"stable": False}
    calls = {"n": 0}

    def checker(name):
        calls["n"] += 1
        if name == ACTIONABLE_ANIMATION_STABLE:
            if calls["n"] >= 3:
                state["stable"] = True
            return state["stable"]
        return True

    result = wait_actionable(
        checker,
        require=(ACTIONABLE_VISIBLE, ACTIONABLE_ANIMATION_STABLE),
        timeout=2.0,
        interval=0.01,
    )
    assert result.ok is True
    assert result.attempts >= 2  # 动画稳定需要轮询


def test_wait_actionable_timeout():
    result = wait_actionable(
        lambda name: False,
        require=("visible",),
        timeout=0.2,
        interval=0.02,
    )
    assert result.ok is False
    assert result.timed_out is True
    assert "visible" in result.error


# ── 断言轮询 (TDD) ──────────────────────────────────────────────────


def test_expect_eventually_converges():
    values = iter([1, 2, 3])
    target = 3

    def assertion():
        value = next(values)
        assert value == target, f"got {value}"

    result = expect_eventually(assertion, timeout=2.0, interval=0.01)
    assert result.ok is True
    assert result.attempts == 3


def test_expect_eventually_times_out():
    def assertion():
        assert 1 == 2, "1 != 2"

    result = expect_eventually(assertion, timeout=0.2, interval=0.02)
    assert result.ok is False
    assert result.timed_out is True
    assert "1 != 2" in result.error


def test_expect_passes_first_try():
    result = expect_eventually(lambda: True, timeout=1.0)
    assert result.ok is True
    assert result.attempts == 1
