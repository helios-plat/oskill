"""Tests for flow_orchestrator / bandit_router / memory_offload / pentest_squad /
code_parse / marketplace / svg_path_tools (2-8 深挖批次)。"""

from __future__ import annotations

import pytest

from oskill.bandit_router import BanditRouter
from oskill.code_parse import (
    SYMBOL_CLASS,
    parse_code,
    parse_python_tree,
)
from oskill.flow_orchestrator import (
    FlowBroker,
    FlowRegistry,
    FlowRunner,
    FlowStep,
)
from oskill.marketplace import (
    STATUS_CLAIMED,
    STATUS_DELIVERED,
    STATUS_OPEN,
    STATUS_SETTLED,
    Marketplace,
)
from oskill.memory_offload import OffloadPipeline
from oskill.pentest_squad import ROLE_RECON, SquadOrchestrator
from oskill.svg_path_tools import (
    fit_smooth_cubic,
    path_bbox,
    path_center,
    render_cubic_path,
    simplify_line,
)

# ── 2. flow_orchestrator ────────────────────────────────────────────


def _steps() -> list[FlowStep]:
    return [
        FlowStep("s1", "load", lambda i, c: {"data": "x"}),
        FlowStep("s2", "process", lambda i, c: {"out": c.get("data", "") + "!"}),
    ]


def test_flow_runner_sequential():
    result = FlowRunner().run(_steps(), {})
    assert result.ok is True
    assert result.steps_run == ["s1", "s2"]
    assert result.context["out"] == "x!"


def test_flow_runner_error_fail():
    steps = [
        FlowStep("s1", "boom", lambda i, c: (_ for _ in ()).throw(RuntimeError("x"))),
    ]
    result = FlowRunner().run(steps, {})
    assert result.ok is False
    assert "s1" in result.error


def test_flow_runner_error_skip():
    steps = [
        FlowStep(
            "s1", "boom", lambda i, c: (_ for _ in ()).throw(RuntimeError("x")), on_error="skip"
        ),
        FlowStep("s2", "after", lambda i, c: {"done": True}),
    ]
    result = FlowRunner().run(steps, {})
    assert result.ok is True
    assert result.context["done"] is True


def test_flow_runner_dynamic_insert():
    insert = FlowStep("extra", "extra", lambda i, c: {"extra": 1})
    result = FlowRunner().run(_steps(), {}, insert_steps=[insert])
    assert "insert:extra" in result.steps_run
    assert result.context["extra"] == 1


def test_flow_broker_dispatch():
    registry = FlowRegistry()
    registry.register("research", [FlowStep("r", "r", lambda i, c: {})])
    registry.register("build", [FlowStep("b", "b", lambda i, c: {})])
    broker = FlowBroker(registry)
    broker.add_route(lambda i: "research" if i.get("type") == "research" else "", "research")
    broker.add_route(lambda i: "build" if i.get("type") == "build" else "", "build")
    assert broker.dispatch({"type": "build"}) == "build"
    assert broker.dispatch({"type": "other"}) is None


# ── 3. bandit_router ────────────────────────────────────────────────


def test_bandit_records_and_updates():
    router = BanditRouter(seed=42)
    router.record("a", 1.0)
    router.record("a", 0.0)
    state = router.states["a"]
    assert state.alpha == 2.0
    assert state.beta == 2.0
    assert state.observations == 2


def test_bandit_sample_prefers_better():
    router = BanditRouter(seed=42, epsilon=0.0)
    router.record("good", 1.0)
    router.record("good", 1.0)
    router.record("good", 1.0)
    router.record("bad", 0.0)
    router.record("bad", 0.0)
    picks = [router.sample_best(["good", "bad"]) for _ in range(20)]
    assert picks.count("good") > picks.count("bad")


def test_bandit_choose_and_observe():
    router = BanditRouter(seed=1, epsilon=0.0)
    provider, result = router.choose_and_observe(
        ["p"],
        lambda p: "ok",
        reward_fn=lambda r: 1.0,
    )
    assert provider == "p"
    assert router.states["p"].observations == 1


def test_bandit_error_gives_zero_reward():
    router = BanditRouter(seed=1, epsilon=0.0)

    def boom(p):
        raise RuntimeError("x")

    provider, result = router.choose_and_observe(["p"], boom)
    assert result is None
    assert router.states["p"].beta > 1.0  # 失败记录


# ── 4. memory_offload (L1.5 + L3) ───────────────────────────────────


def test_l15_judge_segments():
    pipeline = OffloadPipeline()
    batches = [[{"role": "user"}], [{"role": "user"}], [{"role": "user"}]]
    pipeline.judge_segments(batches, lambda b: "long" if len(batches) > 2 else "short")
    assert len(pipeline.long_segments()) == 3


def test_l3_token_budget_and_compress():
    pipeline = OffloadPipeline(token_budget=100, compress_ratio=0.5)
    pipeline.ingest("x" * 1600)  # 400 tokens > 100 budget
    assert pipeline.should_compress() is True
    result = pipeline.compress(lambda t: "[compressed]")
    assert result["compressed_tokens"] > 0
    assert pipeline.cursor_token > 0
    assert pipeline.recall_cursor()["cursor_token"] > 0


