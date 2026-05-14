"""Validation submodule.

Phase 1 functions (re-exported from legacy module):
    cpcv_pipeline, walk_forward_optimization, regime_aware_rolling

Phase 2 additions:
    probability_of_backtest_overfitting, deflated_sharpe_ratio
"""
# Re-export oprim at package level for backward compatibility with mock patches
# (tests mock oskill.validation.oprim.*)
import oprim  # noqa: F401

# Phase 1 legacy imports (preserve backward compatibility)
from oskill.validation._legacy import (
    cpcv_pipeline,
    regime_aware_rolling,
    walk_forward_optimization,
)

# Phase 2 additions
from oskill.validation.pbo import probability_of_backtest_overfitting
from oskill.validation.deflated_sharpe import deflated_sharpe_ratio

__all__ = [
    # Phase 1
    "walk_forward_optimization",
    "cpcv_pipeline",
    "regime_aware_rolling",
    # Phase 2
    "probability_of_backtest_overfitting",
    "deflated_sharpe_ratio",
]
