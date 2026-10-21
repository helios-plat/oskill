"""Tests for Veya P1/P2 顶级 Agent 功能复现 — oskill 层 (8 个).

Covers: deep_research_tree, dag_visual_layout, leader_worker_dispatch,
contextual_reschedule, voice_interruption_handler, soul_self_evolution,
worktree_conflict_resolve, harness_uniform_route.
"""

from __future__ import annotations

import pytest


class FakeLLM:
    def __init__(self, score_current="7", score_candidate="9"):
        self.scores = (score_current, score_candidate)

    async def __call__(self, *, messages, tools=None, max_tokens=4096, stop_sequences=None):
        q = messages[-1]["content"]
        if "子问题" in q:
            ans = "1 子问题A\n2 子问题B"
        elif "配置进化" in q:
            ans = "候选SOUL v2"
        elif "适配度" in q:
            ans = self.scores[0] if "当前" in q else self.scores[1]
        elif "打断判定" in q:
            ans = '{"interrupts": true, "confidence": 0.9}'
        else:
            ans = "t1 | 理由"
        return {
            "content": [{"type": "text", "text": ans}],
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "stop_reason": "end_turn",
        }


class TestDeepResearchTree:
    async def test_tree_expansion(self):
        from oskill import deep_research_tree

        r = await deep_research_tree("量子计算", caller=FakeLLM(), max_depth=2, max_branches=2)
        assert r["node_count"] == 3  # 根 + 2 子
        assert r["depth"] == 2
        root = r["nodes"][0]
        assert root["parent"] is None and len(root["children"]) == 2

    async def test_max_depth_respected(self):
        from oskill import deep_research_tree

        r = await deep_research_tree("x", caller=FakeLLM(), max_depth=1, max_branches=2)
        assert r["depth"] == 1 and r["node_count"] == 1

    async def test_empty_rejected(self):
        from oskill import deep_research_tree

        with pytest.raises(Exception):
            await deep_research_tree("", caller=FakeLLM())


class TestDagVisualLayout:
    def test_layered(self):
        from oskill import dag_visual_layout

        lay = dag_visual_layout(
            ["a", "b", "c"],
            edges=[{"from": "a", "to": "b"}, {"from": "a", "to": "c"}],
        )
        assert lay["positions"]["a"]["level"] == 0
        assert lay["positions"]["b"]["level"] == 1
        assert lay["positions"]["b"]["y"] > lay["positions"]["a"]["y"]

    def test_radial(self):
        from oskill import dag_visual_layout

        lay = dag_visual_layout(["a", "b"], edges=[], layout="radial", width=100, height=100)
        assert lay["layout"] == "radial"
        assert 0 <= lay["positions"]["a"]["x"] <= 100

    def test_unknown_node(self):
        from oskill import dag_visual_layout

        with pytest.raises(Exception):
            dag_visual_layout(["a"], edges=[{"from": "a", "to": "ghost"}])


class TestLeaderWorkerDispatch:
    async def test_round_robin(self):
        from oskill import leader_worker_dispatch

        async def w1(task, payload):
            return f"w1:{task}"

        async def w2(task, payload):
            return f"w2:{task}"

        r = await leader_worker_dispatch(["a", "b", "c"], workers={"w1": w1, "w2": w2})
        assert r["completed"] == 3
        assert r["assignments"] == {"a": "w1", "b": "w2", "c": "w1"}

    async def test_least_busy(self):
        from oskill import leader_worker_dispatch

        r = await leader_worker_dispatch(
            ["a", "b", "c"],
            workers={"w1": lambda t, p: 1, "w2": lambda t, p: 1},
            strategy="least_busy",
        )
        # 交替（计数相同 → min 取首个）
        assert r["assignments"]["a"] == "w1"

    async def test_leader_injected(self):
        from oskill import leader_worker_dispatch

        class Leader:
            async def assign(self, task, workers):
                return "w2"

        async def w(task, payload):
            return task

        r = await leader_worker_dispatch(["a", "b"], workers={"w1": w, "w2": w}, leader=Leader())
        assert all(v == "w2" for v in r["assignments"].values())

    async def test_error_isolation(self):
        from oskill import leader_worker_dispatch

        async def good(task, payload):
            return "ok"

        async def bad(task, payload):
            raise RuntimeError("boom")

        r = await leader_worker_dispatch(["a", "b"], workers={"good": good, "bad": bad})
        assert r["completed"] == 1 and r["failed"] == 1
        assert "boom" in next(iter(r["errors"].values()))

    async def test_empty_rejected(self):
        from oskill import leader_worker_dispatch

        with pytest.raises(Exception):
            await leader_worker_dispatch([], workers={"w": lambda t, p: 1})


class TestContextualReschedule:
    async def test_heuristic_priority(self):
        from oskill import contextual_reschedule

        r = await contextual_reschedule(
            [{"id": "a", "priority": 1}, {"id": "b", "priority": 5}],
            context="b 更紧急",
        )
        assert r["method"] == "heuristic"
        assert r["order"] == ["b", "a"]

    async def test_llm_path(self):
        from oskill import contextual_reschedule

        r = await contextual_reschedule([{"id": "a", "priority": 1}], context="x", caller=FakeLLM())
        assert r["method"] == "llm"
        assert r["order"] == ["a"]  # t1 非法 id → 保留原序

    async def test_empty_rejected(self):
        from oskill import contextual_reschedule

        with pytest.raises(Exception):
            await contextual_reschedule([], context="x")


