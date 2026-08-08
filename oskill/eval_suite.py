"""oskill.eval_suite — 评估套件 + 统计显著性 (ai-agent-book 第6章 3O 内化)。

机制: 声明式评测集 (EvalCase) + 注入式评分器 → 跑分 (EvalRun) → 双跑对比
(baseline vs candidate) + 统计显著性 (配对 t 检验 / Wilcoxon 符号秩 /
Cohen's d 效应量)。全部确定性可计算, 评分由调用方注入 (LLM/规则/测试)。

零 veya 反向依赖: 纯统计 + 数据结构, scipy 可选 (缺失回落纯 Python 实现)。
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ── 数据结构 ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EvalCase:
    """一个评测用例。

    Attributes:
        id: 用例 id。
        input: 输入 (任意可序列化)。
        expected: 期望输出 (评分器使用)。
        meta: 附加元数据 (标签/难度/领域)。
    """

    id: str
    input: Any
    expected: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalRun:
    """一次跑分结果。"""

    suite_name: str
    scores: dict[str, float] = field(default_factory=dict)  # case_id → score
    details: dict[str, Any] = field(default_factory=dict)  # case_id → 附加信息

    def summary(self) -> dict[str, float]:
        """均值/中位数/标准差/最小/最大。"""
        values = list(self.scores.values())
        if not values:
            return {}
        return {
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "n": len(values),
        }


Scorer = Callable[[EvalCase], float]
"""评分器: 输入用例 → 分数 [0, 1]。"""


# ── 跑分 ──────────────────────────────────────────────────────────────


def run_suite(cases: list[EvalCase], scorer: Scorer, *, suite_name: str = "suite") -> EvalRun:
    """对一组用例跑一个评分器。

    Args:
        cases: 评测用例。
        scorer: 评分器 (LLM 评分/规则/测试结果 → 分数)。
        suite_name: 套件名。

    Returns:
        EvalRun (scores + summary)。

    Example:
        >>> r = run_suite([EvalCase("1", "x")], lambda c: 0.8)
        >>> r.summary()["mean"]
        0.8
    """
    run = EvalRun(suite_name=suite_name)
    for case in cases:
        try:
            run.scores[case.id] = float(scorer(case))
        except Exception as exc:
            run.scores[case.id] = 0.0
            run.details[case.id] = {"error": f"{exc.__class__.__name__}: {exc}"}
    return run


# ── 统计显著性 ────────────────────────────────────────────────────────


def paired_t_test(a: list[float], b: list[float]) -> dict[str, float]:
    """配对 t 检验: b - a 的差异是否显著 (双侧)。

    Args:
        a: baseline 分数序列。
        b: candidate 分数序列 (与 a 等长配对)。

    Returns:
        {t_statistic, p_value, df, mean_diff, significant_05}
        样本量 < 2 或方差为 0 时 p_value = 1.0。

    Example:
        >>> r = paired_t_test([0.5, 0.6, 0.5], [0.7, 0.8, 0.7])
        >>> r["mean_diff"] > 0
        True
    """
    n = len(a)
    if n < 2 or len(b) != n:
        return {
            "t_statistic": 0.0,
            "p_value": 1.0,
            "df": max(n - 1, 0),
            "mean_diff": 0.0,
            "significant_05": False,
        }
    diffs = [bi - ai for ai, bi in zip(a, b)]
    mean_diff = statistics.fmean(diffs)
    if n == 1:
        return {
            "t_statistic": 0.0,
            "p_value": 1.0,
            "df": 0,
            "mean_diff": mean_diff,
            "significant_05": False,
        }
    stdev = statistics.stdev(diffs)
    if stdev == 0:
        # 差异完全一致: 非零 → 完美显著; 零 → 无差异
        significant = mean_diff != 0
        return {
            "t_statistic": 0.0,
            "p_value": 0.0 if significant else 1.0,
            "df": n - 1,
            "mean_diff": mean_diff,
            "significant_05": significant,
        }
    t = mean_diff / (stdev / math.sqrt(n))
    df = n - 1
    p = _t_cdf_two_tail(abs(t), df)
    return {
        "t_statistic": t,
        "p_value": p,
        "df": df,
        "mean_diff": mean_diff,
        "significant_05": p < 0.05,
    }


def wilcoxon_signed_rank(a: list[float], b: list[float]) -> dict[str, float]:
    """Wilcoxon 符号秩检验 (非参数配对, 不假设正态)。

    Returns:
        {w_statistic, p_value, n, significant_05}。
    """
    diffs = [bi - ai for ai, bi in zip(a, b) if ai != bi]
    if len(diffs) < 2:
        return {"w_statistic": 0.0, "p_value": 1.0, "n": len(diffs), "significant_05": False}
    # 秩 (平均秩处理并列)
    sorted_abs = sorted(abs(d) for d in diffs)
    ranks = {value: i + 1 for i, value in enumerate(sorted_abs)}
    w_plus = sum(ranks[abs(d)] for d in diffs if d > 0)
    w_minus = sum(ranks[abs(d)] for d in diffs if d < 0)
    w = min(w_plus, w_minus)
    n = len(diffs)
    # 正态近似 (z = (W - n(n+1)/4) / sqrt(n(n+1)(2n+1)/24))
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w - mu) / sigma if sigma > 0 else 0.0
    p = _normal_two_tail(abs(z))
    return {"w_statistic": w, "p_value": p, "n": n, "significant_05": p < 0.05}


def cohens_d(a: list[float], b: list[float]) -> float:
    """Cohen's d 效应量 (配对): |mean_diff| / pooled_stdev。

    差异完全一致 (stdev=0) 且非零时返回饱和值 3.0 (完美一致效应)。
    """
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    diffs = [bi - ai for ai, bi in zip(a, b)]
    mean_diff = statistics.fmean(diffs)
    stdev = statistics.stdev(diffs)
    if stdev == 0:
        return 3.0 if mean_diff != 0 else 0.0
    return abs(mean_diff) / stdev


@dataclass
class ComparisonReport:
    """双跑对比报告。"""

    baseline: EvalRun
    candidate: EvalRun
    t_test: dict[str, float] = field(default_factory=dict)
    wilcoxon: dict[str, float] = field(default_factory=dict)
    effect_size: float = 0.0

    @property
    def candidate_wins(self) -> bool:
        """candidate 显著优于 baseline (t 检验 p<0.05 且均值更高)。"""
        return self.t_test.get("significant_05", False) and self.t_test.get("mean_diff", 0.0) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.summary(),
            "candidate": self.candidate.summary(),
            "t_test": self.t_test,
            "wilcoxon": self.wilcoxon,
            "effect_size": self.effect_size,
            "candidate_wins": self.candidate_wins,
        }


def compare_runs(baseline: EvalRun, candidate: EvalRun) -> ComparisonReport:
    """对比两次跑分: 配对显著性 + 效应量。

    Args:
        baseline: 基线跑分。
        candidate: 候选跑分 (相同用例集)。

    Returns:
        ComparisonReport。

    Example:
        >>> b = run_suite([EvalCase("1", "x")], lambda c: 0.5)
        >>> c = run_suite([EvalCase("1", "x")], lambda c: 0.9)
        >>> compare_runs(b, c).candidate_wins
        True
    """
    common = [cid for cid in baseline.scores if cid in candidate.scores]
    a = [baseline.scores[cid] for cid in common]
    b = [candidate.scores[cid] for cid in common]
    return ComparisonReport(
        baseline=baseline,
        candidate=candidate,
        t_test=paired_t_test(a, b),
        wilcoxon=wilcoxon_signed_rank(a, b),
        effect_size=cohens_d(a, b),
    )


# ── 数值近似 (无 scipy 依赖) ─────────────────────────────────────────


def _lbeta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betai(a: float, b: float, x: float) -> float:
    """正则化不完全 beta I_x(a, b) (Numerical Recipes betai)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_cdf_two_tail(t: float, df: int) -> float:
    """Student-t 双侧 p 值: p = 2 * (1 - I_{df/(df+t^2)}(df/2, 1/2))。"""
    if df <= 0:
        return 1.0
    x = df / (df + t * t)
    # P(T < t) = 1 - 0.5*I_x(df/2, 1/2), 双侧 p = I_x(df/2, 1/2)
    p = _betai(df / 2.0, 0.5, x)
    return max(0.0, min(1.0, p))


