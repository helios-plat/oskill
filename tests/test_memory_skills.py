"""Tests for rrf_retrieval / memory_layers / memory_assets (TencentDB 3O 内化)。"""

from __future__ import annotations

from oskill.memory_assets import (
    ACL,
    VISIBILITY_PRIVATE,
    VISIBILITY_RESTRICTED,
    VISIBILITY_TEAM,
    AssetRegistry,
    MemoryAsset,
    Principal,
)
from oskill.memory_layers import (
    ATOM_FACT,
    ATOM_PREFERENCE,
    DistillPipeline,
    L1Atom,
    L2Scenario,
    L3Persona,
)
from oskill.rrf_retrieval import (
    RetrievalBudget,
    bm25_score,
    hybrid_search,
    rrf_merge,
    tokenize,
)

# ── RRF 混合检索 ─────────────────────────────────────────────────────


def test_tokenize_bigram():
    assert "天气" in tokenize("今天天气如何")
    assert "refactor" in tokenize("Refactor legacy code")


def test_bm25_score_basic():
    df = {"a": 1, "b": 5}
    score = bm25_score(["a"], ["a", "a", "b"], df=df, n_docs=10, avg_dl=3)
    assert score > 0
    # 无关查询 → 0
    assert bm25_score(["zzz"], ["a", "b"], df=df, n_docs=10, avg_dl=3) == 0


def test_rrf_merge_shared_ranked_higher():
    lists = [
        [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}],
        [{"id": "b", "text": "y"}],
    ]
    merged = rrf_merge(lists)
    assert merged[0]["id"] == "b"  # 双路命中排名更高
    assert "rrf_score" in merged[0]


def test_hybrid_search_budget_cap():
    fts = [{"id": f"f{i}", "text": "x" * 100} for i in range(10)]
    vec = [{"id": f"f{i}", "text": "x" * 100} for i in range(10)]
    results = hybrid_search(fts, vec, budget=RetrievalBudget(max_items=3, max_chars=10_000))
    assert len(results) == 3  # max_items 截断


def test_hybrid_search_char_cap():
    fts = [{"id": f"f{i}", "text": "y" * 500} for i in range(5)]
    vec = []
    results = hybrid_search(fts, vec, budget=RetrievalBudget(max_items=10, max_chars=900))
    assert len(results) <= 2  # 900 chars / 500 per item


# ── L0-L3 分层蒸馏 ───────────────────────────────────────────────────


def _pipeline() -> DistillPipeline:
    return DistillPipeline(l1_threshold=2, l2_threshold=2, score_threshold=3.0)


def test_record_and_trigger():
    pipe = _pipeline()
    pipe.record("用户喜欢 Python")
    assert pipe.should_distill() is False  # 1 < 2
    pipe.record("用户偏好异步代码")
    assert pipe.should_distill() is True  # 2 >= 2


def test_distill_l1_with_score():
    pipe = _pipeline()
    pipe.record("用户喜欢 Python")

    def l1_fn(entries):
        return [
            L1Atom(
                kind=ATOM_PREFERENCE, text="偏好 Python", score=8.0, source_entry=entries[0].text
            )
        ]

    atoms = pipe.distill_l1(l1_fn)
    assert len(atoms) == 1
    assert atoms[0].kind == ATOM_PREFERENCE
    assert atoms[0].score == 8.0
    assert pipe.pending_l1 == []  # 队列清空
    assert pipe.summary()["atoms"] == 1


def test_build_scenario_and_persona():
    pipe = _pipeline()
    pipe.record("用户喜欢 Python")

    def l1_fn(entries):
        return [
            L1Atom(kind=ATOM_PREFERENCE, text="偏好 Python", score=8.0),
            L1Atom(kind=ATOM_FACT, text="技术栈是 FastAPI", score=7.0),
        ]

    pipe.distill_l1(l1_fn)
    assert pipe.should_build_scenario() is True

    def l2_fn(unassigned):
        return [
            L2Scenario(
                id="s1",
                title="技术栈",
                content="用户技术偏好",
                atom_ids=[unassigned[0].text, unassigned[1].text],
            )
        ]

    scenarios = pipe.build_scenarios(l2_fn)
    assert len(scenarios) == 1
    assert pipe.scenarios["s1"].title == "技术栈"

    pipe.stabilize_persona(lambda scenarios: L3Persona(profile="资深 Python 开发者"))
    assert "Python" in pipe.recall_quick()
    assert "[Persona]" in pipe.recall_quick()


def test_recall_atoms_score_filter():
    pipe = _pipeline()
    pipe.record("x")
    pipe.distill_l1(
        lambda entries: [
            L1Atom(kind=ATOM_FACT, text="高价值", score=9.0),
            L1Atom(kind=ATOM_FACT, text="低价值", score=1.0),
        ]
    )
    atoms = pipe.recall_atoms()
    assert [a.text for a in atoms] == ["高价值"]  # score >= 3.0


# ── 记忆资产 + ACL + loadout ─────────────────────────────────────────


def test_visibility_access():
    registry = AssetRegistry(team_members=["alice", "bob"])
    registry.register(MemoryAsset(id="m1", owner="alice", visibility=VISIBILITY_PRIVATE))
    registry.register(MemoryAsset(id="m2", owner="alice", visibility=VISIBILITY_TEAM))
    assert registry.check_access(registry.assets["m1"], Principal("alice")) is True
    assert registry.check_access(registry.assets["m1"], Principal("bob")) is False  # private
    assert registry.check_access(registry.assets["m2"], Principal("bob")) is True  # team


def test_restricted_acl():
    registry = AssetRegistry()
    asset = MemoryAsset(
        id="m3",
        owner="alice",
        visibility=VISIBILITY_RESTRICTED,
        acl=ACL(users=["carol"], roles=["reviewer"], agents=["builder-1"]),
    )
    registry.register(asset)
    assert registry.check_access(asset, Principal("carol")) is True
    assert registry.check_access(asset, Principal("dave", roles=["reviewer"])) is True
    assert registry.check_access(asset, Principal("eve")) is False


def test_loadout_binding_and_filter():
    registry = AssetRegistry(team_members=["alice"])
    registry.register(MemoryAsset(id="codegraph", owner="alice", visibility=VISIBILITY_TEAM))
    registry.register(MemoryAsset(id="secret", owner="alice", visibility=VISIBILITY_PRIVATE))
    registry.register(MemoryAsset(id="skill1", owner="alice", visibility=VISIBILITY_TEAM))

    loadout = registry.assemble_loadout(
        "builder-1",
        Principal("alice"),
        bindings={"builder-1": ["codegraph", "secret", "skill1"]},
        priorities={"codegraph": 3.0, "skill1": 1.0},
    )
    ids = [a.id for a in loadout]
    assert "secret" in ids  # owner 可见 private
    assert loadout[0].id == "codegraph"  # 高优先级在前

    # 非 owner 的 loadout: private 被过滤
    loadout_bob = registry.assemble_loadout(
        "builder-1",
        Principal("bob"),
        bindings={"builder-1": ["codegraph", "secret"]},
    )
    assert "secret" not in [a.id for a in loadout_bob]


def test_asset_version_increment():
    registry = AssetRegistry()
    asset = MemoryAsset(id="a1", title="v1")
    registry.register(asset)
    registry.register(MemoryAsset(id="a1", title="v2"))
    assert registry.assets["a1"].version == 2
    assert registry.summary()["assets"] == 1
