"""oskill.spec_execute — 可执行 Spec 技能 (spec-kit 3O 内化)。

流程: parse → validate → 拆任务 → 驱动实现 (caller 注入) → 验收核对 (test_runner) → 报告。

预设 (presets): scaffold / lean / self-test / architecture — 对齐 spec-kit presets。
零 veya 反向依赖: 实现调用与测试执行由装配层注入。
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from oprim._spec_parse import parse_spec, validate_spec

# ── 预设 (spec-kit presets 对齐) ─────────────────────────────────────

PRESETS: dict[str, str] = {
    "scaffold": """## 目标
搭建 {{project}} 的基础脚手架: 目录结构、入口、最小可运行闭环。

## 验收标准
- 项目可启动 (入口命令无报错)
- 目录结构与约定一致
- README 说明运行方式

## 约束
- 不引入未必要的外部依赖
- 保持最小实现

## 测试门
- 启动冒烟通过
""",
    "lean": """## 目标
以最小改动实现 {{feature}}: 只做必要变更, 不重构无关代码。

## 验收标准
- 功能按描述可用
- 改动 diff 最小可审查

## 约束
- 不触碰无关模块
- 保持既有代码风格

## 测试门
- 相关测试通过
""",
    "self-test": """## 目标
为 {{module}} 补充测试: 覆盖主路径与关键边界。

## 验收标准
- 新增测试通过
- 关键分支覆盖

## 约束
- 不改动被测代码行为

## 测试门
- pytest 全绿
""",
    "architecture": """## 目标
按 {{pattern}} 重构 {{module}}: 分层清晰、依赖方向正确。

## 验收标准
- 依赖方向单向
- 模块职责单一

## 约束
- 行为不回归

## 测试门
- 全量测试通过
""",
}


def render_preset(name: str, variables: dict[str, str] | None = None) -> str:
    """预设 spec 渲染 ({{var}} 占位符替换)。"""
    if name not in PRESETS:
        raise ValueError(f"未知预设: {name}; 可选 {sorted(PRESETS)}")
    text = PRESETS[name]
    for key, value in (variables or {}).items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


class SpecExecutor:
    """可执行 Spec: 校验 → 拆任务 → 实现 → 验收。"""

    def __init__(self, audit_path: str = "") -> None:
        self._audit = Path(audit_path or Path.home() / ".veya" / "audit" / "spec.jsonl")

    def _audit_write(self, entry: dict[str, Any]) -> None:
        try:
            self._audit.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    async def execute(
        self,
        spec_text: str,
        *,
        implementer: Callable[[str, str], Awaitable[dict[str, Any]]],
        test_runner: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        splitter: Callable[[str], list[str]] | None = None,
    ) -> dict[str, Any]:
        """执行 spec: 解析 → 校验 → 拆任务 → 逐任务实现 → 验收核对。

        Args:
            spec_text: markdown spec (章节: 目标/验收标准/约束/测试门)
            implementer: (task_text, task_index) -> {"ok", "output"}
            test_runner: () -> {"ok", "output"} (测试门执行)
            splitter: 任务拆解函数 (缺省按验收标准条目)
        """
        spec = parse_spec(spec_text)
        check = validate_spec(spec)
        if not check["ok"]:
            return {"ok": False, "status": "invalid_spec",
                    "missing": check["missing"], "spec": spec}

        # 任务拆解: 缺省按验收标准条目
        if splitter is not None:
            tasks = splitter(str(spec.get("goal", ""))) or spec["acceptance"]
        else:
            tasks = spec["acceptance"] or [spec["goal"]]

        results: list[dict[str, Any]] = []
        for i, task in enumerate(tasks):
            try:
                r = await implementer(task, i)
            except Exception as e:  # noqa: BLE001
                r = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
            results.append({"task": task[:200], "ok": bool(r.get("ok")),
                            "output": str(r.get("output", ""))[:500],
                            "error": str(r.get("error", ""))[:300]})

        # 验收核对 (测试门)
        gate: dict[str, Any] = {"ok": None, "output": ""}
        if test_runner is not None:
            try:
                gate = await test_runner()
            except Exception as e:  # noqa: BLE001
                gate = {"ok": False, "output": f"{type(e).__name__}: {e}"[:300]}

        accepted = all(r["ok"] for r in results) and (gate["ok"] is not False)
        report = {
            "ok": accepted,
            "status": "accepted" if accepted else "needs_work",
            "tasks": len(tasks),
            "results": results,
            "test_gate": gate,
            "spec_id": f"spec_{uuid.uuid4().hex[:10]}",
            "ts": time.time(),
        }
        self._audit_write(report)
        return report


spec_executor = SpecExecutor()


__all__ = ["PRESETS", "SpecExecutor", "spec_executor", "render_preset"]