def test_l3_no_compress_under_budget():
    pipeline = OffloadPipeline(token_budget=1000)
    pipeline.ingest("short")
    assert pipeline.should_compress() is False
    result = pipeline.compress(lambda t: "x")
    assert result["compressed_tokens"] == 0


# ── 6. pentest_squad ────────────────────────────────────────────────


def test_squad_orchestration():
    squad = SquadOrchestrator()
    squad.register_agent(ROLE_RECON, lambda t: {"hosts": ["h1"]})

    def exploit(task):
        return [{"title": "SQLi", "severity": "high"}, {"title": "误报"}]

    squad.register_agent("exploit", exploit)
    squad.register_agent("verify", lambda f: f.title == "SQLi")

    report = squad.run_squad("http://x")
    assert len(report.findings) == 2
    assert len(report.verified_findings) == 1
    assert report.verified_findings[0].title == "SQLi"
    assert report.agent_runs[ROLE_RECON] == 1


def test_squad_multi_context_parallel():
    squad = SquadOrchestrator()
    squad.register_agent("exploit", lambda task: [{"title": f"f{task['view']}"}])
    report = squad.run_squad("http://x", contexts=[{}, {}, {}])
    assert len(report.findings) == 3
    assert report.agent_runs["exploit:2"] == 1


def test_squad_unknown_role_raises():
    squad = SquadOrchestrator()
    with pytest.raises(ValueError, match="unknown role"):
        squad.register_agent("nope", lambda t: None)


# ── 7. code_parse ───────────────────────────────────────────────────


def test_parse_python_tree_symbols_and_calls():
    tree = parse_python_tree("def f():\n    g()\n\ndef g():\n    pass\n", module="a.py")
    assert [s.name for s in tree.symbols] == ["f", "g"]
    assert tree.calls[0].caller == "f"
    assert tree.calls[0].callee == "g"
    assert tree.callers_of("g") == ["f"]


def test_parse_python_class_method():
    tree = parse_python_tree("class A:\n    def m(self):\n        pass\n")
    kinds = {s.name: s.kind for s in tree.symbols}
    assert kinds["A"] == SYMBOL_CLASS
    assert kinds["m"] == "method"


def test_parse_python_imports():
    tree = parse_python_tree("import os\nfrom pathlib import Path\n")
    assert "os" in tree.imports
    assert "pathlib" in tree.imports


def test_parse_generic_go():
    tree = parse_code("package main\nfunc hello() {}\ntype User struct{}", module="main.go")
    assert "hello" in tree.symbol_names()


def test_parse_python_file(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("def a():\n    b()\n", encoding="utf-8")
    tree = parse_code(f)
    assert tree.symbols[0].name == "a"


# ── 8a. marketplace ─────────────────────────────────────────────────


def test_marketplace_full_flow():
    market = Marketplace()
    listing = market.post("商家", "做一篇种草文", budget=100)
    assert listing.status == STATUS_OPEN
    market.claim(listing.id, "creator-1")
    assert market.listings[listing.id].status == STATUS_CLAIMED

    def publish(listing, content):
        return "content-123"

    market.deliver(
        listing.id, "creator-1", platform="xhs", content={"title": "t"}, publish_fn=publish
    )
    assert market.listings[listing.id].status == STATUS_DELIVERED
    assert market.listings[listing.id].content_id == "content-123"

    amount = market.settle(listing.id)
    assert amount == 100
    assert market.listings[listing.id].status == STATUS_SETTLED


def test_marketplace_claim_twice_rejected():
    market = Marketplace()
    listing = market.post("m", "b")
    market.claim(listing.id, "c1")
    with pytest.raises(ValueError, match="not open"):
        market.claim(listing.id, "c2")


def test_marketplace_deliver_wrong_creator():
    market = Marketplace()
    listing = market.post("m", "b")
    market.claim(listing.id, "c1")
    with pytest.raises(ValueError, match="not claimed"):
        market.deliver(listing.id, "c2", platform="p", content={},
                       publish_fn=lambda listing, content: "x")


# ── 8b. svg_path_tools ──────────────────────────────────────────────


def test_path_bbox_and_center():
    bbox = path_bbox("M0 0 L10 0 L10 10 Z")
    assert bbox["width"] == 10
    assert bbox["height"] == 10
    center = path_center("M0 0 L10 0 L10 10 Z")
    assert center == (5.0, 5.0)


def test_simplify_line_reduces_points():
    points = [(0, 0), (1, 0.1), (2, -0.05), (3, 0.02), (10, 0)]
    simplified = simplify_line(points, epsilon=1.0)
    assert len(simplified) < len(points)
    assert simplified[0] == points[0]
    assert simplified[-1] == points[-1]


def test_fit_smooth_cubic_g1():
    segs = fit_smooth_cubic([(0, 0), (10, 5), (20, 0)])
    assert len(segs) == 2
    # G1: 段1 的 control2 与段2 的 control1 共线 (同向)
    c2a = segs[0]["control2"]
    end = segs[0]["end"]
    c1b = segs[1]["control1"]
    vec1 = (end[0] - c2a[0], end[1] - c2a[1])
    vec2 = (c1b[0] - end[0], c1b[1] - end[1])
    dot = vec1[0] * vec2[0] + vec1[1] * vec2[1]
    assert dot > 0  # 同向


def test_render_cubic_path():
    d = render_cubic_path([(0, 0), (10, 5), (20, 0)])
    assert d.startswith("M0 0")
    assert "C" in d
