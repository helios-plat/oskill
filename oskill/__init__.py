"""oskill — Composite financial analysis workflows built on oprim atomic operations."""

from oskill._version import __version__
from oskill.performance import (
    bootstrap_sharpe,
    factor_attribution,
    psr_dsr,
    regime_aware_performance,
)
from oskill.validation import (
    cpcv_pipeline,
    regime_aware_rolling,
    walk_forward_optimization,
)

__all__ = [
    "__version__",
    # Group 1: Performance
    "bootstrap_sharpe",
    "psr_dsr",
    "factor_attribution",
    "regime_aware_performance",
    # Group 2: Validation
    "walk_forward_optimization",
    "cpcv_pipeline",
    "regime_aware_rolling",
]
