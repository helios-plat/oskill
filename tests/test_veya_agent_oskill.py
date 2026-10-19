"""Tests for Veya 顶级 Agent 增强元素 — oskill 层 (3 个).

Covers: repomap_gen, hitl_instruction_steer, mcp_schema_adapter.
注意：oskill venv 无 obase 依赖，全部经 Protocol 注入（FakeIndexer）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

# ---------------------------------------------------------------------------
# repomap_gen（注入 FakeIndexer）
# ---------------------------------------------------------------------------


class FakeIndexer:
    def __init__(self, *, fail=False):
        self.fail = fail

    async def index_file(self, path):
        return []

    async def index_tree(self, root, *, max_files=500):
        if self.fail:
            raise FileNotFoundError(root)

        def sym(name, kind, path):
            return SimpleNamespace(
                name=name,
                kind=kind,
                path=path,
                to_dict=lambda: {"name": name, "kind": kind, "path": path},
            )

        return SimpleNamespace(
            root=root,
            files=["/r/a.py", "/r/b.py", "/r/util.py"],
            languages={"python": 3},
            symbol_count=5,
            symbols=[
                sym("alpha", "function", "/r/a.py"),
                sym("b", "import", "/r/a.py"),
                sym("Beta", "class", "/r/b.py"),
                sym("b2", "function", "/r/b.py"),
                sym("util_fn", "function", "/r/util.py"),
            ],
        )


class TestRepomapGen:
    async def test_basic_repomap(self):
        from oskill import repomap_gen

        m = await repomap_gen("/r", indexer=FakeIndexer())
        assert m["root"] == "/r"
        assert m["symbol_count"] == 5
        assert m["languages"] == {"python": 3}
        assert m["symbol_index"]["alpha"] == ["/r/a.py"]
        assert "Beta" in m["symbol_index"]

    async def test_module_edge(self):
        from oskill import repomap_gen

        m = await repomap_gen("/r", indexer=FakeIndexer())
        # import b → /r/b.py（模块 stem 匹配）
        assert {"from": "/r/a.py", "to": "/r/b.py"} in m["edges"], m["edges"]

    async def test_orphan_modules(self):
        from oskill import repomap_gen

        m = await repomap_gen("/r", indexer=FakeIndexer())
        assert "/r/util.py" in m["orphan_modules"]

    async def test_missing_root(self):
        from oskill import repomap_gen

        with pytest.raises(Exception, match="root not found"):
            await repomap_gen("/nope", indexer=FakeIndexer(fail=True))

    async def test_empty_root_rejected(self):
        from oskill import repomap_gen

        with pytest.raises(Exception):
            await repomap_gen("", indexer=FakeIndexer())

    async def test_indexer_required(self):
        from oskill import repomap_gen

        with pytest.raises(Exception):
            await repomap_gen("/r", indexer=None)


# ---------------------------------------------------------------------------
# hitl_instruction_steer
# ---------------------------------------------------------------------------


class TestHitlInstructionSteer:
    def test_prepend(self):
        from oskill import hitl_instruction_steer

        r = hitl_instruction_steer("先跑测试", original_text="计划：\n- 开发")
        assert r["steered"] and r["mode"] == "prepend"
        assert r["text"].startswith("[HITL 干预] 先跑测试")

    def test_append(self):
        from oskill import hitl_instruction_steer

        r = hitl_instruction_steer("别忘了文档", original_text="计划", mode="append")
        assert r["text"].endswith("[HITL 干预] 别忘了文档")

    def test_replace_with_anchor(self):
        from oskill import hitl_instruction_steer

        text = "步骤：\n1. 使用 MySQL\n2. 部署"
        r = hitl_instruction_steer(
            "改用 PostgreSQL", original_text=text, mode="replace", anchor="MySQL"
        )
        assert r["replaced"] and r["steered"]
        assert "PostgreSQL" in r["text"] and "MySQL" not in r["text"]

    def test_replace_anchor_miss(self):
        from oskill import hitl_instruction_steer

        r = hitl_instruction_steer("x", original_text="abc", mode="replace", anchor="zzz")
        assert r["steered"] is False and r["replaced"] is False
        assert r["text"] == "abc"

    def test_markers_off(self):
        from oskill import hitl_instruction_steer

        r = hitl_instruction_steer("停", original_text="x", markers=False)
        assert "[HITL" not in r["text"]

    def test_replace_requires_anchor(self):
        from oskill import hitl_instruction_steer

        with pytest.raises(Exception):
            hitl_instruction_steer("x", original_text="y", mode="replace")

    def test_empty_rejected(self):
        from oskill import hitl_instruction_steer

        with pytest.raises(Exception):
            hitl_instruction_steer("", original_text="y")


# ---------------------------------------------------------------------------
# mcp_schema_adapter
# ---------------------------------------------------------------------------


class TestMcpSchemaAdapter:
    def test_to_mcp_camel_case(self):
        from oskill import mcp_schema_adapter

        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "max_amount": {"type": "number"},
            },
            "required": ["user_id"],
        }
        out = mcp_schema_adapter(schema)
        assert set(out["properties"]) == {"userId", "maxAmount"}
        assert out["required"] == ["userId"]

    def test_to_python_snake_case(self):
        from oskill import mcp_schema_adapter

        schema = {
            "type": "object",
            "properties": {"userId": {"type": "string"}},
            "required": ["userId"],
        }
        out = mcp_schema_adapter(schema, direction="to_python")
        assert "user_id" in out["properties"]
        assert out["required"] == ["user_id"]

    def test_nested_properties(self):
        from oskill import mcp_schema_adapter

        schema = {
            "type": "object",
            "properties": {
                "billing_address": {
                    "type": "object",
                    "properties": {"street_name": {"type": "string"}},
                }
            },
        }
        out = mcp_schema_adapter(schema)
        assert "streetName" in out["properties"]["billingAddress"]["properties"]

    def test_invalid_schema_rejected(self):
        from oskill import mcp_schema_adapter

        with pytest.raises(Exception):
            mcp_schema_adapter({"type": "array"})
        with pytest.raises(Exception):
            mcp_schema_adapter({"type": "object"})  # 无 properties

    def test_to_openai_tools(self):
        from oskill import to_openai_tools

        schema = {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        }
        t = to_openai_tools(schema, name="pay", description="支付")
        assert t["type"] == "function"
        assert t["function"]["name"] == "pay"
        assert "userId" in t["function"]["parameters"]["properties"]

    def test_to_openai_requires_name(self):
        from oskill import to_openai_tools

        with pytest.raises(Exception):
            to_openai_tools({"type": "object", "properties": {}}, name="", description="d")
