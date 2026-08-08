"""Tests for rag_pipeline / content_moderation / conversation_vars /
code_graph_builder / triage_flow / health_probe (剩余价值批次)。"""

from __future__ import annotations

import pytest

from oskill.code_graph_builder import CodeGraphBuilder
from oskill.content_moderation import (
    ModerationRule,
    moderate,
    moderate_with_llm,
)
from oskill.conversation_vars import SCOPE_PROJECT, ConversationVars
from oskill.health_probe import (
    STATUS_HEALTHY,
    STATUS_INVALID,
    STATUS_RATE_LIMITED,
    HealthMonitor,
    HealthProbe,
)
from oskill.rag_pipeline import (
    RagIndex,
    build_rag_pipeline,
    chunk_text,
    clean_document,
)
from oskill.triage_flow import (
    STATUS_NEEDS_INFO,
    STATUS_READY_AGENT,
    STATUS_WONTFIX,
    TriageFlow,
    TriageIssue,
)

# ── rag_pipeline ────────────────────────────────────────────────────


def test_clean_document_folds_blank_lines():
    text = "para1\n\n\n\npara2\n\n\npara3"
    cleaned = clean_document(text)
    assert "\n\n\n" not in cleaned


def test_clean_document_dedup_paragraphs():
    text = "long paragraph here " + "x" * 50 + "\nlong paragraph here " + "x" * 50
    cleaned = clean_document(text)
    assert cleaned.count("long paragraph") == 1


def test_chunk_text_paragraph_boundary():
    text = "p1\n\np2\n\np3"
    chunks = chunk_text(text, max_chars=1000, overlap=0)
    assert len(chunks) == 1  # 全部在 max_chars 内


def test_chunk_text_overlong():
    text = "y" * 2000
    chunks = chunk_text(text, max_chars=800, overlap=0)
    assert len(chunks) >= 3


