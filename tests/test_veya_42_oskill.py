"""Tests for the Veya/3O 42-element inventory — oskill layer (9 skills).

Covers: context_compression, rag_rerank, code_symbol_investigate,
browser_automation_loop, prompt_evolution_eval, multi_modal_fusion,
error_diagnose_skill, mcp_tool_route, task_dag_split.
"""

from __future__ import annotations

import pathlib

import pytest

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class FakeLLM:
    def __init__(self, answer_map=None, default="结论X"):
        self.answer_map = answer_map or {}
        self.default = default

    async def __call__(self, *, messages, tools=None, max_tokens=4096, stop_sequences=None):
        q = messages[-1]["content"]
        for key, ans in self.answer_map.items():
            if key in q:
                return {
                    "content": [{"type": "text", "text": ans}],
                    "usage": {"input_tokens": 5, "output_tokens": 3},
                    "stop_reason": "end_turn",
                }
        return {
            "content": [{"type": "text", "text": self.default}],
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "stop_reason": "end_turn",
        }


SUMMARIZER = FakeLLM(answer_map={"摘要": "关键决策已保留"})
JUDGE = FakeLLM(answer_map={"Prompt:": "8", "评估器": "8"})
DIAG = FakeLLM(
    answer_map={
        "root_cause": '{"root_cause": "空指针", "confidence": 0.9, "fix_suggestions": ["判空"]}'
    }
)
DAG = FakeLLM(
    answer_map={
        "nodes": '{"nodes": [{"id": "t1", "title": "a"}, {"id": "t2", "title": "b"}], "edges": [{"from": "t1", "to": "t2"}]}'
    }
)


class FakeEmbed:
    async def __call__(self, *, text, model="x"):
        return [1.0, 0.0]


class FakeStore:
    def __init__(self, hits):
        self.hits = hits

    async def search(self, *args, **kwargs):
        return self.hits


class FakePage:
    async def goto(self, url, *, timeout_ms=30_000):
        pass

    async def content(self):
        return "<html></html>"

    async def click(self, selector, *, timeout_ms=10_000):
        pass

    async def screenshot(self, *, path=None):
        return b""


# ---------------------------------------------------------------------------
# context_compression
# ---------------------------------------------------------------------------


class TestContextCompression:
    async def test_long_text_compressed(self):
        from oskill import context_compression

        r = await context_compression("x" * 10_000, caller=SUMMARIZER, budget_tokens=1000)
        assert r["compressed"] is True
        assert r["ratio"] < 1.0
        assert r["summary"] == "关键决策已保留"

    async def test_short_text_untouched(self):
        from oskill import context_compression

        r = await context_compression("short", caller=SUMMARIZER)
        assert r["compressed"] is False and r["text"] == "short"

    async def test_empty_rejected(self):
        from oskill import context_compression

        with pytest.raises(Exception):
            await context_compression("", caller=SUMMARIZER)


# ---------------------------------------------------------------------------
# rag_rerank
# ---------------------------------------------------------------------------


class TestRagRerank:
    async def test_rerank_order(self):
        from oskill import rag_rerank

        hits = [
            {"chunk_id": "c1", "content": "a", "score": 0.9},
            {"chunk_id": "c2", "content": "b", "score": 0.3},
        ]
        ranked = await rag_rerank("q", embedder=FakeEmbed(), store=FakeStore(hits), top_k=2)
        assert ranked[0]["chunk_id"] == "c1"
        assert ranked[1]["score"] < ranked[0]["score"]

    async def test_empty_query_rejected(self):
        from oskill import rag_rerank

        with pytest.raises(Exception):
            await rag_rerank("", embedder=FakeEmbed(), store=FakeStore([]))

    async def test_no_candidates(self):
        from oskill import rag_rerank

        with pytest.raises(Exception):
            await rag_rerank("q", embedder=FakeEmbed(), store=FakeStore([]))


# ---------------------------------------------------------------------------
# code_symbol_investigate
# ---------------------------------------------------------------------------


class TestCodeSymbolInvestigate:
    async def test_dependency_graph(self, tmp_path: pathlib.Path):
        from oskill import code_symbol_investigate

        (tmp_path / "a.py").write_text("def foo(): pass\nimport b\n")
        (tmp_path / "b.py").write_text("class B: pass\ndef foo2(): pass\n")
        g = await code_symbol_investigate([str(tmp_path / "a.py"), str(tmp_path / "b.py")])
        assert g["total_symbols"] >= 4
        assert g["modules"]
        assert all(e["symbol"] in ("B", "foo2", "b") for e in g["edges"])

    async def test_empty_paths_rejected(self):
        from oskill import code_symbol_investigate

        with pytest.raises(Exception):
            await code_symbol_investigate([])

    async def test_all_unparseable(self, tmp_path: pathlib.Path):
        from oskill import code_symbol_investigate

        p = tmp_path / "missing.py"
        with pytest.raises(Exception):
            await code_symbol_investigate([str(p)])


# ---------------------------------------------------------------------------
# browser_automation_loop
# ---------------------------------------------------------------------------


