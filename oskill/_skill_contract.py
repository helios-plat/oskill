"""oskill.skill_contract — 技能契约 (Verify / Red-Flag / Rationalization)。Pure.

把 addyosmani/agent-skills 的"技能锚定于可验证工作流"范式内化为纯校验原语:
一个技能除了 name/description/parameters, 还可声明可选契约字段——

  * ``when_to_use``     触发条件 (何时该用这个技能);
  * ``verification``    完成的**证据**要求 (测试通过 / 构建输出 / 可观测断言);
  * ``red_flags``       出错的预警信号;
  * ``rationalizations`` 常见"偷懒借口 + 反驳", 防模型跳过关键步骤。

契约字段全部**可选** (向后兼容): 只有声明了才校验其结构。校验与渲染都是
纯函数 (无 I/O), 与 ``leaf_contract`` 同风格; veya 侧只装配 (解析 manifest →
校验 → 渲染进目录/披露块)。
"""

from __future__ import annotations

from typing import Any

# 技能契约扩展字段 (在 name/description/parameters 之外, 均可选)
CONTRACT_FIELDS = ("when_to_use", "verification", "red_flags", "rationalizations")


def validate_skill_contract(manifest: dict[str, Any]) -> list[str]:
    """校验技能 manifest。核心字段必填; 契约字段声明了才校验结构。

    返回错误消息列表 (空 = 合法)。纯函数, 供 SkillHub 加载期与技能开发工具复用,
    口径单一 (不在两处各写一套校验)。
    """
    manifest = manifest or {}
    name = str(manifest.get("name") or "").strip()
    label = name or "?"
    errors: list[str] = []

    # ── 核心契约 (与 SkillHub 既有校验同口径) ──
    if not name:
        errors.append("skill requires name")
    if not str(manifest.get("description") or "").strip():
        errors.append(f"skill '{label}' requires description")
    params = manifest.get("parameters")
    if not isinstance(params, dict) or "properties" not in params:
        errors.append(f"skill '{label}' requires parameters.properties")

    # ── 扩展契约 (可选; 声明即校验结构, 不声明零影响) ──
    for field in ("when_to_use", "verification", "red_flags"):
        if field in manifest and not _str_list(manifest.get(field)):
            errors.append(f"skill '{label}' {field} present but empty")

    rats = manifest.get("rationalizations")
    if rats is not None:
        if not isinstance(rats, list) or not rats:
            errors.append(f"skill '{label}' rationalizations must be a non-empty list")
        else:
            for index, item in enumerate(rats, start=1):
                if (
                    not isinstance(item, dict)
                    or not str(item.get("excuse") or "").strip()
                    or not str(item.get("counter") or "").strip()
                ):
                    errors.append(
                        f"skill '{label}' rationalizations[{index}] needs excuse + counter"
                    )
    return errors


def extract_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    """归一化技能契约字段 (缺省为空)。供 SkillHub 存储与渲染。"""
    manifest = manifest or {}
    return {
        "when_to_use": _str_list(manifest.get("when_to_use")),
        "verification": _str_list(manifest.get("verification")),
        "red_flags": _str_list(manifest.get("red_flags")),
        "rationalizations": [
            {
                "excuse": str(item.get("excuse") or "").strip(),
                "counter": str(item.get("counter") or "").strip(),
            }
            for item in (manifest.get("rationalizations") or [])
            if isinstance(item, dict)
        ],
    }


def has_contract(manifest: dict[str, Any]) -> bool:
    """是否声明了任一扩展契约字段 (决定要不要渲染契约块)。"""
    contract = extract_contract(manifest)
    return any(contract[field] for field in CONTRACT_FIELDS)


def format_skill_contract_block(
    manifest: dict[str, Any], *, include_rationalizations: bool = False
) -> str:
    """把技能契约渲染成紧凑文本块 (渐进披露: 命中技能时喂给模型)。

    只渲染已声明的段, 无契约 → 返回空串。``include_rationalizations`` 默认关
    (借口/反驳偏长, 仅在模型显式追问技能细节时展开)。
    """
    manifest = manifest or {}
    contract = extract_contract(manifest)
    name = str(manifest.get("name") or "").strip()
    lines: list[str] = []
    if name:
        lines.append(f"## skill: {name}")
    desc = str(manifest.get("description") or "").strip()
    if desc:
        lines.append(desc)
    if contract["when_to_use"]:
        lines.append("When to use: " + "; ".join(contract["when_to_use"]))
    if contract["verification"]:
        lines.append("Verify (evidence required):")
        lines += [f"  - {item}" for item in contract["verification"]]
    if contract["red_flags"]:
        lines.append("Red flags:")
        lines += [f"  - {item}" for item in contract["red_flags"]]
    if include_rationalizations and contract["rationalizations"]:
        lines.append("Do not skip:")
        lines += [f'  - "{r["excuse"]}" → {r["counter"]}' for r in contract["rationalizations"]]
    return "\n".join(lines)


def _str_list(value: Any) -> list[str]:
    """str → [str]; list → 清洗后的 str 列表; 其它 → []。与 leaf_contract 同口径。"""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