def test_build_rag_pipeline_and_bm25(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# 文档\n\nveya 是一个 agent 框架\n\n" + "z" * 500, encoding="utf-8")
    chunks, index = build_rag_pipeline([f], max_chars=800, overlap=0)
    assert index.stats()["chunks"] >= 1
    hits = index.bm25_retrieve("veya agent")
    assert hits  # BM25 命中


def test_rag_index_vector_retrieve():
    index = RagIndex()
    from oskill.rag_pipeline import Chunk

    index.add_chunks(
        [
            Chunk("c1", "apple fruit"),
            Chunk("c2", "car engine"),
        ],
        embed_fn=lambda t: [1.0 if "fruit" in t else 0.0, 1.0 if "engine" in t else 0.0],
    )
    hits = index.vector_retrieve("fruit", embed_fn=lambda t: [1.0, 0.0])
    assert hits[0].id == "c1"


# ── content_moderation ──────────────────────────────────────────────


def test_moderate_keyword_block():
    verdict = moderate("this has badword", [ModerationRule("k", "keyword", pattern=["badword"])])
    assert verdict.passed is False
    assert verdict.blocked_rules == ["k"]


def test_moderate_keyword_replace():
    verdict = moderate(
        "badword here", [ModerationRule("k", "keyword", pattern=["badword"], action="replace")]
    )
    assert verdict.passed is True
    assert "badword" not in verdict.text


def test_moderate_length_limit():
    verdict = moderate("x" * 100, [ModerationRule("len", "length", limit=50)])
    assert verdict.passed is False


def test_moderate_repeat_detection():
    verdict = moderate("aaaaab", [ModerationRule("rep", "repeat", limit=5)])
    assert verdict.passed is False


def test_moderate_with_llm_rules_then_llm():
    verdict = moderate_with_llm(
        "clean text",
        lambda t: {"passed": False},
        rules=[ModerationRule("k", "keyword", pattern=["badword"])],
    )
    assert verdict.passed is False
    assert "llm" in verdict.blocked_rules


# ── conversation_vars ───────────────────────────────────────────────


def test_conversation_vars_set_get_version():
    vars_store = ConversationVars()
    vars_store.set("name", "veya")
    vars_store.set("name", "veya2")
    assert vars_store.get("name") == "veya2"
    assert vars_store.get_entry("name").version == 2


def test_conversation_vars_ttl_expiry():
    vars_store = ConversationVars()
    vars_store.set("tmp", "x", ttl_s=1)
    assert vars_store.get("tmp") == "x"
    vars_store.get_entry("tmp").expires_at = 0  # 强制过期
    assert vars_store.get("tmp") is None


def test_conversation_vars_scope_snapshot():
    vars_store = ConversationVars()
    vars_store.set("a", 1, scope=SCOPE_PROJECT)
    vars_store.set("b", 2)
    snapshot = vars_store.snapshot(scope=SCOPE_PROJECT)
    assert snapshot == {"a": 1}


# ── code_graph_builder ─────────────────────────────────────────────


def test_build_graph_full(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("def a(): pass\n", encoding="utf-8")
    f2.write_text("def b(): pass\n", encoding="utf-8")
    builder = CodeGraphBuilder()

    def summarize(path, content):
        return f"summary:{path}"

    def cluster(summaries):
        from oskill.code_graph_semantic import SemanticNode, SourceRef, content_hash

        node = SemanticNode(name="core", summary="; ".join(summaries.values()))
        for path in summaries:
            node.sources.append(SourceRef(path, content_hash("x")))
        return {"core": node}

    build = builder.build_graph([f1, f2], summarize=summarize, cluster=cluster)
    assert build.nodes["core"].summary  # 两文件摘要
    assert builder.stats.files_summarized == 2


def test_incremental_build_caches_unchanged(tmp_path):
    f1 = tmp_path / "a.py"
    f1.write_text("v1", encoding="utf-8")
    builder = CodeGraphBuilder()

    def summarize(path, content):
        return f"s:{content}"

    def cluster(summaries):
        from oskill.code_graph_semantic import SemanticNode, SourceRef, content_hash

        node = SemanticNode(name="n", summary="; ".join(summaries.values()))
        for path in summaries:
            node.sources.append(SourceRef(path, content_hash("x")))
        return {"n": node}

    builder.build_graph([f1], summarize=summarize, cluster=cluster)
    # 变更文件
    f1.write_text("v2", encoding="utf-8")
    build = builder.incremental_build([f1], summarize=summarize, cluster=cluster)
    assert builder.stats.files_summarized >= 1
    assert "v2" in build.nodes["n"].summary or "v2" in str(build.nodes["n"])


def test_build_graph_export_knowledge_graph(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("def a(): pass\n", encoding="utf-8")
    builder = CodeGraphBuilder()

    def summarize(path, content):
        return "s"

    def cluster(summaries):
        from oskill.code_graph_semantic import SemanticNode

        return {"n1": SemanticNode(name="n1", summary="s")}

    builder.build_graph([f], summarize=summarize, cluster=cluster)
    graph = builder.export_knowledge_graph()
    assert "n1" in graph.nodes


# ── triage_flow ─────────────────────────────────────────────────────


def test_triage_full_flow():
    flow = TriageFlow()
    issue = flow.add_issue(TriageIssue(title="bug", description="crash"))
    assert issue.status == "needs-triage"
    flow.transition(issue.id, STATUS_NEEDS_INFO)
    flow.transition(issue.id, STATUS_READY_AGENT)
    assert flow.agent_ready(issue.id)["ready"] is True


def test_triage_illegal_transition():
    flow = TriageFlow()
    issue = flow.add_issue(TriageIssue(title="t", description="d"))
    flow.transition(issue.id, STATUS_WONTFIX)  # 终态
    with pytest.raises(ValueError, match="illegal transition"):
        flow.transition(issue.id, STATUS_READY_AGENT)  # wontfix → 任何都非法


def test_triage_agent_ready_blockers():
    flow = TriageFlow()
    issue = flow.add_issue(TriageIssue(title="t", description=""))  # 无描述
    assert flow.agent_ready(issue.id)["ready"] is False
    assert "无描述" in flow.agent_ready(issue.id)["blockers"]


def test_triage_wontfix_not_ready():
    flow = TriageFlow()
    issue = flow.add_issue(TriageIssue(title="t", description="d"))
    flow.transition(issue.id, STATUS_WONTFIX)
    assert flow.agent_ready(issue.id)["ready"] is False
    assert "wontfix" in flow.agent_ready(issue.id)["blockers"]


# ── health_probe ────────────────────────────────────────────────────


def test_probe_updates_state():
    probe = HealthProbe("key1", lambda: STATUS_HEALTHY, cooldown_s=0)
    assert probe.probe() == STATUS_HEALTHY
    assert probe.state.observations == 1


def test_probe_cooldown_skips():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        return STATUS_RATE_LIMITED

    probe = HealthProbe("key1", flaky, cooldown_s=1000)
    probe.probe()
    assert probe.state.status == STATUS_RATE_LIMITED
    assert probe.probe() == STATUS_RATE_LIMITED  # 冷却中复用
    assert calls["n"] == 1  # 第二次未执行探测


def test_monitor_summary():
    monitor = HealthMonitor()
    monitor.register(HealthProbe("a", lambda: STATUS_HEALTHY, cooldown_s=0))
    monitor.register(HealthProbe("b", lambda: STATUS_INVALID, cooldown_s=0))
    summary = monitor.run_once()
    assert summary["healthy"] == ["a"]
    assert summary["counts"][STATUS_INVALID] == 1
