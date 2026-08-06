"""oskill._online_cpd_update — 在线因果参数更新(CPD, 无状态)。

给定旧 CPD 参数 + 新观测(父状态配置 + 子节点结果), 返回更新后的参数。
干预执行后, 用真实观测到的成功/失败更新 CPD —— 让因果模型本身随时间变准。

两种模式:
  - Dirichlet 伪计数更新: counts[config][state] += strength。
    贝叶斯意义: 以 Dirichlet 为先验的共轭更新, 收敛到真实频率, strength 控制伪计数强度。
  - EMA 快速适应: probs ← (1−α)·probs + α·onehot, 再按 total_mass 换算回计数表示。
    对概念漂移(环境变了)响应快; α 越大越跟手、越抖。

CPD 数据模型 (JSON 可持久化):
    {
      "child_states": ["success", "fault"],          # 子节点状态序(索引即位置)
      "parents": ["mode"],                            # 父变量名(元数据)
      "counts": {                                     # 父状态配置 -> 每子状态的伪计数
        "degraded": [3.0, 7.0],
        "healthy":  [9.0, 1.0]
      }
    }
父状态配置用 "|" 拼接多父值(config_key), 空配置 = 无父节点。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def config_key(*parent_values: Any) -> str:
    """父状态配置 → 字典键。多父值用 '|' 拼接, 单父值原样返回。"""
    if len(parent_values) == 1:
        return str(parent_values[0])
    return "|".join(str(v) for v in parent_values)


def split_config(key: str) -> List[str]:
    return key.split("|")


@dataclass
class CategoricalCPD:
    """条件概率分布: 每个父配置一行 Dirichlet 伪计数。

    version: 结构/参数版本号 —— 每次更新自增, 供审计记录 "当时用的是哪版 CPD"。
    """

    child_states: List[str]
    counts: Dict[str, List[float]] = field(default_factory=dict)
    parents: List[str] = field(default_factory=list)
    version: int = 1

    # ── 构造 ────────────────────────────────────────────────────────
    @classmethod
    def uniform(cls, child_states: List[str], parents: List[str] | None = None,
                prior_mass: float = 1.0) -> "CategoricalCPD":
        """空 CPD: 没有任何配置行, 首次观测时按均匀先验初始化。"""
        return cls(child_states=list(child_states), counts={},
                   parents=list(parents or []))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategoricalCPD":
        if not data:
            raise ValueError("CPD 数据为空")
        return cls(child_states=list(data["child_states"]),
                   counts={str(k): [float(v) for v in vals]
                           for k, vals in (data.get("counts") or {}).items()},
                   parents=list(data.get("parents", [])),
                   version=int(data.get("version", 1)))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # ── 查询 ────────────────────────────────────────────────────────
    def _row(self, parent_config: str, *, create: bool = False) -> List[float]:
        row = self.counts.get(parent_config)
        if row is not None:
            return row
        if create:
            prior = [1.0] * len(self.child_states)   # 均匀伪计数先验
            self.counts[parent_config] = prior
            return prior
        raise KeyError(f"父配置 {parent_config!r} 无观测, 无法预测")

    def probs(self, parent_config: str) -> Dict[str, float]:
        """P(child_state | parent_config)。"""
        row = self._row(parent_config)
        total = sum(row)
        if total <= 0:
            raise ValueError("伪计数总和为 0")
        return {s: row[i] / total for i, s in enumerate(self.child_states)}

    def p_fault(self, parent_config: str, fault_state: Optional[str] = None) -> float:
        """P(fault | parent_config)。fault_state 缺省取最后一个子状态(约定)。"""
        fault = fault_state or self.child_states[-1]
        return self.probs(parent_config)[fault]

    def state_index(self, child_state: str) -> int:
        try:
            return self.child_states.index(child_state)
        except ValueError as exc:
            raise ValueError(f"子状态 {child_state!r} 不在 {self.child_states} 中") from exc


# ---------------------------------------------------------------------------
# 无状态更新: 旧 CPD + 观测 → 新 CPD (不修改入参)
# ---------------------------------------------------------------------------

def _clone(cpd: CategoricalCPD) -> CategoricalCPD:
    return CategoricalCPD(child_states=list(cpd.child_states),
                          counts={k: list(v) for k, v in cpd.counts.items()},
                          parents=list(cpd.parents),
                          version=cpd.version)


def dirichlet_update(cpd: CategoricalCPD,
                     parent_config: str,
                     child_state: str,
                     strength: float = 1.0) -> CategoricalCPD:
    """Dirichlet 伪计数更新: counts[config][state] += strength。"""
    if strength <= 0:
        raise ValueError(f"strength 必须 > 0, 收到 {strength}")
    out = _clone(cpd)
    row = out._row(parent_config, create=True)
    row[out.state_index(child_state)] += strength
    out.version = cpd.version + 1
    return out


def ema_update(cpd: CategoricalCPD,
               parent_config: str,
               child_state: str,
               alpha: float = 0.1,
               total_mass: float = 100.0) -> CategoricalCPD:
    """EMA 更新: probs ← (1−α)·probs + α·onehot, 换算回计数表示。

    首次观测该配置时从均匀分布起步。total_mass 决定计数表示的"惯性"。
    """
    if not (0 < alpha <= 1):
        raise ValueError(f"alpha 必须 ∈ (0,1], 收到 {alpha}")
    out = _clone(cpd)
    try:
        row = out._row(parent_config)
    except KeyError:
        row = [1.0] * len(out.child_states)
        out.counts[parent_config] = row
    idx = out.state_index(child_state)
    total = sum(row)
    probs = [v / total for v in row]
    new_probs = [(1 - alpha) * p + (alpha if i == idx else 0.0)
                 for i, p in enumerate(probs)]
    out.counts[parent_config] = [p * total_mass for p in new_probs]
    out.version = cpd.version + 1
    return out


def update_cpd(cpd: CategoricalCPD,
               parent_config: str,
               child_state: str,
               mode: str = "dirichlet",
               **kwargs: Any) -> CategoricalCPD:
    """统一入口: mode ∈ dirichlet | ema。"""
    if mode == "dirichlet":
        return dirichlet_update(cpd, parent_config, child_state,
                                strength=float(kwargs.get("strength", 1.0)))
    if mode == "ema":
        return ema_update(cpd, parent_config, child_state,
                          alpha=float(kwargs.get("alpha", 0.1)),
                          total_mass=float(kwargs.get("total_mass", 100.0)))
    raise ValueError(f"未知更新模式 {mode!r}, 只支持 dirichlet|ema")


__all__ = ["CategoricalCPD", "config_key", "dirichlet_update", "ema_update",
           "split_config", "update_cpd"]
