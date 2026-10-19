"""oskill._meta_strategy — 跨任务元策略：故障签名 → 策略先验迁移.

当新故障（ThreatProfile.signature）与已知策略（StrategyState）的相似度足够高时，
把该策略的先验权重迁移到新故障，作为干预候选的起点（跨任务复用）。

相似度（加权融合，stateless 纯算法）:
- feature:   Jaccard(故障特征集合, 策略适用特征集合)
- depth:     因果图深度接近度 1 - min(1, |Δdepth|)
- dependency: 外部依赖服务集合 Jaccard

迁移判定: score >= transfer_threshold → transferable=True，best 策略先验可注入新 StrategyState。

例:
    >>> r = meta_strategy_transfer(["timeout", "cpu_spike"],
    ...     strategy_pool=[{"strategy_id": "s1", "applicable_features": ["timeout", "cpu_spike"],
    ...                     "dependencies": ["db"], "depth": 0.0, "priors": {"rollback": 0.7}}],
    ...     transfer_threshold=0.3)
    >>> r["transferable"]
    True
"""

from __future__ import annotations

from typing import Any

__all__ = ["meta_strategy_transfer", "jaccard"]


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard 集合相似度（空集安全）。"""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _depth_similarity(a: float, b: float) -> float:
    return max(0.0, 1.0 - min(1.0, abs(a - b)))


def skill_rules_to_strategy_pool(
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """把 aii.skill_rules 行(静态预处理规则)转成 strategy_pool 格式。

    规则 condition 的每个键值对被序列化为可匹配特征串, 供 meta_strategy_transfer
    的 threat_signature 命中(消费方把失败上下文转成同格式特征即可匹配)。

    入参规则行示例(aii.skill_rules 表行):
        {"rule_name": "scanned_zlib_pdf_prefilter",
         "condition": {"file_name_contains": "z-lib.sk", "ext": "pdf",
                       "text_layer_chars_lt": 1000, "size_mb_gt": 20},
         "action": {"route": "ocr_queue", "skip_llm": true}}
    返回 strategy_pool 项:
        {"strategy_id": "scanned_zlib_pdf_prefilter",
         "applicable_features": ["cond:file_name_contains=z-lib.sk", "cond:ext=pdf",
                                 "cond:text_layer_chars_lt=1000", "cond:size_mb_gt=20"],
         "dependencies": [], "depth": 0.0,
         "priors": {"route": "ocr_queue", "skip_llm": True}}
    """
    pool: list[dict[str, Any]] = []
    for rule in rules:
        cond = rule.get("condition") or {}
        if not isinstance(cond, dict):
            continue
        features = [f"cond:{k}={v}" for k, v in sorted(cond.items()) if v is not None]
        if not features:
            continue
        pool.append(
            {
                "strategy_id": rule.get("rule_name") or "rule_unknown",
                "applicable_features": features,
                "dependencies": [],
                "depth": 0.0,
                "priors": dict(rule.get("action") or {}),
            }
        )
    return pool


def meta_strategy_transfer(
    threat_signature: list[str],
    *,
    strategy_pool: list[dict[str, Any]],
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
    transfer_threshold: float = 0.5,
    top_k: int = 3,
    threat_depth: float = 0.0,
    threat_dependencies: list[str] | None = None,
) -> dict[str, Any]:
    """故障签名 → 策略先验迁移。

    Args:
        threat_signature: 故障特征集合（如 ["timeout", "cpu_spike"]）。
        strategy_pool: 策略候选列表，每项:
            {"strategy_id", "applicable_features": [...], "dependencies": [...],
             "depth": float, "priors": {...}}
        weights: (feature, depth, dependency) 三项权重（和为 1 推荐，不强制）。
        transfer_threshold: 迁移阈值（score >= 阈值 → transferable）。
        top_k: 返回的候选数量。
        threat_depth: 新故障在因果图中的深度。
        threat_dependencies: 新故障的外部依赖集合。

    Returns:
        {
            "candidates": [{"strategy_id", "score", "components": {...}}],
            "best": {...} | None,
            "transferable": bool,
            "threshold": float
        }
    """
    w_feat, w_depth, w_dep = weights
    threat_feats = {str(s) for s in threat_signature}
    threat_deps = {str(s) for s in (threat_dependencies or [])}

    scored: list[dict[str, Any]] = []
    for strat in strategy_pool:
        feat_sim = jaccard(threat_feats, {str(s) for s in strat.get("applicable_features", [])})
        depth_sim = _depth_similarity(threat_depth, float(strat.get("depth", 0.0)))
        dep_sim = jaccard(threat_deps, {str(s) for s in strat.get("dependencies", [])})
        score = w_feat * feat_sim + w_depth * depth_sim + w_dep * dep_sim
        scored.append(
            {
                "strategy_id": strat.get("strategy_id"),
                "name": strat.get("name", strat.get("strategy_id")),
                "priors": dict(strat.get("priors", {})),
                "score": round(score, 4),
                "components": {
                    "feature": round(feat_sim, 4),
                    "depth": round(depth_sim, 4),
                    "dependency": round(dep_sim, 4),
                },
            }
        )

    scored.sort(key=lambda s: s["score"], reverse=True)
    candidates = scored[: max(0, top_k)]
    best = candidates[0] if candidates and candidates[0]["score"] > 0 else None
    transferable = bool(best and best["score"] >= transfer_threshold)

    return {
        "candidates": candidates,
        "best": best,
        "transferable": transferable,
        "threshold": transfer_threshold,
    }
