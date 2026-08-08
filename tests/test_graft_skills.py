"""Tests for code_graph_semantic / agent_wiring (NanoNets/Graft 3O 内化)。"""

from __future__ import annotations

from pathlib import Path

from oskill.agent_wiring import (
    list_agents,
    plan_wiring,
    write_agent_instructions,
)
from oskill.code_graph_semantic import (
    LINK_DEPENDS_ON,
    LINK_PART_OF,
    LINK_PRODUCES,
    SemanticBuild,
    SemanticNode,
    SourceRef,
    build_fingerprint,
    content_hash,
    incremental_refresh,
    parse_wikilinks,
    render_node_markdown,
    semantic_build,
    stale_nodes,
)

# ── 哈希与指纹 ───────────────────────────────────────────────────────


def test_content_hash_deterministic():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_build_fingerprint(tmp_path: Path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    fp = build_fingerprint([f])
    assert fp[str(f)] == content_hash("x = 1\n")
    # 变更后指纹变化
    f.write_text("x = 2\n", encoding="utf-8")
    assert build_fingerprint([f])[str(f)] != fp[str(f)]


def test_stale_nodes_detects_change(tmp_path: Path):
    f = tmp_path / "a.py"
    f.write_text("v1", encoding="utf-8")
    node = SemanticNode(name="n", summary="s", sources=[SourceRef(str(f), content_hash("v1"))])
    build = SemanticBuild(nodes={"n": node})
    assert stale_nodes(build, [f]) == []
    f.write_text("v2", encoding="utf-8")
    assert stale_nodes(build, [f]) == ["n"]


# ── 两遍构建 ─────────────────────────────────────────────────────────


def test_semantic_build_two_passes(tmp_path: Path):
    f1 = tmp_path / "mod_a.py"
    f1.write_text("def a(): pass\n", encoding="utf-8")
    f2 = tmp_path / "mod_b.py"
    f2.write_text("def b(): pass\n", encoding="utf-8")

    def summarize(path: str, content: str) -> str:
        return f"摘要: {Path(path).name}"

    def cluster(summaries: dict[str, str]) -> dict[str, SemanticNode]:
        node = SemanticNode(name="core", summary="; ".join(summaries.values()))
        for path in summaries:
            node.sources.append(SourceRef(path, content_hash("fake")))
        node.add_link(LINK_DEPENDS_ON, "util")
        return {"core": node}

    build = semantic_build([f1, f2], summarize=summarize, cluster=cluster)
    assert "core" in build.nodes
    assert "mod_a.py" in build.nodes["core"].summary
    assert build.nodes["core"].links[LINK_DEPENDS_ON] == ["util"]
    assert len(build.fingerprint) == 2


# ── 增量刷新 ─────────────────────────────────────────────────────────


def test_incremental_refresh_only_changed(tmp_path: Path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("v1", encoding="utf-8")
    f2.write_text("v1", encoding="utf-8")
    calls: list[str] = []

    def summarize(path: str, content: str) -> str:
        calls.append(path)
        return f"s:{Path(path).name}"

    def cluster(summaries: dict[str, str]) -> dict[str, SemanticNode]:
        node = SemanticNode(name="core", summary=", ".join(summaries.values()))
        for path in summaries:
            node.sources.append(SourceRef(path, content_hash("v1")))
        return {"core": node}

    build = semantic_build([f1, f2], summarize=summarize, cluster=cluster)
    assert len(calls) == 2

    # 只改 b.py → b 重新摘要 (a 复用), fingerprint 更新
    f2.write_text("v2", encoding="utf-8")
    refreshed = incremental_refresh(build, [f1, f2], summarize)
    # a 未变: 未被重新摘要 (calls 只增 1); b 变更: 新增独立节点
    assert any(c.endswith("b.py") for c in calls[2:])
    assert not any(c.endswith("a.py") for c in calls[2:])
    assert refreshed.fingerprint[str(f2)] == content_hash("v2")


# ── Markdown 渲染 ────────────────────────────────────────────────────


def test_render_node_markdown_blocks():
    node = SemanticNode(
        name="core",
        summary="处理核心逻辑",
        crux="if quota <= 0: return\n",
        sources=[SourceRef("src/core.py", "abc123")],
        notes="用户备注",
    )
    node.add_link(LINK_PART_OF, "system")
    node.add_link(LINK_PRODUCES, "report")
    md = render_node_markdown(node)
    assert "## Summary" in md and "处理核心逻辑" in md
    assert "## Crux" in md and "if quota <= 0" in md
    assert "src/core.py" in md
    assert "[[system]]" in md and "[[report]]" in md
    assert "用户备注" in md


def test_parse_wikilinks():
    md = "a [[node-a]] b [[node-b|别名]] c"
    assert parse_wikilinks(md) == ["node-a", "node-b"]


def test_invalid_link_type_raises():
    import pytest

    node = SemanticNode(name="n")
    with pytest.raises(ValueError, match="invalid link type"):
        node.add_link("unknown", "x")


# ── agent_wiring: 多 agent 指令集成 ──────────────────────────────────


def test_plan_wiring_dry_run(tmp_path: Path):
    results = plan_wiring("Use the graph.", root=tmp_path, agents=["agents", "claude"])
    by_agent = {r.agent: r for r in results}
    assert by_agent["agents"].file == "AGENTS.md"
    assert by_agent["claude"].file.endswith(".claude/skills/veya/SKILL.md")
    assert by_agent["agents"].action == "written"


def test_write_agent_instructions_shared_file(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("# 项目说明\n\n用户内容\n", encoding="utf-8")
    write_agent_instructions(
        "Use the semantic graph.",
        root=tmp_path,
        agents=["agents"],
        skill_name="graft",
    )
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- graft:start -->" in text
    assert "Use the semantic graph." in text
    assert "用户内容" in text  # 用户内容保留
    assert text.index("graft:start") > text.index("用户内容")  # 追加在末尾


def test_write_agent_instructions_updates_marker_in_place(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text(
        "<!-- graft:start -->\nold\n<!-- graft:end -->\n", encoding="utf-8"
    )
    write_agent_instructions(
        "new instructions",
        root=tmp_path,
        agents=["agents"],
        skill_name="graft",
    )
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "new instructions" in text
    assert "old" not in text  # 原位替换


def test_write_owned_file(tmp_path: Path):
    write_agent_instructions(
        "Claude skill content",
        root=tmp_path,
        agents=["claude"],
        skill_name="veya",
    )
    skill = tmp_path / ".claude" / "skills" / "veya" / "SKILL.md"
    assert skill.exists()
    assert "Claude skill content" in skill.read_text(encoding="utf-8")


def test_list_agents_known():
    agents = list_agents()
    assert {"agents", "gemini", "copilot", "claude", "cursor", "windsurf"} <= set(agents)


def test_unknown_agent_skipped(tmp_path: Path):
    results = write_agent_instructions("x", root=tmp_path, agents=["nope"], dry_run=True)
    assert results[0].action == "skipped"
