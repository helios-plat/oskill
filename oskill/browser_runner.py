"""oskill.browser_runner — 浏览器驱动测试 runner (Cypress runner 机制 3O 内化)。

浏览器 E2E 测试执行器 (playwright 可选驱动, 缺失时结构化降级):
  * **BrowserCommands** — visit/click/type/assert_text/assert_visible/screenshot;
  * **BrowserRunner** — 驱动抽象 (playwright 注入): 命令执行 → 结果收集 →
    失败截图; 无 playwright 时返回 not_available 结构化错误;
  * **run_browser_test** — 测试场景执行 (命令序列 + 断言) → 用例结果
    (与 test_report 契约组合)。
零 veya 反向依赖: playwright 可选 (缺失降级); 命令实现注入。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

DriverFn = Callable[[str, dict[str, Any]], Any]
"""驱动命令: (command, args) → 结果 (playwright 封装注入)。"""


@dataclass
class BrowserStepResult:
    """一个浏览器步骤的结果。"""

    command: str
    ok: bool
    detail: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"command": self.command, "ok": self.ok, "detail": self.detail[:200]}


class BrowserRunner:
    """浏览器测试执行器 (驱动注入)。"""

    def __init__(
        self, driver: DriverFn | None = None, *, screenshot_dir: str | None = None
    ) -> None:
        self.driver = driver
        self.screenshot_dir = screenshot_dir

    def available(self) -> bool:
        """驱动是否可用 (playwright 注入)。"""
        return self.driver is not None

    def run_steps(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """执行命令序列 (Cypress command 语义)。

        Args:
            steps: [{command, args?, screenshot?}] — visit/click/type/
                assert_text/assert_visible/screenshot。

        Returns:
            {ok, results, failed_at, screenshots}。
        """
        if self.driver is None:
            return {
                "ok": False,
                "results": [],
                "failed_at": None,
                "screenshots": [],
                "error": "driver 未注入 (playwright 缺失?)",
            }
        results: list[BrowserStepResult] = []
        screenshots: list[str] = []
        failed_at: str | None = None
        for step in steps:
            command = step.get("command", "")
            args = step.get("args", {})
            start = time.monotonic()
            try:
                result = self.driver(command, args)
                ok = bool(result)
            except Exception as exc:  # noqa: BLE001
                ok = False
                result = f"{exc.__class__.__name__}: {exc}"
            step_result = BrowserStepResult(
                command=command,
                ok=ok,
                detail=str(result)[:200],
                duration_ms=(time.monotonic() - start) * 1000,
            )
            results.append(step_result)
            if not ok:
                failed_at = command
                if step.get("screenshot") and self.screenshot_dir:
                    shots = self._capture(step.get("screenshot"))
                    screenshots.extend(shots)
                break
            if command == "screenshot":
                screenshots.append(str(result))
        return {
            "ok": failed_at is None,
            "results": [r.to_dict() for r in results],
            "failed_at": failed_at,
            "screenshots": screenshots,
            "error": None if failed_at is None else f"failed at {failed_at}",
        }

    def _capture(self, name: str) -> list[str]:
        """失败截图 (驱动提供 screenshot 命令)。"""
        if self.driver is None:
            return []
        try:
            path = f"{self.screenshot_dir}/{name}_{int(time.time())}.png"
            result = self.driver("screenshot", {"path": path})
            return [str(result)]
        except Exception:  # noqa: BLE001
            return []


def run_browser_test(
    name: str,
    steps: list[dict[str, Any]],
    *,
    driver: DriverFn,
    screenshot_dir: str | None = None,
) -> dict[str, Any]:
    """执行一次浏览器测试 (命令序列 + 截图) → 结构化结果。

    Args:
        name: 测试名。
        steps: 命令序列。
        driver: 驱动命令实现。
        screenshot_dir: 截图目录。

    Returns:
        {name, ok, results, failed_at, screenshots} (可转 test_report 用例)。
    """
    runner = BrowserRunner(driver, screenshot_dir=screenshot_dir)
    result = runner.run_steps(steps)
    result["name"] = name
    return result


# ── Playwright 驱动工厂 (可选依赖) ─────────────────────────────────


def playwright_driver(base_url: str = "") -> DriverFn:
    """构造 playwright 驱动 (首次调用时导入, 缺失抛 ImportError)。"""

    def driver(command: str, args: dict[str, Any]) -> Any:
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError("playwright 未安装; pip install playwright") from exc
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                if command == "visit":
                    page.goto(base_url + str(args.get("url", "")))
                    return True
                if command == "click":
                    page.click(args.get("selector", ""))
                    return True
                if command == "type":
                    page.fill(args.get("selector", ""), args.get("text", ""))
                    return True
                if command == "assert_text":
                    page.wait_for_selector(args.get("selector", ""))
                    text = page.inner_text(args.get("selector", ""))
                    return args.get("contains", "") in text
                if command == "assert_visible":
                    page.wait_for_selector(args.get("selector", ""))
                    return page.is_visible(args.get("selector", ""))
                if command == "screenshot":
                    path = args.get("path", "screenshot.png")
                    page.screenshot(path=path)
                    return path
                raise ValueError(f"unknown command: {command}")
            finally:
                browser.close()

    return driver


__all__ = ["BrowserRunner", "BrowserStepResult", "playwright_driver", "run_browser_test"]
