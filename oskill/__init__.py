"""oskill — Composite financial analysis workflows built on oprim atomic operations."""

from oskill._version import __version__

# Phase 6D: Advanced backtest
from oskill.backtest.embargo_cv import embargo_purged_cv
from oskill.backtest.random_subsampling import random_subsampling_validation
from oskill.backtest.walk_forward_optimization import walk_forward_optimization_pipeline
from oskill.bayesian.gp_regression import gaussian_process_regression
from oskill.bayesian.hierarchical import hierarchical_bayes_normal

# Phase 6B: Bayesian
from oskill.bayesian.linear_regression import bayesian_linear_regression
from oskill.bayesian.posterior_diagnostics import posterior_diagnostics
from oskill.bayesian.var import bayesian_var
from oskill.causal import symbolic_transfer_entropy

# Phase 7D: Causal Discovery
from oskill.causal_discovery import pcmci_causal_discovery

# Phase 4 prerequisites: change_point
from oskill.change_point.bayesian_online import bocpd_bayesian
from oskill.change_point.pelt import pelt_change_point
from oskill.conformal.adaptive_cp import adaptive_conformal_inference
from oskill.conformal.change_point_cp import conformal_with_change_points

# Phase 7B: Conformal Prediction
from oskill.conformal.split_cp import conformal_prediction_interval
from oskill.covariance.denoising import denoised_covariance

# Phase 2: Covariance
from oskill.covariance.shrinkage import ledoit_wolf_shrinkage
from oskill.distribution import (
    bootstrap_distribution,
    detect_outliers_robust,
    distribution_shift_test,
)
from oskill.distributional_rl.iqn import implicit_quantile_loss

# Phase 7C: Distributional RL
from oskill.distributional_rl.quantile_regression import quantile_regression_loss
from oskill.factor.barra import barra_style_decomposition
from oskill.factor.carhart import carhart_4_factor_model
from oskill.factor.fama_french import fama_french_5_factor_model

# Phase 4 prerequisites + Phase 5C: factor
from oskill.factor.ic import factor_ic
from oskill.factor.neutralization import factor_neutralization

# Phase 2: Factor
from oskill.factor.quantile_returns import factor_quantile_returns

# Phase 7E: Generative
from oskill.generative.ddpm_paths import ddpm_synthetic_path_generator
from oskill.hmm import gaussian_hmm
from oskill.llm.consistency import llm_response_consistency
from oskill.llm.cot import chain_of_thought_extractor
from oskill.llm.deterministic_call import deterministic_llm_call
from oskill.llm.faithfulness import faithfulness_score
from oskill.llm.multi_model import multi_model_ensemble
from oskill.llm.prompt_fingerprint import prompt_fingerprint

# Phase 3: LLM
from oskill.llm.tool_validation import tool_call_validator

# Phase 9A: Market Making
from oskill.market_making.avellaneda_stoikov import avellaneda_stoikov_quotes
from oskill.market_making.cartea_jaimungal import cartea_jaimungal_optimal_quotes
from oskill.microstructure.bar_aggregation import (
    dollar_bar_aggregation,
    tick_imbalance_bar,
    volume_imbalance_bar,
)
from oskill.microstructure.hawkes import hawkes_branching_ratio
from oskill.microstructure.liquidity import amihud_illiquidity, kyle_lambda_estimator

# Phase 4: Microstructure
from oskill.microstructure.order_flow import order_flow_imbalance
from oskill.ml_finance.bet_sizing import bet_sizing
from oskill.ml_finance.cusum_filter import cusum_filter
from oskill.ml_finance.fractional_diff import fractional_differentiation
from oskill.ml_finance.meta_labeling import meta_labeling
from oskill.ml_finance.sample_weights import return_attribution_weights, sample_uniqueness_weights

# Phase 4 prerequisites + Phase 5B: ml_finance
from oskill.ml_finance.triple_barrier import triple_barrier_label

# Phase 9A: Operational Risk
from oskill.operational_risk.lda import operational_risk_lda
from oskill.performance import (
    bootstrap_sharpe,
    factor_attribution,
    psr_dsr,
    regime_aware_performance,
)
from oskill.point_process import fit_hawkes
from oskill.prediction import calibration_analysis

# Phase 3: RAG
from oskill.rag.chunking import chunking_strategy_apply
from oskill.rag.reranking import reranker_score
from oskill.scm_fit import structural_causal_model_fit
from oskill.signal_detection import adx, cusum_detector, platt_calibration
from oskill.signals.aggregation import weighted_signal_aggregation
from oskill.signals.ensemble import signal_ensemble

# Phase 9A: Signature
from oskill.signature.kernel import signature_kernel
from oskill.signature.pricing import signature_based_pricing
from oskill.similarity import (
    commodity_ratio_analytics,
    geopolitical_risk_index,
    historical_analogy_search,
    regime_transition_analysis,
)

# Phase 4: State Space
from oskill.state_space.kalman import kalman_filter_pipeline, kalman_smoother
from oskill.state_space.particle import particle_filter_pipeline
from oskill.validation import (
    cpcv_pipeline,
    regime_aware_rolling,
    walk_forward_optimization,
)

# Phase 6C: Advanced validation
from oskill.validation.csv import combinatorially_symmetric_cv
from oskill.validation.deflated_sharpe import deflated_sharpe_ratio
from oskill.validation.full_cpcv import full_combinatorial_purged_cv
from oskill.validation.haircut import haircut_sharpe

# Phase 2: Validation
from oskill.validation.pbo import probability_of_backtest_overfitting
from oskill.validation.trial_correction import bonferroni_holm_correction

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
    # Group 23: Microstructure (Phase 4)
    "order_flow_imbalance",
    "dollar_bar_aggregation",
    "volume_imbalance_bar",
    "tick_imbalance_bar",
    "kyle_lambda_estimator",
    "amihud_illiquidity",
    "hawkes_branching_ratio",
    # Group 24: State Space (Phase 4)
    "kalman_filter_pipeline",
    "kalman_smoother",
    "particle_filter_pipeline",
    # Group 25: Conformal Prediction (Phase 7B)
    "conformal_prediction_interval",
    "adaptive_conformal_inference",
    "conformal_with_change_points",
    # Group 26: Distributional RL (Phase 7C)
    "quantile_regression_loss",
    "implicit_quantile_loss",
    # Group 27: Causal Discovery (Phase 7D)
    "pcmci_causal_discovery",
    "structural_causal_model_fit",
    # Group 28: Generative (Phase 7E)
    "ddpm_synthetic_path_generator",
    # Group 29: Signature (Phase 9A)
    "signature_kernel",
    "signature_based_pricing",
    # Group 30: Market Making (Phase 9A)
    "avellaneda_stoikov_quotes",
    "cartea_jaimungal_optimal_quotes",
    # Group 31: Operational Risk (Phase 9A)
    "operational_risk_lda",
]
