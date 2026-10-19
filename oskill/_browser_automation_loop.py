"""oskill.browser_automation_loop — Web 页面元素定位与多步自动交互技能.

组合 oprim.browser_fetch_dom（抓 DOM）+ oprim.browser_click_element（点击），
按步骤脚本顺序执行并汇总每步观察。stateless：page 句柄经参数注入。

Example:
    >>> r = await browser_automation_loop(
    ...     page, steps=[
    ...         {"action": "goto", "url": "https://x"},
    ...         {"action": "click", "selector": "#go"},
    ...     ],
    ... )
    >>> r["steps_done"]
    2
"""

from __future__ import annotations

from typing import Any, Literal

from oprim import browser_click_element, browser_fetch_dom

from oskill._exceptions import OskillError

StepAction = Literal["goto", "fetch", "click"]


async def browser_automation_loop(
    page: Any,
    *,
    steps: list[dict[str, Any]],
    stop_on_error: bool = True,
    max_steps: int = 20,
) -> dict[str, Any]:
    """多步网页自动交互。

    Args:
        page: 页面句柄（obase.browser_runner.BrowserPageHandle 兼容协议）。
        steps: 步骤列表，每项 {"action": "goto"|"fetch"|"click", ...}：
            - goto:   {"url": str}
            - fetch:  {"screenshot": bool, "screenshot_path": str|None}
            - click:  {"selector": str}
        stop_on_error: 任一步失败是否立即终止。
        max_steps: 步骤数上限。

    Returns:
        {"status": "completed"|"stopped", "steps_done": int, "results": [dict]}

    Raises:
        OskillError: steps 为空 / 超限 / action 非法。
    """
    if not steps:
        raise OskillError("browser_automation_loop: steps must not be empty")
    if len(steps) > max_steps:
        raise OskillError(
            f"browser_automation_loop: {len(steps)} steps exceed max_steps={max_steps}"
        )
    if page is None:
        raise OskillError("browser_automation_loop: page handle required")


    results: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        action = step.get("action")
        try:
            if action == "goto":
                await page.goto(step["url"], timeout_ms=step.get("timeout_ms", 30_000))
                result = {"step_no": i, "action": "goto", "url": step["url"], "ok": True}
            elif action == "fetch":
                result = await browser_fetch_dom(
                    "about:blank",
                    browser=page,
                    screenshot=bool(step.get("screenshot", False)),
                    screenshot_path=step.get("screenshot_path"),
                )
                result = {"step_no": i, "action": "fetch", **result}
            elif action == "click":
                result = await browser_click_element(
                    step["selector"],
                    browser=page,
                    timeout_ms=step.get("timeout_ms", 10_000),
                )
                result = {"step_no": i, "action": "click", **result}
            else:
                raise OskillError(
                    f"browser_automation_loop: unknown action {action!r} "
                    f"(allowed: goto/fetch/click)"
                )
        except Exception as exc:  # noqa: BLE001
            result = {
                "step_no": i,
                "action": action,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            if stop_on_error:
                results.append(result)
                return {"status": "stopped", "steps_done": i + 1, "results": results}
        results.append(result)

    return {"status": "completed", "steps_done": len(results), "results": results}
