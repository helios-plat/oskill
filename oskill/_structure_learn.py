"""oskill._structure_learn — 结构学习：基于干预历史对因果图边做增/删/重加权（保守阈值）.

组合（≥2 个 oprim 思想的算法组合）:
- oprim._do_calculus_intervention 的图手术视角（干预 = 对 target 施术，观察 outcome 变化）
- 干预历史聚合统计（支持/反例计数）
- 图边更新（增/删/重加权，全部保守阈值约束）

保守策略:
- 加边: 正向干预证据支持数 >= min_support，且加边后图仍为 DAG
- 删边: 反例数 >= delete_threshold 且反例 >= 支持（不轻易删）
- 重加权: 单次步长 <= max_step，权重 clamp 到 [min_weight, 1.0]

interventions 形如（支持/反例的聚合依据）:
    {"target": "llm_call", "outcome": "latency", "delta": -0.35, "support": 8, "success": true}
    (delta < 0 且 success → 支持 target→outcome 为因果边；delta >= 0 → 反例)

图对象由调用方持有/持久化（如 obase.persistent_store 的 CausalGraphDoc / obase.causal_graph_store.CausalGraphStore）。
stateless：本函数不持有状态。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["structure_learn", "update_cpd", "LearnableGraph"]


@runtime_checkable
class LearnableGraph(Protocol):
    """可学习因果图协议（兼容 obase.causal_graph_store.CausalGraphStore）。"""

    def has_edge(self, cause: str, effect: str) -> bool: ...
    def add_edge(self, cause: str, effect: str, **attrs: Any) -> None: ...
    def remove_edge(self, cause: str, effect: str) -> None: ...
    def is_dag(self) -> bool: ...


def _current_weight(dag: LearnableGraph, u: str, v: str) -> float:
    """读取边权重（图无权重时默认 0.5 = 未知强度；写入用 add_edge(..., weight=w) 覆盖）。"""
    reader = getattr(dag, "edge_weight", None)
    if callable(reader):
        try:
            return float(reader(u, v))
        except Exception:  # noqa: BLE001 — 无权重图回退
            pass
    return 0.5


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def structure_learn(
    causal_dag: LearnableGraph,
    *,
    interventions: list[dict[str, Any]],
    min_support: int = 3,
    delete_threshold: int = 5,
    max_step: float = 0.1,
    min_weight: float = 0.05,
) -> dict[str, Any]:
    """基于干预历史对因果图做保守结构更新。

    Args:
        causal_dag: 实现 LearnableGraph 的因果图（增删边/无环检查）。
        interventions: 干预历史（见模块 docstring）。
        min_support: 加边所需的最小正向证据数。
        delete_threshold: 删边所需的最小反例数。
        max_step: 单次重加权步长上限。
        min_weight: 边权重下限。

    Returns:
        {
            "added": [(u, v)],
            "removed": [(u, v)],
            "reweighted": [(u, v, old_w, new_w)],
            "blocked": [(u, v)]  // 支持够但加边会成环
        }
    """
    added: list[tuple[str, str]] = []
    removed: list[tuple[str, str]] = []
    reweighted: list[tuple[str, str, float, float]] = []
    blocked: list[tuple[str, str]] = []

    # 聚合干预证据：候选边 (target, outcome) → (positive, negative)
    evidence: dict[tuple[str, str], list[int]] = {}
    for itv in interventions:
        t = str(itv.get("target", ""))
        o = str(itv.get("outcome", ""))
        if not t or not o or t == o:
            continue
        support = int(itv.get("support", 1))
        delta = float(itv.get("delta", 0.0))
        success = bool(itv.get("success", delta < 0))
        if delta < 0 and success:
            evidence.setdefault((t, o), [0, 0])[0] += max(1, support)
        else:
            evidence.setdefault((t, o), [0, 0])[1] += max(1, support)

    for (t, o), (positive, negative) in evidence.items():
        exists = causal_dag.has_edge(t, o)
        if exists:
            if positive >= min_support and positive > negative:
                old_w = _current_weight(causal_dag, t, o)
                new_w = _clamp(old_w + max_step, min_weight, 1.0)
                causal_dag.add_edge(t, o, weight=new_w)
                reweighted.append((t, o, old_w, new_w))
            elif negative >= delete_threshold and negative >= positive:
                causal_dag.remove_edge(t, o)
                removed.append((t, o))
        else:
            if positive >= min_support and positive > negative:
                # 加边前验证无环：试加 → is_dag 检查 → 回滚
                causal_dag.add_edge(t, o)
                if getattr(causal_dag, "is_dag", None) and not causal_dag.is_dag():
                    causal_dag.remove_edge(t, o)
                    blocked.append((t, o))
                else:
                    causal_dag.add_edge(t, o, weight=_clamp(min_weight + max_step, min_weight, 1.0))
                    added.append((t, o))

    return {
        "added": added,
        "removed": removed,
        "reweighted": reweighted,
        "blocked": blocked,
        "evidence": {
            f"{t}->{o}": {"positive": p, "negative": n} for (t, o), (p, n) in evidence.items()
        },
    }


def update_cpd(
    cpd: dict[str, Any],
    *,
    interventions: list[dict[str, Any]],
    alpha: float = 0.1,
) -> dict[str, Any]:
    """用干预历史对 CPD 表做 EMA 平滑更新（CPD 资产 = obase.persistent_store.CPD 的 dict 形式）。

    table 键 = parents 组合（如 "a=1" / "a=1,b=0"），值 = P(node=1 | combo)。
    干预记录 target=parents 中的节点、outcome=本节点时，用观测频率平滑既有概率。

    Returns:
        更新后的 CPD dict（同构于 CPD.to_dict()）。
    """
    node = cpd["node"]
    table = {str(k): float(v) for k, v in cpd.get("table", {}).items()}
    parents = list(cpd.get("parents", []))

    counts: dict[str, list[int]] = {}
    for itv in interventions:
        if str(itv.get("outcome", "")) != node:
            continue
        combo = ",".join(f"{p}={1 if itv.get(p, 0) else 0}" for p in parents)
        entry = counts.setdefault(combo, [0, 0])
        if float(itv.get("delta", 0.0)) < 0 and bool(itv.get("success", True)):
            entry[0] += 1  # 观测到 node=1
        entry[1] += 1  # 总观测

    for combo, (ones, total) in counts.items():
        if total == 0:
            continue
        observed = ones / total
        prior = table.get(combo, 0.5)
        table[combo] = round((1 - alpha) * prior + alpha * observed, 4)

    return {
        "node": node,
        "parents": parents,
        "table": table,
        "meta": cpd.get("meta", {}),
    }