class TestVoiceInterruptionHandler:
    async def test_keyword_interrupt(self):
        from oskill import voice_interruption_handler

        r = await voice_interruption_handler("停一下，我改主意了", current_turn="执行中")
        assert r["interrupts"] is True and r["action"] == "pause"
        assert r["method"] == "heuristic"

    async def test_non_interrupt(self):
        from oskill import voice_interruption_handler

        r = await voice_interruption_handler("好的继续", current_turn="执行中")
        assert r["interrupts"] is False and r["action"] == "continue"

    async def test_llm_path(self):
        from oskill import voice_interruption_handler

        r = await voice_interruption_handler("随便说说", current_turn="x", caller=FakeLLM())
        assert r["method"] == "llm" and r["interrupts"] is True

    async def test_empty_rejected(self):
        from oskill import voice_interruption_handler

        with pytest.raises(Exception):
            await voice_interruption_handler("", current_turn="x")


class TestSoulSelfEvolution:
    async def test_adopt(self):
        from oskill import soul_self_evolution

        r = await soul_self_evolution("SOUL v1", feedback="太啰嗦", caller=FakeLLM())
        assert r["evolved"] is True
        assert r["candidate"] == "候选SOUL v2"
        assert r["candidate_score"] == 9 and r["current_score"] == 7
        assert r["diff"]

    async def test_reject_no_gain(self):
        from oskill import soul_self_evolution

        r = await soul_self_evolution("SOUL v1", feedback="x", caller=FakeLLM("9", "5"))
        assert r["evolved"] is False
        assert r["candidate"] == "SOUL v1"  # 未采纳保留原配置

    async def test_empty_rejected(self):
        from oskill import soul_self_evolution

        with pytest.raises(Exception):
            await soul_self_evolution("", feedback="x", caller=FakeLLM())


class TestWorktreeConflictResolve:
    def test_ours(self):
        from oskill import worktree_conflict_resolve

        r = worktree_conflict_resolve(
            [{"file": "a", "ours": "x=1", "theirs": "x=2"}], strategy="ours"
        )
        assert r["resolved"][0]["content"] == "x=1"

    def test_theirs(self):
        from oskill import worktree_conflict_resolve

        r = worktree_conflict_resolve(
            [{"file": "a", "ours": "x=1", "theirs": "x=2"}], strategy="theirs"
        )
        assert r["resolved"][0]["content"] == "x=2"

    def test_merge_identical(self):
        from oskill import worktree_conflict_resolve

        r = worktree_conflict_resolve(
            [{"file": "a", "ours": "l1\nl2", "theirs": "l1\nl2"}], strategy="merge"
        )
        assert r["resolved"][0]["content"] == "l1\nl2"

    def test_merge_unresolvable(self):
        from oskill import worktree_conflict_resolve

        r = worktree_conflict_resolve([{"file": "a", "ours": "x", "theirs": "y"}], strategy="merge")
        assert len(r["unresolved"]) == 1
        assert "<<<<<<<" in r["unresolved"][0].get("reason", "") or r["unresolved"][0]["reason"]

    def test_empty_rejected(self):
        from oskill import worktree_conflict_resolve

        with pytest.raises(Exception):
            worktree_conflict_resolve([])


class TestHarnessUniformRoute:
    async def test_exact_route(self):
        from oskill import harness_uniform_route

        async def h(ev):
            return f"handled {ev['kind']}"

        r = await harness_uniform_route(
            {"type": "task.done", "data": {"id": 1}}, handlers={"task.done": h}
        )
        assert r["handled"] and r["route"] == "task.done"
        assert r["normalized"]["payload"] == {"id": 1}

    async def test_prefix_route(self):
        from oskill import harness_uniform_route

        async def h(ev):
            return "ok"

        r = await harness_uniform_route({"kind": "task.fail"}, handlers={"task.*": h})
        assert r["route"] == "task.*"

    async def test_wildcard_and_fallback(self):
        from oskill import harness_uniform_route

        async def h(ev):
            return "wild"

        async def fb(ev):
            return "fallback"

        r = await harness_uniform_route({"kind": "zz"}, handlers={"*": h})
        assert r["route"] == "*" and r["result"] == "wild"
        r2 = await harness_uniform_route({"kind": "zz"}, handlers={"task.*": h}, fallback=fb)
        assert r2["route"] == "__fallback__" and r2["result"] == "fallback"

    async def test_no_match(self):
        from oskill import harness_uniform_route

        async def h(ev):
            return 1

        r = await harness_uniform_route({"kind": "zz"}, handlers={"task.*": h})
        assert r["handled"] is False and r["route"] is None

    async def test_router_injected(self):
        from oskill import harness_uniform_route

        class Router:
            async def handle(self, event):
                return {"routed": event["kind"]}

        r = await harness_uniform_route({"kind": "k"}, router=Router())
        assert r["route"] == "router" and r["result"] == {"routed": "k"}
