"""oskill.test_stability — 测试稳定性三机制 (Cypress 机制 3O 内化)。

让 E2E/时序不确定环境下的测试不 flaky:
  * **命令自动重试 (retry-ability)** — 操作失败自动重试直到超时, 带回退间隔
    与完整重试轨迹 (Cypress 灵魂: 默认 4s 超时);
  * **Actionability 等待** — 操作前确定性等待: 元素可见/可点/不遮挡/动画稳定
    才执行 (检查器注入, 满足才放行);
  * **断言轮询** — expect 自动重试: 断言在轮询中收敛 (TDD 语义), 非即时判定。
统一 RunResult (重试轨迹/超时判定/总耗时), 与 eval_suite/verity_check 同哲学。

零 veya 反向依赖: 检查器/操作函数由调用方注入; 纯确定性编排。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")

DEFAULT_TIMEOUT_S = 4.0
DEFAULT_INTERVAL_S = 0.1


@dataclass
class RunResult:
    """一次重试执行的结果 (轨迹可审计)。

    Attributes:
        ok: 是否成功。
        value: 成功时的返回值。
        error: 最终错误 (失败时)。
        attempts: 尝试次数。
        trace: 每次尝试的错误摘要 (可审计/可解释)。
        elapsed: 总耗时秒数。
        timed_out: 是否超时失败。
    """

    ok: bool
    value: Any = None
    error: str = ""
    attempts: int = 0
    trace: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "attempts": self.attempts,
            "trace": self.trace,
            "elapsed": self.elapsed,
            "timed_out": self.timed_out,
            "error": self.error[:300],
        }


def retry_until(
    fn: Callable[[], T],
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    interval: float = DEFAULT_INTERVAL_S,
    label: str = "operation",
    error_retries: int | None = None,
) -> RunResult:
    """命令自动重试: 失败重试直到成功或超时 (Cypress retry-ability)。

    Args:
        fn: 待执行操作 (成功返回非 None 或抛异常; 调用方包装判定)。
        timeout: 总超时秒数 (默认 4s, Cypress 默认)。
        interval: 重试间隔秒数。
        label: 操作名 (轨迹可读)。
        error_retries: 异常型失败允许的额外尝试; None=不限制
            (重试到超时, Cypress 默认语义)。

    Returns:
        RunResult (ok/attempts/trace/timed_out)。

    Example:
        >>> r = retry_until(lambda: 1 if time.time() > 0 else 0)
        >>> r.ok
        True
    """
    start = time.monotonic()
    trace: list[str] = []
    attempts = 0
    last_error = ""
    consecutive_errors = 0
    while True:
        attempts += 1
        try:
            value = fn()
            if value is not None:
                return RunResult(
                    ok=True,
                    value=value,
                    attempts=attempts,
                    trace=trace,
                    elapsed=time.monotonic() - start,
                )
            last_error = f"{label}: returned None (falsy)"
        except Exception as exc:  # noqa: BLE001
            last_error = f"{label}: {exc.__class__.__name__}: {str(exc)[:120]}"
            consecutive_errors += 1
            if error_retries is not None and consecutive_errors > error_retries:
                trace.append(last_error)
                return RunResult(
                    ok=False,
                    error=last_error,
                    attempts=attempts,
                    trace=trace,
                    elapsed=time.monotonic() - start,
                    timed_out=False,
                )
        trace.append(last_error)
        if time.monotonic() - start >= timeout:
            return RunResult(
                ok=False,
                error=last_error,
                attempts=attempts,
                trace=trace,
                elapsed=time.monotonic() - start,
                timed_out=True,
            )
        time.sleep(interval)


# ── Actionability 等待 ───────────────────────────────────────────────

ACTIONABLE_VISIBLE = "visible"
ACTIONABLE_CLICKABLE = "clickable"
ACTIONABLE_NOT_COVERED = "not_covered"
ACTIONABLE_ANIMATION_STABLE = "animation_stable"
ACTIONABLE_CHECKS = (
    ACTIONABLE_VISIBLE,
    ACTIONABLE_CLICKABLE,
    ACTIONABLE_NOT_COVERED,
    ACTIONABLE_ANIMATION_STABLE,
)

Checker = Callable[[str], bool]
"""actionability 检查器: (检查名) → 是否通过 (注入 DOM 检查器)。"""


def wait_actionable(
    checker: Checker,
    *,
    require: tuple[str, ...] = ACTIONABLE_CHECKS,
    timeout: float = DEFAULT_TIMEOUT_S,
    interval: float = DEFAULT_INTERVAL_S,
) -> RunResult:
    """Actionability 等待: 所有要求检查通过才放行 (Cypress 操作前等待)。

    Args:
        checker: 检查器 (visible/clickable/not_covered/animation_stable)。
        require: 要求的检查子集。
        timeout: 总超时。
        interval: 轮询间隔。

    Returns:
        RunResult (ok 表示全部检查通过)。

    Example:
        >>> r = wait_actionable(lambda c: True, require=("visible",))
        >>> r.ok
        True
    """
    start = time.monotonic()
    trace: list[str] = []
    attempts = 0
    while True:
        attempts += 1
        pending = [name for name in require if not checker(name)]
        if not pending:
            return RunResult(
                ok=True, attempts=attempts, trace=trace, elapsed=time.monotonic() - start
            )
        trace.append(f"pending: {', '.join(pending)}")
        if time.monotonic() - start >= timeout:
            return RunResult(
                ok=False,
                error=f"actionability timeout: {', '.join(pending)}",
                attempts=attempts,
                trace=trace,
                elapsed=time.monotonic() - start,
                timed_out=True,
            )
        time.sleep(interval)


# ── 断言轮询 (TDD 语义) ──────────────────────────────────────────────


def expect_eventually(
    assertion: Callable[[], Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    interval: float = DEFAULT_INTERVAL_S,
    label: str = "assertion",
) -> RunResult:
    """断言自动重试: 断言在轮询中收敛 (Cypress expect retry)。

    Args:
        assertion: 断言函数 (通过返回/不抛; 失败抛 AssertionError)。
        timeout: 总超时。
        interval: 轮询间隔。
        label: 断言名。

    Returns:
        RunResult (ok 表示断言在超时前收敛)。

    Example:
        >>> r = expect_eventually(lambda: (_ for _ in ()).throw(AssertionError("x")))
        >>> r.ok is False
        True
    """
    start = time.monotonic()
    trace: list[str] = []
    attempts = 0
    while True:
        attempts += 1
        try:
            assertion()
            return RunResult(
                ok=True, attempts=attempts, trace=trace, elapsed=time.monotonic() - start
            )
        except AssertionError as exc:
            trace.append(f"{label}: {str(exc)[:120]}")
        if time.monotonic() - start >= timeout:
            return RunResult(
                ok=False,
                error=trace[-1] if trace else label,
                attempts=attempts,
                trace=trace,
                elapsed=time.monotonic() - start,
                timed_out=True,
            )
        time.sleep(interval)