def _lbeta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betai(a: float, b: float, x: float) -> float:
    """正则化不完全 beta I_x(a, b) (Numerical Recipes betai)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_cdf_two_tail(t: float, df: int) -> float:
    """Student-t 双侧 p 值: p = 2 * (1 - I_{df/(df+t^2)}(df/2, 1/2))。"""
    if df <= 0:
        return 1.0
    x = df / (df + t * t)
    # P(T < t) = 1 - 0.5*I_x(df/2, 1/2), 双侧 p = I_x(df/2, 1/2)
    p = _betai(df / 2.0, 0.5, x)
    return max(0.0, min(1.0, p))


def _betacf(a: float, b: float, x: float, max_iter: int = 100) -> float:
    """连分式求正则化不完全 beta。"""
    eps = 3e-9
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < eps:
        d = eps
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < eps:
            d = eps
        c = 1.0 + aa / c
        if abs(c) < eps:
            c = eps
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < eps:
            d = eps
        c = 1.0 + aa / c
        if abs(c) < eps:
            c = eps
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _normal_two_tail(z: float) -> float:
    """标准正态双侧 CDF 近似 (Abramowitz-Stegun)。"""
    if z == 0:
        return 1.0
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = (
        (((1.330274429 * t - 1.821255978) * t + 1.781477937) * t - 0.356563782) * t + 0.319381530
    ) * t
    tail = 0.3989422804 * math.exp(-z * z / 2) * poly
    return 2 * tail
