"""oskill.productization_gate — 产品化四问 (FDE 书第7章 3O 内化)。

把现场解法提炼为产品前的决策门 (Palantir "强烈的观点, 松散地持有"):
  * 问1 个性 vs 共性 — 同类问题在 >= 3 个客户独立出现 = 产品信号;
  * 问2 泛化代价 vs 收益 — 现场代码"快而糙", 泛化成本高于写第一版时
    留在组件层, 不强行平台化 (平台每个能力 = 终身维护承诺);
  * 问3 非代码人可用 — 现场工具使用者是工程师, 平台能力使用者是所有人;
  * 问4 现场空间 — 平台收编过多则现场退化 (激进授权: 高层定目标, 打法归现场)。

综合判定: productize (收编平台) / components (留组件层) / keep_field (留在现场)。
零 veya 反向依赖: 纯决策表。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DECISION_PRODUCTIZE = "productize"
DECISION_COMPONENTS = "components"
DECISION_KEEP_FIELD = "keep_field"

# 产品化共性信号阈值 (3 个客户独立出现)
COMMONALITY_THRESHOLD = 3


@dataclass
class ProductizationVerdict:
    """产品化四问决策结果。

    Attributes:
        decision: productize / components / keep_field。
        answers: 四问答案。
        reasons: 决策理由。
    """

    decision: str
    answers: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"decision": self.decision, "answers": self.answers, "reasons": self.reasons}


def evaluate_productization(
    *,
    independent_customers: int,
    generalization_cost: float,
    expected_customers: int,
    per_customer_savings: float,
    usable_by_non_coders: bool,
    field_room: bool,
    commonality_threshold: int = COMMONALITY_THRESHOLD,
) -> ProductizationVerdict:
    """产品化四问决策。

    Args:
        independent_customers: 独立出现过同问题的客户数 (>= 阈值 = 共性)。
        generalization_cost: 泛化投入 (相对写第一版成本, 如 3.0 = 3 倍)。
        expected_customers: 预期未来客户数。
        per_customer_savings: 每个客户省下的定制成本。
        usable_by_non_coders: 是否可被不会写代码的人使用。
        field_room: 收编后现场是否还有空间 (创造力不被压死)。
        commonality_threshold: 共性信号阈值 (默认 3, Palantir 经验法则)。

    Returns:
        ProductizationVerdict。

    Example:
        >>> v = evaluate_productization(independent_customers=5,
        ...                             generalization_cost=2.0,
        ...                             expected_customers=10,
        ...                             per_customer_savings=4.0,
        ...                             usable_by_non_coders=True,
        ...                             field_room=True)
        >>> v.decision
        'productize'
    """
    answers: dict[str, Any] = {}
    reasons: list[str] = []

    # 问1: 个性 vs 共性
    common = independent_customers >= commonality_threshold
    answers["q1_commonality"] = {
        "ok": common,
        "customers": independent_customers,
        "threshold": commonality_threshold,
        "note": "3 客户相同痛点是产品信号, 1 客户可能只是怪癖",
    }
    if not common:
        reasons.append(f"共性不足: {independent_customers} 客户 < {commonality_threshold} (个性)")

    # 问2: 泛化代价 vs 收益
    benefit = expected_customers * per_customer_savings
    worth_it = benefit > generalization_cost
    answers["q2_generalization"] = {
        "ok": worth_it,
        "generalization_cost": generalization_cost,
        "benefit": benefit,
        "note": "泛化成本高于写第一版时留在组件层, 不强行平台化",
    }
    if not worth_it:
        reasons.append(f"泛化不值: 成本 {generalization_cost} > 收益 {benefit}")

    # 问3: 非代码人可用
    answers["q3_usable"] = {
        "ok": bool(usable_by_non_coders),
        "note": "现场工具使用者是工程师, 平台能力使用者是所有人",
    }
    if not usable_by_non_coders:
        reasons.append("不能非代码人使用 (交互抽象不足)")

    # 问4: 现场空间
    answers["q4_field_room"] = {
        "ok": bool(field_room),
        "note": "收编过多现场退化为配置员 (激进授权: 高层定目标, 打法归现场)",
    }
    if not field_room:
        reasons.append("收编后现场无空间 (创造力被压死)")

    # 综合判定
    if common and worth_it and usable_by_non_coders and field_room:
        return ProductizationVerdict(DECISION_PRODUCTIZE, answers, reasons or ["四问全过"])
    if common and worth_it:
        reasons.append("共性强 + 泛化值, 但交互/现场未满足 → 留组件层")
        return ProductizationVerdict(DECISION_COMPONENTS, answers, reasons)
    return ProductizationVerdict(DECISION_KEEP_FIELD, answers, reasons or ["留在现场"])


__all__ = [
    "COMMONALITY_THRESHOLD",
    "DECISION_COMPONENTS",
    "DECISION_KEEP_FIELD",
    "DECISION_PRODUCTIZE",
    "ProductizationVerdict",
    "evaluate_productization",
]
