"""Tests for knowledge_graph_query / pentest_loop (Graphify / Strix 3O 内化)。"""

from __future__ import annotations

from oskill.code_graph_semantic import (
    LINK_DEPENDS_ON,
    SemanticBuild,
    SemanticNode,
    SourceRef,
)
from oskill.knowledge_graph_query import (
    EDGE_EXTRACTED,
    EDGE_INFERRED,
    GraphNode,
    KnowledgeGraph,
    semantic_to_graph,
)
from oskill.pentest_loop import (
    PHASE_EXPLOIT,
    PHASE_RECON,
    Finding,
    PentestReport,
    run_pentest_loop,
    verify_finding,
)

# ── KnowledgeGraph: 图遍历 ───────────────────────────────────────────


def _graph() -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for nid in ("a", "b", "c", "d"):
        graph.add_node(GraphNode(nid, label=nid.upper(), kind="concept"))
    graph.add_edge("a", "b", kind=LINK_DEPENDS_ON, trust=EDGE_EXTRACTED, evidence="import")
    graph.add_edge("b", "c", kind=LINK_DEPENDS_ON, trust=EDGE_EXTRACTED, evidence="import")
    graph.add_edge("c", "d", kind="related", trust=EDGE_INFERRED, evidence="similar name")
    return graph


def test_neighbors_and_trust_filter():
    graph = _graph()
    assert {n.id for n in graph.neighbors("b")} == {"a", "c"}
    # INFERRED 过滤: b 无 INFERRED 边
    assert graph.neighbors("b", trust=EDGE_INFERRED) == []
    assert {n.id for n in graph.neighbors("c", trust=EDGE_INFERRED)} == {"d"}


def test_shortest_path_bfs():
    graph = _graph()
    assert graph.shortest_path("a", "d") == ["a", "b", "c", "d"]
    assert graph.shortest_path("a", "c") == ["a", "b", "c"]
    assert graph.shortest_path("a", "a") == ["a"]
    assert graph.shortest_path("a", "nope") == []


def test_trace_with_evidence():
    graph = _graph()
    result = graph.trace("a", "c")
    assert result["found"] is True
    assert result["path"] == ["a", "b", "c"]
    assert result["edges"][0]["trust"] == EDGE_EXTRACTED
    assert result["edges"][0]["evidence"] == "import"


def test_communities_label_propagation():
    graph = _graph()
    communities = graph.communities()
    # a-b-c-d 是链, 社区数应 <= 2
    assert len(communities) >= 1
    members = {n for members in communities.values() for n in members}
    assert members == {"a", "b", "c", "d"}


def test_export_json():
    graph = _graph()
    data = graph.export_json()
    assert data["stats"]["nodes"] == 4
    assert data["stats"]["extracted"] == 2
    assert data["stats"]["inferred"] == 1


def test_invalid_edge_raises():
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("a"))
    import pytest

    with pytest.raises(KeyError):
        graph.add_edge("a", "nope")
    with pytest.raises(ValueError, match="invalid trust"):
        graph.add_edge("a", "a", trust="maybe")


# ── 与 code_graph_semantic 组合 ──────────────────────────────────────


def test_semantic_to_graph_marking():
    build = SemanticBuild()
    a = SemanticNode(name="core", summary="s")
    b = SemanticNode(name="util", summary="s")
    c = SemanticNode(name="shared", summary="s")
    a.sources.append(SourceRef("src/x.py", "h1"))
    b.sources.append(SourceRef("src/x.py", "h1"))  # 与 a 共享来源
    c.sources.append(SourceRef("src/x.py", "h1"))  # 与 a/b 共享来源 (core↔shared 无边 → INFERRED)
    a.add_link(LINK_DEPENDS_ON, "util")
    build.nodes = {"core": a, "util": b, "shared": c}

    graph = semantic_to_graph(build)
    # EXTRACTED: semantic link
    extracted = [e for e in graph.edges if e.trust == EDGE_EXTRACTED]
    assert extracted and extracted[0].kind == LINK_DEPENDS_ON
    # INFERRED: 共享来源共现 (core↔util 已有显式边被去重, 无边的对生成 INFERRED)
    inferred = [e for e in graph.edges if e.trust == EDGE_INFERRED]
    assert inferred and inferred[0].kind == "co_occurrence"
    stats = graph.export_json()["stats"]
    assert stats["extracted"] == 1
    assert stats["inferred"] >= 1


# ── PentestLoop: 阶段机 + 验证门 ─────────────────────────────────────


def test_verify_gate_confirmed():
    finding = Finding(title="SQLi", proof_of_concept="curl ...")
    verified = verify_finding(finding, verifier=lambda f: True, evidence="response 200")
    assert verified.status == "confirmed"
    assert "response 200" in verified.evidence


def test_verify_gate_rejects_false_positive():
    finding = Finding(title="SQLi", proof_of_concept="curl ...")
    verified = verify_finding(finding, verifier=lambda f: False)
    assert verified.status == "rejected"


def test_verify_gate_exception_rejects():
    finding = Finding(title="x")

    def boom(f):
        raise RuntimeError("no")

    assert verify_finding(finding, verifier=boom).status == "rejected"


def test_pentest_loop_full():
    calls = {"recon": 0, "exploit": 0, "verify": 0}

    def recon(target):
        calls["recon"] += 1
        return {"hosts": [target]}

    def exploit(target, recon_output):
        calls["exploit"] += 1
        return [
            Finding(title="真漏洞", severity="high", proof_of_concept="poc1"),
            Finding(title="误报", severity="low", proof_of_concept="poc2"),
        ]

    def verifier(finding):
        calls["verify"] += 1
        return finding.title == "真漏洞"

    report = run_pentest_loop("http://target", recon=recon, exploit=exploit, verifier=verifier)
    assert calls["recon"] == calls["exploit"] == 1
    assert calls["verify"] == 2
    assert report.vulnerable is True
    assert len(report.confirmed) == 1
    assert report.confirmed[0].title == "真漏洞"


def test_pentest_report_markdown_and_sarif():
    report = PentestReport(
        target="http://x",
        findings=[
            Finding(
                title="SQLi",
                severity="high",
                description="注入",
                proof_of_concept="' OR 1=1",
                remediation="参数化查询",
                status="confirmed",
            ),
            Finding(title="误报", status="rejected"),
        ],
    )
    md = report.markdown()
    assert "SQLi" in md and "参数化查询" in md
    assert "误报" not in md  # rejected 不进报告
    sarif = report.sarif()
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"][0]["results"]) == 1
    assert sarif["runs"][0]["results"][0]["level"] == "error"  # high → error


def test_pentest_loop_clean():
    report = run_pentest_loop(
        "http://safe",
        recon=lambda t: {},
        exploit=lambda t, o: [Finding(title="疑似")],
        verifier=lambda f: False,
    )
    assert report.vulnerable is False
    assert "未发现已确认漏洞" in report.summary


def test_phase_contract():
    from oskill.pentest_loop import PHASES, PentestState

    state = PentestState(target="t")
    assert state.phase == PHASE_RECON
    assert state.next_action() == "run_recon"
    assert len(PHASES) == 4
    state.phase = PHASE_EXPLOIT
    assert state.next_action() == "run_exploit"
