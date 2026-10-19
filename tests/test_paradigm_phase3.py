"""3O 范式 Phase 3 — oskill 元技能层测试.

覆盖: 纯解析技能、§4.3 LLM 协议注入、§4.1 组合 ≥2 oprim + LLM + sibling。
"""

from __future__ import annotations

import inspect

import pytest
from obase import LocalVFS

from oskill import audit_sandbox_script, extract_json_block
from oskill.code_auditor import audit_sandbox_script as _audit_impl
from oskill.protocols import LLMCaller


def test_extract_json_block_valid():
    text = 'prefix\n```json\n{"has_bug": true, "confidence": 0.9, "analysis": "x"}\n```\nsuffix'
    assert extract_json_block(text) == {
        "has_bug": True,
        "confidence": 0.9,
        "analysis": "x",
    }


def test_extract_json_block_missing():
    with pytest.raises(ValueError, match="No JSON block"):
        extract_json_block("no json here")


def test_extract_json_block_invalid():
    with pytest.raises(ValueError, match="Invalid JSON"):
        extract_json_block("```json\n{not valid}\n```")


def test_llm_caller_is_protocol():
    """§4.3: LLMCaller 是 Protocol (不可实例化), 强迫上层注入。"""
    assert inspect.isclass(LLMCaller)
    with pytest.raises(TypeError):
        LLMCaller()  # type: ignore[abstract]


def test_audit_sandbox_script_signature():
    """§4.4 风格: ≤1 位置参数, 其余 keyword-only。"""
    params = list(inspect.signature(_audit_impl).parameters.values())
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    assert [p.name for p in positional] == ["target_path"]
    for p in params[1:]:
        assert p.kind is p.KEYWORD_ONLY


def test_composes_declaration_in_docstring():
    """规范 §1.2: sibling 互调必须在 docstring 显式声明 Composes。"""
    doc = _audit_impl.__doc__ or ""
    assert "Composes oprim: [read_isolated_file, execute_sandbox_cmd]" in doc
    assert "Composes oskill: [extract_json_block]" in doc


class _FakeLLM:
    """结构化实现 LLMCaller 协议的假 LLM。"""

    def __init__(self, reply: str):
        self.reply = reply

    async def __call__(self, *, messages, tools=None, max_tokens=4096):
        assert isinstance(messages, list) and messages
        assert "audit this code" in messages[0]["content"]
        return {"content": self.reply}


async def test_audit_sandbox_script_composition(tmp_path):
    """端到端: 读文件(oprim) + py_compile(oprim) + LLM(注入) + 解析(sibling)。"""
    vfs = LocalVFS(str(tmp_path))
    await vfs.write_file("script.py", b"def f():\n    return 1\n")
    fake_llm = _FakeLLM('```json\n{"has_bug": false, "confidence": 0.95, "analysis": "clean"}\n```')
    result = await audit_sandbox_script("script.py", llm=fake_llm, vfs=vfs)
    assert result == {"has_bug": False, "confidence": 0.95, "analysis": "clean"}


async def test_audit_sandbox_script_syntax_error_still_audited(tmp_path):
    """语法错误不阻断: 证据照常交给 LLM 审计。"""
    vfs = LocalVFS(str(tmp_path))
    await vfs.write_file("bad.py", b"def broken(:\n")
    fake_llm = _FakeLLM(
        '```json\n{"has_bug": true, "confidence": 0.99, "analysis": "syntax error"}\n```'
    )
    result = await audit_sandbox_script("bad.py", llm=fake_llm, vfs=vfs)
    assert result["has_bug"] is True
