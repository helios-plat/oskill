"""oskill element manifest — machine-readable registry of all public elements."""  # pragma: no cover

from __future__ import annotations

VERSION = "1.9.0"

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
    # Phase 2 additions (v1.5.0):
    "ledoit_wolf_shrinkage",
    "denoised_covariance",
    "probability_of_backtest_overfitting",
    "deflated_sharpe_ratio",
    "factor_quantile_returns",
    # Phase 3 additions (v1.6.0):
    "tool_call_validator",
    "chain_of_thought_extractor",
    "llm_response_consistency",
    "multi_model_ensemble",
    "faithfulness_score",
    "chunking_strategy_apply",
    "reranker_score",
    # Phase 4 prerequisites (v1.7.0):
    "triple_barrier_label",
    "factor_ic",
    "bocpd_bayesian",
    "pelt_change_point",
    # Phase 5B: ml_finance (v1.8.0):
    "meta_labeling",
    "sample_uniqueness_weights",
    "return_attribution_weights",
    "fractional_differentiation",
    "cusum_filter",
    "bet_sizing",
    # Phase 5C: factor models (v1.8.0):
    "fama_french_5_factor_model",
    "carhart_4_factor_model",
    "barra_style_decomposition",
    "factor_neutralization",
    # Phase 6B: Bayesian (5)
    "bayesian_linear_regression",
    "bayesian_var",
    "gaussian_process_regression",
    "hierarchical_bayes_normal",
    "posterior_diagnostics",
    # Phase 6C: Advanced validation (4)
    "combinatorially_symmetric_cv",
    "haircut_sharpe",
    "full_combinatorial_purged_cv",
    "bonferroni_holm_correction",
    # Phase 6D: Advanced backtest (3)
    "embargo_purged_cv",
    "random_subsampling_validation",
    "walk_forward_optimization_pipeline",
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
    "llm": [
        "deterministic_llm_call",
        "prompt_fingerprint",
        "tool_call_validator",
        "chain_of_thought_extractor",
        "llm_response_consistency",
        "multi_model_ensemble",
        "faithfulness_score",
    ],
    "rag": ["chunking_strategy_apply", "reranker_score"],
    "covariance": ["ledoit_wolf_shrinkage", "denoised_covariance"],
    "validation_phase2": [
        "probability_of_backtest_overfitting", "deflated_sharpe_ratio",
        "combinatorially_symmetric_cv", "haircut_sharpe",
        "full_combinatorial_purged_cv", "bonferroni_holm_correction",
    ],
    "ml_labeling": ["triple_barrier_label"],
    "ml_finance": [
        "meta_labeling", "sample_uniqueness_weights", "return_attribution_weights",
        "fractional_differentiation", "cusum_filter", "bet_sizing",
    ],
    "change_point": ["bocpd_bayesian", "pelt_change_point"],
    "factor": [
        "factor_ic", "factor_quantile_returns",
        "fama_french_5_factor_model", "carhart_4_factor_model",
        "barra_style_decomposition", "factor_neutralization",
    ],
    # Phase 6 categories
    "bayesian": [
        "bayesian_linear_regression", "bayesian_var",
        "gaussian_process_regression", "hierarchical_bayes_normal",
        "posterior_diagnostics",
    ],
    "backtest": [
        "embargo_purged_cv", "random_subsampling_validation",
        "walk_forward_optimization_pipeline",
    ],
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
    # Phase 2 additions:
    "ledoit_wolf_shrinkage": "stable",
    "denoised_covariance": "stable",
    "probability_of_backtest_overfitting": "stable",
    "deflated_sharpe_ratio": "stable",
    "factor_quantile_returns": "stable",
    # Phase 3 additions:
    "tool_call_validator": "experimental",
    "chain_of_thought_extractor": "experimental",
    "llm_response_consistency": "experimental",
    "multi_model_ensemble": "experimental",
    "faithfulness_score": "experimental",
    "chunking_strategy_apply": "experimental",
    "reranker_score": "experimental",
    # Phase 4 + 5 additions:
    "triple_barrier_label": "stable",
    "factor_ic": "stable",
    "bocpd_bayesian": "stable",
    "pelt_change_point": "stable",
    "meta_labeling": "stable",
    "sample_uniqueness_weights": "stable",
    "return_attribution_weights": "stable",
    "fractional_differentiation": "stable",
    "cusum_filter": "stable",
    "bet_sizing": "stable",
    "fama_french_5_factor_model": "stable",
    "carhart_4_factor_model": "stable",
    "barra_style_decomposition": "stable",
    "factor_neutralization": "stable",
    # Phase 6 stability
    "bayesian_linear_regression": "stable",
    "bayesian_var": "stable",
    "gaussian_process_regression": "stable",
    "hierarchical_bayes_normal": "stable",
    "posterior_diagnostics": "stable",
    "combinatorially_symmetric_cv": "stable",
    "haircut_sharpe": "stable",
    "full_combinatorial_purged_cv": "stable",
    "bonferroni_holm_correction": "stable",
    "embargo_purged_cv": "stable",
    "random_subsampling_validation": "stable",
    "walk_forward_optimization_pipeline": "stable",
}
