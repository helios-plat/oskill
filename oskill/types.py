"""oskill.types — Shared dataclass types for oskill elements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawRegimeState:
    date: datetime
    state: str
    confidence: float


@dataclass
class SmoothingConfig:
    stress_states: list[str]
    stress_min_days: int
    normal_min_days: int


@dataclass
class SmoothingResult:
    smoothed_state: str
    state_changed: bool
    change_confirmed_at: datetime | None
    days_in_current_state: int
    transitional_state: str | None
    transitional_days: int


@dataclass
class DimContribution:
    dim_name: str
    raw_score: float
    base_weight: float
    multiplier: float
    weight_used: float
    contribution: float
    is_boosted: bool
    is_dampened: bool


@dataclass
class ScoreWeightedResult:
    total_score: float
    dim_contributions: list[DimContribution]
    weights_used: dict[str, float]
    regime: str
