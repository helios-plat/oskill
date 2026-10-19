"""3O 范式 Phase 3 — 纯计算技能 (stateless, 无 IO, 无外部依赖).

被其他 oskill 受限互调 (规范 §1.2: 仅允许调用纯计算 sibling)。
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError


def extract_json_block(text: str) -> dict[str, Any]:
    """
    纯计算技能: 从 LLM 返回的文本中提取 Markdown JSON 块。
    无 IO, 无外部依赖, stateless。
    """
    pattern = r"```json\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in LLM output.")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}") from e


def extract_code_block(text: str, *, language: str = "python") -> str:
    """纯计算技能: 从 LLM 输出中提取指定语言的代码围栏块 (无状态)。

    无围栏时原样返回 (容忍裸代码输出)。
    """
    pattern = rf"```(?:{language}|\w*)\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return text.strip()
    return match.group(1).strip()


def parse_tool_call_json(raw_text: str) -> dict:
    """技能 13: 提取工具 JSON (无状态)"""
    try:
        # 简化版：实际应含正则提取逻辑
        return json.loads(raw_text)
    except Exception as e:
        raise ValueError(f"Invalid Tool JSON: {e}") from e


def validate_tool_args(schema: type[BaseModel], args: dict) -> BaseModel:
    """技能 14: 形式化校验 (无 IO)"""
    try:
        return schema(**args)
    except ValidationError as e:
        raise ValueError(f"Schema violation: {e.json()}") from e
