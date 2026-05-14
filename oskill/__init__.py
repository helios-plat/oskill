"""oskill — Composite financial analysis workflows built on oprim atomic operations."""

from oskill._version import __version__
from oskill.llm.deterministic_call import deterministic_llm_call
from oskill.llm.prompt_fingerprint import prompt_fingerprint
from oskill.signals.aggregation import weighted_signal_aggregation
from oskill.signals.ensemble import signal_ensemble
from oskill.causal import symbolic_transfer_entropy
from oskill.distribution import (
    bootstrap_distribution,
    detect_outliers_robust,
    distribution_shift_test,
)
from oskill.hmm import gaussian_hmm
from oskill.performance import (
    bootstrap_sharpe,
    factor_attribution,
    psr_dsr,
    regime_aware_performance,
)
from oskill.point_process import fit_hawkes
from oskill.prediction import calibration_analysis
from oskill.signal_detection import adx, cusum_detector, platt_calibration
from oskill.similarity import (
    commodity_ratio_analytics,
    geopolitical_risk_index,
    historical_analogy_search,
    regime_transition_analysis,
)
from oskill.validation import (
    cpcv_pipeline,
    regime_aware_rolling,
    walk_forward_optimization,
)
# Phase 2: Covariance
from oskill.covariance.shrinkage import ledoit_wolf_shrinkage
from oskill.covariance.denoising import denoised_covariance
# Phase 2: Validation
from oskill.validation.pbo import probability_of_backtest_overfitting
from oskill.validation.deflated_sharpe import deflated_sharpe_ratio
# Phase 2: Factor
from oskill.factor.quantile_returns import factor_quantile_returns

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
    # Group 3: Distribution
    "distribution_shift_test",
    "detect_outliers_robust",
    "bootstrap_distribution",
    # Group 4: Similarity
    "historical_analogy_search",
    "regime_transition_analysis",
    "commodity_ratio_analytics",
    "geopolitical_risk_index",
    # Group 5: Prediction
    "calibration_analysis",
    # Group 6: Signal Detection (NEW from Selene)
    "adx",
    "cusum_detector",
    "platt_calibration",
    # Group 7: Point Process (NEW from Selene)
    "fit_hawkes",
    # Group 8: Causal (NEW from Selene)
    "symbolic_transfer_entropy",
    # Group 9: HMM (NEW from Selene)
    "gaussian_hmm",
    # Group 10: Signals (Phase 1)
    "signal_ensemble",
    "weighted_signal_aggregation",
    # Group 11: LLM (Phase 1)
    "deterministic_llm_call",
    "prompt_fingerprint",
    # Group 12: Covariance (Phase 2)
    "ledoit_wolf_shrinkage",
    "denoised_covariance",
    # Group 13: Validation (Phase 2)
    "probability_of_backtest_overfitting",
    "deflated_sharpe_ratio",
    # Group 14: Factor (Phase 2)
    "factor_quantile_returns",
]