class TestBrowserAutomationLoop:
    async def test_multi_step(self):
        from oskill import browser_automation_loop

        r = await browser_automation_loop(
            FakePage(),
            steps=[
                {"action": "goto", "url": "http://x"},
                {"action": "click", "selector": "#a"},
            ],
        )
        assert r["status"] == "completed" and r["steps_done"] == 2

    async def test_stop_on_error(self):
        from oskill import browser_automation_loop

        class BrokenPage(FakePage):
            async def click(self, selector, *, timeout_ms=10_000):
                raise TimeoutError("no element")

        r = await browser_automation_loop(
            BrokenPage(),
            steps=[{"action": "click", "selector": "#missing"}],
        )
        assert r["status"] == "stopped" and r["steps_done"] == 1

    async def test_empty_steps_rejected(self):
        from oskill import browser_automation_loop

        with pytest.raises(Exception):
            await browser_automation_loop(FakePage(), steps=[])


# ---------------------------------------------------------------------------
# prompt_evolution_eval
# ---------------------------------------------------------------------------


class TestPromptEvolutionEval:
    async def test_ranking(self):
        from oskill import prompt_evolution_eval

        r = await prompt_evolution_eval({"v1": "p1", "v2": "p2"}, samples=["s1"], judge=JUDGE)
        assert r["best_variant"] in ("v1", "v2")
        assert r["scores"]["v1"]["avg"] == 8.0
        assert r["ranked"][0] == r["best_variant"]

    async def test_too_few_variants(self):
        from oskill import prompt_evolution_eval

        with pytest.raises(Exception):
            await prompt_evolution_eval({"v1": "p1"}, samples=["s"], judge=JUDGE)


# ---------------------------------------------------------------------------
# multi_modal_fusion
# ---------------------------------------------------------------------------


class TestMultiModalFusion:
    async def test_text_doc_fusion(self, tmp_path: pathlib.Path):
        from oskill import multi_modal_fusion

        doc = tmp_path / "doc.txt"
        doc.write_text("报表内容")
        r = await multi_modal_fusion(
            {"text": "hello", "doc": [str(doc)]}, prompt="总结", caller=FakeLLM()
        )
        assert r["conclusion"] == "结论X"
        assert r["inputs_count"] == 2

    async def test_empty_inputs_rejected(self):
        from oskill import multi_modal_fusion

        with pytest.raises(Exception):
            await multi_modal_fusion({}, prompt="总结", caller=FakeLLM())


# ---------------------------------------------------------------------------
# error_diagnose_skill
# ---------------------------------------------------------------------------


class TestErrorDiagnoseSkill:
    async def test_diagnosis(self, tmp_path: pathlib.Path):
        from oskill import error_diagnose_skill

        (tmp_path / "a.py").write_text("def foo(): pass\n")
        r = await error_diagnose_skill(
            'Traceback (most recent call last):\n  File "/repo/app.py", line 5, in main',
            caller=DIAG,
            file_paths=[str(tmp_path / "a.py")],
        )
        assert r["root_cause"] == "空指针"
        assert r["confidence"] == 0.9
        assert "foo" in r["related_symbols"]
        assert r["evidence"]  # 堆栈文件线索

    async def test_empty_traceback_rejected(self):
        from oskill import error_diagnose_skill

        with pytest.raises(Exception):
            await error_diagnose_skill("", caller=DIAG)


# ---------------------------------------------------------------------------
# mcp_tool_route
# ---------------------------------------------------------------------------


class TestMcpToolRoute:
    async def test_route_vector_path(self):
        from oskill import mcp_tool_route

        tools = [
            {"name": "weather", "description": "查询天气"},
            {"name": "calc", "description": "计算"},
        ]
        r = await mcp_tool_route(
            "天气怎么样",
            tools=tools,
            embedder=FakeEmbed(),
            store=FakeStore([{"chunk_id": "weather", "content": "w", "score": 0.8}]),
        )
        assert r["best_tool"]["name"] == "weather"

    async def test_route_keyword_fallback(self):
        from oskill import mcp_tool_route

        tools = [{"name": "weather", "description": "查询天气"}]
        r = await mcp_tool_route("天气", tools=tools, embedder=FakeEmbed(), store=FakeStore([]))
        assert r["best_tool"]["name"] == "weather"

    async def test_empty_rejected(self):
        from oskill import mcp_tool_route

        with pytest.raises(Exception):
            await mcp_tool_route("", tools=[], embedder=FakeEmbed(), store=FakeStore([]))


# ---------------------------------------------------------------------------
# task_dag_split
# ---------------------------------------------------------------------------


class TestTaskDagSplit:
    async def test_split_and_toposort(self):
        from oskill import task_dag_split

        r = await task_dag_split("开发登录", caller=DAG)
        assert len(r["nodes"]) == 2
        assert r["topological_order"] == ["t1", "t2"]
        assert r["cycle_detected"] is False

    async def test_cycle_detection(self):
        from oskill._task_dag_split import _toposort

        order, cycle = _toposort(["a", "b"], [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
        assert cycle is True and set(order) == {"a", "b"}

    async def test_empty_rejected(self):
        from oskill import task_dag_split

        with pytest.raises(Exception):
            await task_dag_split("", caller=DAG)
