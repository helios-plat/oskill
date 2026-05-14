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
# Phase 3: LLM
from oskill.llm.tool_validation import tool_call_validator
from oskill.llm.cot import chain_of_thought_extractor
from oskill.llm.consistency import llm_response_consistency
from oskill.llm.multi_model import multi_model_ensemble
from oskill.llm.faithfulness import faithfulness_score
# Phase 3: RAG
from oskill.rag.chunking import chunking_strategy_apply
from oskill.rag.reranking import reranker_score
# Phase 4 prerequisites + Phase 5B: ml_finance
from oskill.ml_finance.triple_barrier import triple_barrier_label
from oskill.ml_finance.meta_labeling import meta_labeling
from oskill.ml_finance.sample_weights import sample_uniqueness_weights, return_attribution_weights
from oskill.ml_finance.fractional_diff import fractional_differentiation
from oskill.ml_finance.cusum_filter import cusum_filter
from oskill.ml_finance.bet_sizing import bet_sizing
# Phase 4 prerequisites: change_point
from oskill.change_point.bayesian_online import bocpd_bayesian
from oskill.change_point.pelt import pelt_change_point
# Phase 4 prerequisites + Phase 5C: factor
from oskill.factor.ic import factor_ic
from oskill.factor.fama_french import fama_french_5_factor_model
from oskill.factor.carhart import carhart_4_factor_model
from oskill.factor.barra import barra_style_decomposition
from oskill.factor.neutralization import factor_neutralization
# Phase 6B: Bayesian
from oskill.bayesian.linear_regression import bayesian_linear_regression
from oskill.bayesian.var import bayesian_var
from oskill.bayesian.gp_regression import gaussian_process_regression
from oskill.bayesian.hierarchical import hierarchical_bayes_normal
from oskill.bayesian.posterior_diagnostics import posterior_diagnostics
# Phase 6C: Advanced validation
from oskill.validation.csv import combinatorially_symmetric_cv
from oskill.validation.haircut import haircut_sharpe
from oskill.validation.full_cpcv import full_combinatorial_purged_cv
from oskill.validation.trial_correction import bonferroni_holm_correction
# Phase 6D: Advanced backtest
from oskill.backtest.embargo_cv import embargo_purged_cv
from oskill.backtest.random_subsampling import random_subsampling_validation
from oskill.backtest.walk_forward_optimization import walk_forward_optimization_pipeline

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
    # Group 15: LLM (Phase 3)
    "tool_call_validator",
    "chain_of_thought_extractor",
    "llm_response_consistency",
    "multi_model_ensemble",
    "faithfulness_score",
    # Group 16: RAG (Phase 3)
    "chunking_strategy_apply",
    "reranker_score",
    # Group 17: ML Finance (Phase 4+5B)
    "triple_barrier_label",
    "meta_labeling",
    "sample_uniqueness_weights",
    "return_attribution_weights",
    "fractional_differentiation",
    "cusum_filter",
    "bet_sizing",
    # Group 18: Change Point (Phase 4)
    "bocpd_bayesian",
    "pelt_change_point",
    # Group 19: Factor (Phase 4+5C)
    "factor_ic",
    "fama_french_5_factor_model",
    "carhart_4_factor_model",
    "barra_style_decomposition",
    "factor_neutralization",
    # Group 20: Bayesian (Phase 6B)
    "bayesian_linear_regression",
    "bayesian_var",
    "gaussian_process_regression",
    "hierarchical_bayes_normal",
    "posterior_diagnostics",
    # Group 21: Advanced Validation (Phase 6C)
    "combinatorially_symmetric_cv",
    "haircut_sharpe",
    "full_combinatorial_purged_cv",
    "bonferroni_holm_correction",
    # Group 22: Advanced Backtest (Phase 6D)
    "embargo_purged_cv",
    "random_subsampling_validation",
    "walk_forward_optimization_pipeline",
]
