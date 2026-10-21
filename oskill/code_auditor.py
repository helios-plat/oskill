"""3O 范式 Phase 3 — 组合型技能 (规范 §4.1: 组合 ≥2 个 oprim + LLM).

只读审计: 绝不写入文件、绝不持久化 (规范 §4.2)。
"""

from __future__ import annotations

from typing import Any

from obase import VFSProvider
from oprim import execute_sandbox_cmd, read_isolated_file

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_json_block


async def audit_sandbox_script(
    target_path: str,  # ≤1个核心位置参数
    *,  # 强制 kwonly
    llm: LLMCaller,
    vfs: VFSProvider,
) -> dict[str, Any]:
    """
    组合技能: 读取沙盒代码，执行语法检查，交由 LLM 分析并提取结果。

    Composes oprim: [read_isolated_file, execute_sandbox_cmd]
    Composes oskill: [extract_json_block]
    """
    # 1. 组合 oprim_A: 读取文件 (不越权，仅用读权限)
    code_content = await read_isolated_file(target_path, vfs=vfs)

    # 2. 组合 oprim_B: 执行语法检查 (如 python -m py_compile)
    exec_result = await execute_sandbox_cmd(f"python -m py_compile {target_path}", vfs=vfs)

    # 3. 算法装配: 无论对错，将证据收集起来发给模型
    prompt = (
        f"Please audit this code:\n\n```python\n{code_content}\n```\n\n"
        f"Syntax check stderr: {exec_result['stderr']}\n"
        "Return a JSON block with keys: 'has_bug', 'confidence', and 'analysis'."
    )

    messages = [{"role": "user", "content": prompt}]

    # 4. 调用协议注入的 LLM
    llm_response = await llm(messages=messages)
    raw_text = llm_response.get("content", "")

    # 5. 受限互调 (Sibling Call): 调用纯无状态 oskill 解析结果
    # 深度为 1，完全符合规范 §1.2 的 4 约束
    return extract_json_block(raw_text)
