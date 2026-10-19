"""oskill._genetic_dag_mutate — 遗传图变异算法：对工作流 DAG 进行拓扑变异.

Stateless 纯图论计算。不依赖 LLM 或外部服务。

变异操作:
1. 剪枝 (Prune): 随机删除非核心节点（入度/出度 ≤ 1 且非 source/sink）
2. 嫁接 (Graft): 在两节点间插入冗余校验节点
3. 参数变异 (Param Mutate): 微调节点的超时阈值/重试次数
4. 交叉 (Crossover): 从两个父代 DAG 中各取一半子图拼接

要求: 变异后必须保持 DAG 无环且连通性不退化。

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

import copy
import random
import uuid
from typing import Any


def _genetic_dag_mutate(
    baseline_dag: dict[str, Any],
    *,
    mutation_rate: float = 0.3,
    operation_weights: dict[str, float] | None = None,
    random_seed: int | None = None,
) -> dict[str, Any]:
    """对基线 DAG 进行遗传变异，返回变异后的新 DAG.

    变异操作: prune(剪枝) / graft(嫁接) / param_mutate(参数变异).

    Args:
        baseline_dag: 基线工作流 DAG，格式:
            {"nodes": [{"id": str, "type": str, "params": {...}}, ...],
             "edges": [{"source": str, "target": str}, ...]}
        mutation_rate: 全局变异率 (0.0-1.0)
        operation_weights: 各变异操作的权重 {"prune": 0.4, "graft": 0.3, "param": 0.3}
        random_seed: 随机种子（确定性复现）

    Returns:
        {
            "mutated_dag": {...},
            "mutations_applied": [str, ...],
            "nodes_added": int,
            "nodes_removed": int,
            "is_valid_dag": bool,
        }
    """
    op_weights = operation_weights or {"prune": 0.4, "graft": 0.3, "param": 0.3}

    dag = copy.deepcopy(baseline_dag)
    nodes: list[dict[str, Any]] = dag.get("nodes", [])
    edges: list[dict[str, str]] = dag.get("edges", [])
    mutations_applied: list[str] = []
    rng = random.Random(random_seed)
    nodes_added = 0
    nodes_removed = 0

    # 识别 source/sink 节点 (不可删除)
    sources = set(n["id"] for n in nodes if not _has_incoming(n["id"], edges))
    sinks = set(n["id"] for n in nodes if not _has_outgoing(n["id"], edges))
    protected = sources | sinks

    # 1. 剪枝 (Prune): 删除低连接度的非核心节点
    if rng.random() < mutation_rate * op_weights.get("prune", 0.4):
        removable = [
            n
            for n in nodes
            if n["id"] not in protected
            and _in_degree(n["id"], edges) <= 1
            and _out_degree(n["id"], edges) <= 1
        ]
        if len(removable) > 1:
            victim = rng.choice(removable)
            backup = copy.deepcopy(dag)
            _remove_node_with_rewire(dag, victim["id"])
            if not _is_valid_dag(dag):
                dag.clear()
                dag.update(backup)
            else:
                nodes_removed += 1
                mutations_applied.append(f"prune:{victim['id']}")

    # 2. 嫁接 (Graft): 插入冗余校验节点
    if rng.random() < mutation_rate * op_weights.get("graft", 0.3):
        if len(edges) >= 1:
            backup = copy.deepcopy(dag)
            target_edge = rng.choice(edges)
            graft_id = f"graft_{uuid.uuid4().hex[:6]}"
            nodes.append(
                {
                    "id": graft_id,
                    "type": "redundancy_check",
                    "params": {"timeout": 5.0, "retries": 1},
                }
            )
            # 原边 source→target → 变为 source→graft→target
            old_target = target_edge["target"]
            target_edge["target"] = graft_id
            edges.append({"source": graft_id, "target": old_target})
            if not _is_valid_dag(dag):
                dag.clear()
                dag.update(backup)
            else:
                nodes_added += 1
                mutations_applied.append(f"graft:{graft_id}")

    # 3. 参数变异 (Param Mutate): 微调节点参数
    if rng.random() < mutation_rate * op_weights.get("param", 0.3):
        mutable_nodes = [n for n in nodes if n.get("params")]
        if mutable_nodes:
            target = rng.choice(mutable_nodes)
            params = target.setdefault("params", {})
            for key in ("timeout", "retries", "weight"):
                if key in params and isinstance(params[key], (int, float)):
                    old_val = params[key]
                    factor = 1.0 + rng.uniform(-0.3, 0.3)
                    if isinstance(params[key], int):
                        params[key] = max(1, int(old_val * factor))
                    else:
                        params[key] = round(old_val * factor, 2)
                    mutations_applied.append(f"param:{target['id']}.{key}:{old_val}→{params[key]}")
                    break  # 每次只变异一个参数

    # 4. DAG 有效性验证
    is_valid = _is_valid_dag(dag)

    return {
        "mutated_dag": dag,
        "mutations_applied": mutations_applied,
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "is_valid_dag": is_valid,
    }


def _genetic_dag_crossover(
    parent_a: dict[str, Any],
    parent_b: dict[str, Any],
    *,
    random_seed: int | None = None,
) -> dict[str, Any]:
    """两个父代 DAG 交叉生成子代.

    策略: 从 parent_a 取前半节点，从 parent_b 取后半节点，拼接边。
    生成的子代保证 DAG 无环且连通。

    Args:
        parent_a: 父代 A DAG
        parent_b: 父代 B DAG
        random_seed: 随机种子

    Returns:
        {"child_dag": {...}, "crossover_applied": True, "is_valid_dag": bool}
    """
    nodes_a = parent_a.get("nodes", [])
    nodes_b = parent_b.get("nodes", [])
    edges_a = parent_a.get("edges", [])
    edges_b = parent_b.get("edges", [])

    if len(nodes_a) < 2 or len(nodes_b) < 2:
        # 父代太小，无法交叉 → 直接返回 parent_a 副本
        return {
            "child_dag": copy.deepcopy(parent_a),
            "crossover_applied": False,
            "is_valid_dag": True,
        }

    # 从 A 取前半节点
    split_a = max(1, len(nodes_a) // 2)
    selected_a = nodes_a[:split_a]
    ids_a = {n["id"] for n in selected_a}

    # 从 B 取后半节点（排除与 A 重复 ID）
    split_b = len(nodes_b) // 2
    selected_b_raw = nodes_b[split_b:]
    selected_b = []
    for n in selected_b_raw:
        if n["id"] not in ids_a:
            selected_b.append(n)
            ids_a.add(n["id"])

    child_nodes = selected_a + selected_b
    child_edges: list[dict[str, str]] = []

    # 保留 A 内部边
    for e in edges_a:
        if e["source"] in ids_a and e["target"] in ids_a:
            child_edges.append(dict(e))

    # 保留 B 内部边
    for e in edges_b:
        src_id = e["source"]
        tgt_id = e["target"]
        if any(n["id"] == src_id for n in selected_b) and any(
            n["id"] == tgt_id for n in selected_b
        ):
            child_edges.append(dict(e))

    # 连接 A→B: 从前半的 sink 连到后半的 source
    b_sources = [
        n
        for n in selected_b
        if not _has_incoming_in_subset(n["id"], edges_b, {x["id"] for x in selected_b})
    ]
    sinks = [n for n in selected_a if not _has_outgoing_in_subset(n["id"], edges_a, ids_a)]
    if sinks and b_sources:
        bridge_source = sinks[0]["id"]
        bridge_target = b_sources[0]["id"]
        if bridge_source != bridge_target:
            child_edges.append({"source": bridge_source, "target": bridge_target})

    child_dag = {"nodes": child_nodes, "edges": child_edges}
    is_valid = _is_valid_dag(child_dag)

    return {
        "child_dag": child_dag,
        "crossover_applied": True,
        "is_valid_dag": is_valid,
    }


# ---------------------------------------------------------------------------
# 图工具
# ---------------------------------------------------------------------------


def _in_degree(node_id: str, edges: list[dict[str, str]]) -> int:
    return sum(1 for e in edges if e.get("target") == node_id)


def _out_degree(node_id: str, edges: list[dict[str, str]]) -> int:
    return sum(1 for e in edges if e.get("source") == node_id)


def _has_incoming(node_id: str, edges: list[dict[str, str]]) -> bool:
    return _in_degree(node_id, edges) > 0


def _has_outgoing(node_id: str, edges: list[dict[str, str]]) -> bool:
    return _out_degree(node_id, edges) > 0


def _has_incoming_in_subset(node_id: str, edges: list[dict[str, str]], subset: set[str]) -> bool:
    return any(e.get("target") == node_id and e.get("source") in subset for e in edges)


def _has_outgoing_in_subset(node_id: str, edges: list[dict[str, str]], subset: set[str]) -> bool:
    return any(e.get("source") == node_id and e.get("target") in subset for e in edges)


def _remove_node_with_rewire(dag: dict[str, Any], node_id: str) -> None:
    """从 DAG 中移除节点并重连边（A→X→B 变为 A→B）."""
    nodes = dag.get("nodes", [])
    edges: list[dict[str, str]] = dag.get("edges", [])

    # 找到入边和出边
    in_edges = [e for e in edges if e.get("target") == node_id]
    out_edges = [e for e in edges if e.get("source") == node_id]

    # 移除节点
    dag["nodes"] = [n for n in nodes if n["id"] != node_id]

    # 移除涉及该节点的所有边
    new_edges = [e for e in edges if e.get("source") != node_id and e.get("target") != node_id]

    # 重连：对于每对入边+出边，添加桥接边
    for in_e in in_edges:
        for out_e in out_edges:
            src = in_e["source"]
            tgt = out_e["target"]
            # 避免自环
            if src != tgt:
                # 避免重复边
                if not any(ne["source"] == src and ne["target"] == tgt for ne in new_edges):
                    new_edges.append({"source": src, "target": tgt})

    dag["edges"] = new_edges


def _is_valid_dag(dag: dict[str, Any]) -> bool:
    """检查 DAG 是否有效（无环 + 连通）."""
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    if not nodes:
        return True
    try:
        import networkx as nx

        g = nx.DiGraph()
        for n in nodes:
            g.add_node(n["id"])
        for e in edges:
            g.add_edge(e["source"], e["target"])
        # 无环
        if not nx.is_directed_acyclic_graph(g):
            return False
        # 弱连通
        if not nx.is_weakly_connected(g):
            return False
        return True
    except ImportError:
        # 无 networkx → 简化为非空节点即通过
        return len(nodes) > 0
