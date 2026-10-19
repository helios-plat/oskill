"""skill_contract — 校验 / 归一化 / 渲染 (纯函数)。"""

from __future__ import annotations

from oskill._skill_contract import (
    extract_contract,
    format_skill_contract_block,
    has_contract,
    validate_skill_contract,
)

_FULL = {
    "name": "refactor_py",
    "description": "refactor python code",
    "parameters": {"type": "object", "properties": {"goal": {"type": "string"}}},
    "when_to_use": ["function too long", "duplicate logic"],
    "verification": ["pytest green", "no new lint errors"],
    "red_flags": ["no tests exist"],
    "rationalizations": [{"excuse": "too small to test", "counter": "still add one test"}],
}


def test_full_contract_valid():
    assert validate_skill_contract(_FULL) == []
    assert has_contract(_FULL) is True


def test_minimal_valid_no_contract_fields():
    m = {"name": "x", "description": "d", "parameters": {"properties": {}}}
    assert validate_skill_contract(m) == []
    assert has_contract(m) is False  # 无扩展契约 → 不渲染契约块


def test_missing_core_fields():
    errs = validate_skill_contract({"name": "x"})
    assert any("requires description" in e for e in errs)
    assert any("parameters.properties" in e for e in errs)


def test_contract_field_present_but_empty():
    m = {"name": "x", "description": "d", "parameters": {"properties": {}}, "verification": []}
    errs = validate_skill_contract(m)
    assert any("verification present but empty" in e for e in errs)


def test_rationalizations_need_excuse_and_counter():
    m = {
        "name": "y",
        "description": "d",
        "parameters": {"properties": {}},
        "rationalizations": [{"excuse": "e"}],
    }
    errs = validate_skill_contract(m)
    assert any("rationalizations[1] needs excuse + counter" in e for e in errs)


def test_extract_normalizes_str_to_list():
    m = {"name": "z", "description": "d", "parameters": {"properties": {}}, "when_to_use": "single"}
    c = extract_contract(m)
    assert c["when_to_use"] == ["single"]
    assert c["verification"] == []


def test_format_block_only_declared_sections():
    block = format_skill_contract_block(_FULL)
    assert "When to use:" in block
    assert "Verify (evidence required):" in block
    assert "Red flags:" in block
    assert "Do not skip:" not in block  # rationalizations 默认不展开


def test_format_block_include_rationalizations():
    block = format_skill_contract_block(_FULL, include_rationalizations=True)
    assert "Do not skip:" in block
    assert "too small to test" in block


def test_format_block_empty_when_no_contract():
    m = {"name": "x", "description": "", "parameters": {"properties": {}}}
    # 无 description 无契约段 → 只有标题行
    block = format_skill_contract_block(m)
    assert block.strip() == "## skill: x"
