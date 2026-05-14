"""oskill element manifest — machine-readable registry of all public elements."""

from __future__ import annotations

VERSION = "1.4.0"

ELEMENTS: list[str] = [
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
    # Group 6: Signal Detection
    "adx",
    "cusum_detector",
    "platt_calibration",
    # Group 7: Point Process
    "fit_hawkes",
    # Group 8: Causal
    "symbolic_transfer_entropy",
    # Group 9: HMM
    "gaussian_hmm",
    # Phase 1 additions (v1.4.0):
    "signal_ensemble",
    "weighted_signal_aggregation",
    "deterministic_llm_call",
    "prompt_fingerprint",
]

CATEGORIES: dict[str, list[str]] = {
    "performance": ["bootstrap_sharpe", "psr_dsr", "factor_attribution", "regime_aware_performance"],
    "validation": ["walk_forward_optimization", "cpcv_pipeline", "regime_aware_rolling"],
    "distribution": ["distribution_shift_test", "detect_outliers_robust", "bootstrap_distribution"],
    "similarity": [
        "historical_analogy_search",
        "regime_transition_analysis",
        "commodity_ratio_analytics",
        "geopolitical_risk_index",
    ],
    "prediction": ["calibration_analysis"],
    "signal_detection": ["adx", "cusum_detector", "platt_calibration"],
    "point_process": ["fit_hawkes"],
    "causal": ["symbolic_transfer_entropy"],
    "hmm": ["gaussian_hmm"],
    "signals": ["signal_ensemble", "weighted_signal_aggregation"],
    "llm": ["deterministic_llm_call", "prompt_fingerprint"],
}

STABILITY: dict[str, str] = {
    "bootstrap_sharpe": "stable",
    "psr_dsr": "stable",
    "factor_attribution": "stable",
    "regime_aware_performance": "stable",
    "walk_forward_optimization": "stable",
    "cpcv_pipeline": "stable",
    "regime_aware_rolling": "stable",
    "distribution_shift_test": "stable",
    "detect_outliers_robust": "stable",
    "bootstrap_distribution": "stable",
    "historical_analogy_search": "stable",
    "regime_transition_analysis": "stable",
    "commodity_ratio_analytics": "stable",
    "geopolitical_risk_index": "stable",
    "calibration_analysis": "stable",
    "adx": "stable",
    "cusum_detector": "stable",
    "platt_calibration": "stable",
    "fit_hawkes": "stable",
    "symbolic_transfer_entropy": "stable",
    "gaussian_hmm": "stable",
    # Phase 1 additions:
    "signal_ensemble": "stable",
    "weighted_signal_aggregation": "stable",
    "deterministic_llm_call": "experimental",
    "prompt_fingerprint": "stable",
}
