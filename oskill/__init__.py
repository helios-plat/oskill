"""oskill — Composite financial analysis workflows built on oprim atomic operations."""

# Aegis Batch 2, 3, 4 (v2.10.0)
from oskill._llm_caller import LLMCaller
from oskill._schemas import SubjectRef  # canonical location (P7-B4)
from oskill._signal import Signal
from oskill._version import __version__
from oskill.agentic_investigate_loop import (
    InvestigationOutcome,
    InvestigationStep,
    agentic_investigate_loop,
)

# Aegis Gap Elements — Batch B (v3.16.0)
from oskill.app_upgrade_preflight import (
    AppUpgradePreflightResult,
    PreflightCheck,
    app_upgrade_preflight,
)

# Phase 6D: Advanced backtest
from oskill.backtest.embargo_cv import embargo_purged_cv
from oskill.backtest.market_rules_backtest import market_rules_backtest_run
from oskill.backtest.random_subsampling import random_subsampling_validation
from oskill.backtest.walk_forward_optimization import walk_forward_optimization_pipeline
from oskill.backup_schedule_check import (
    BackupScheduleCheckResult,
    backup_schedule_check,
)
from oskill.bayesian.gp_regression import gaussian_process_regression
from oskill.bayesian.hierarchical import hierarchical_bayes_normal

# Phase 6B: Bayesian
from oskill.bayesian.linear_regression import bayesian_linear_regression
from oskill.bayesian.posterior_diagnostics import posterior_diagnostics
from oskill.bayesian.var import bayesian_var
from oskill.behavioral.cpt_analytical import cpt_portfolio_analytical

# Phase 10: Behavioral Portfolio
from oskill.behavioral.cpt_portfolio import cpt_portfolio_optimize
from oskill.behavioral.salience_pricing import salience_asset_pricing
from oskill.caddy_route_add import CaddyRouteAddResult, caddy_route_add
from oskill.candidate_universe_builder_v3 import (
    CandidateUniverseResult,
    candidate_universe_builder_v3,
)
from oskill.causal import symbolic_transfer_entropy

# Phase 7D: Causal Discovery
from oskill.causal_discovery import pcmci_causal_discovery

# Phase 4 prerequisites: change_point
from oskill.change_point.bayesian_online import bocpd_bayesian
from oskill.change_point.pelt import pelt_change_point
from oskill.character_consistency_workflow import (
    CharacterConsistencyError,
    CharacterConsistencyResult,
    character_consistency_workflow,
)

# P7-B3 — Visual Generation Workflows
from oskill.character_three_view import (
    CharacterThreeViewError,
    ThreeViewResult,
    character_three_view,
)
from oskill.check_reference_integrity import IntegrityReport, check_reference_integrity
from oskill.circuit_breaker_check import CircuitBreakerResult, circuit_breaker_check
from oskill.classifier.rule_based import rule_based_classifier, rule_based_veto_check
from oskill.classify_signal import SignalClassification, classify_signal
from oskill.comic_to_animation_workflow import ComicToAnimationError, comic_to_animation_workflow
from oskill.compute_capacity_forecast import (
    CapacityForecastResult,
    ForecastPoint,
    compute_capacity_forecast,
)
from oskill.compute_severity_score import SeverityResult, compute_severity_score
from oskill.conformal.adaptive_cp import adaptive_conformal_inference
from oskill.conformal.change_point_cp import conformal_with_change_points

# Phase 7B: Conformal Prediction
from oskill.conformal.split_cp import conformal_prediction_interval
from oskill.container_health_aggregate import (
    CheckResult,
    HealthAggregateResult,
    container_health_aggregate,
)

# Aegis Gap Elements — Batch A (v3.15.0)
from oskill.container_resource_rank import (
    ContainerResourceEntry,
    ContainerResourceRankResult,
    container_resource_rank,
)

# Aegis Gap Elements — Batch C (v3.17.0)
from oskill.container_swap import ContainerSwapResult, container_swap

# P0-1 fix (v2.7.0): sigmoid market impact model
from oskill.cost import crypto_market_impact_sigmoid
from oskill.covariance.denoising import denoised_covariance

# Phase 2: Covariance
from oskill.covariance.shrinkage import ledoit_wolf_shrinkage

# --- Stratum B2 — 7 oskill (v3.9.0) ---
from oskill.cross_layer_search import (
    Citation,
    CrossLayerSearchResult,
    FusedResult,
    cross_layer_search,
)
from oskill.crypto_data_skills import (
    CryptoSkillError,
    collect_cycle,
    collect_sectors,
    collect_sentiment,
    collect_write_event,
    compute_signal_quality,
    dex_cex_check,
    evaluate_stale,
    fear_greed_fetch_all,
    get_30d_returns_stddev,
    get_etf_inflow_7d,
    get_symbol_basis,
    get_symbol_daily_klines,
    get_symbol_max_pain,
    get_symbol_onchain_metrics,
    get_symbol_options_skew,
    proxy_check_and_notify,
    stale_check_and_notify,
    store_market,
)
from oskill.crypto_environ_processors import (
    EnvironProcessorSkillError,
    derivatives_agg_compute,
    dex_truth_compute,
    dex_truth_dydx_compute,
    dex_truth_gmx_compute,
    etf_flow_compute,
    etf_flow_per_ticker_compute,
    exchange_netflow_compute,
    macro_environ_compute,
    onchain_aggregate_compute,
    options_environ_compute,
)

# --- Helios Wave 01: Crypto Skills ---
from oskill.crypto_fusion_scorers import (
    FusionScorerError,
    derivatives_score,
    flow_score,
    macro_score,
    onchain_score,
    sentiment_score,
    support_resistance_score,
    trend_score,
)
from oskill.data import point_in_time_join
from oskill.data.calendar_surprise_detect import calendar_surprise_detect

# --- Aegis 3O Batch 3 (v3.14.0) ---
from oskill.diagnose_pattern_match import PatternMatchResult, diagnose_pattern_match
from oskill.discipline_vs_violation_winrate_compute import (
    DisciplineComparisonResult,
    GroupStats,
    TradeRecord,
    discipline_vs_violation_winrate_compute,
)
from oskill.distribution import (
    bootstrap_distribution,
    detect_outliers_robust,
    distribution_shift_test,
)
from oskill.distributional_rl.iqn import implicit_quantile_loss

# Phase 7C: Distributional RL
from oskill.distributional_rl.quantile_regression import quantile_regression_loss
from oskill.dsl.evaluator import dsl_rule_evaluate, dsl_rule_validate
from oskill.equity_curve_3seg_compute import EquityCurve3SegResult, equity_curve_3seg_compute
from oskill.event_trail_correlate import CorrelatedEvents, event_trail_correlate

# Phase 3 P18: OKX Demo exchange client
from oskill.exchange.okx_demo import (
    AccountSnapshot,
    FillEvent,
    OKXAPIError,
    OKXClientError,
    OKXDemoRestClient,
    OKXDemoWSPrivate,
    OrderResponse,
)
from oskill.expand_tasks_from_note import NormalizedTask, expand_tasks_from_note
from oskill.factor.barra import barra_style_decomposition
from oskill.factor.carhart import carhart_4_factor_model
from oskill.factor.disclosure_scoring import disclosure_event_scoring
from oskill.factor.event_theme_cluster import event_theme_cluster
from oskill.factor.fama_french import fama_french_5_factor_model

# Phase 4 prerequisites + Phase 5C: factor
from oskill.factor.ic import factor_ic
from oskill.factor.neutralization import factor_neutralization

# Phase 2: Factor
from oskill.factor.quantile_returns import factor_quantile_returns
from oskill.factor.sector_rotation import sector_capital_rotation_detect

# --- Stratum B3 (v3.12.0) ---
from oskill.feed_diff_pipeline import feed_diff_pipeline
from oskill.find_consistency_issues import find_consistency_issues

# Phase 7E: Generative
from oskill.generative.ddpm_paths import ddpm_synthetic_path_generator
from oskill.hmm import gaussian_hmm

# --- AII 3O Batch 3b (v3.10.0) ---
from oskill.hybrid_retrieve import hybrid_retrieve
from oskill.hybrid_search import (
    HybridSearchResult,
    QueryExpander,
    Reranker,
    SearchResult,
    hybrid_search,
)
from oskill.image_qa import image_qa

# P6-B3 — Video Generation Workflows
from oskill.image_to_video_workflow import ImageToVideoWorkflowError, image_to_video_workflow
from oskill.industry_valuation_percentile import (
    IndustryValuationRow,
    ValuationCandidateInput,
    industry_valuation_percentile,
)
from oskill.ingest_substrate import ingest_substrate

# --- AII 3O Batch 4b (v3.11.0) ---
from oskill.ku_extract_pipeline import ku_extract_pipeline
from oskill.lint_substrate_graph import (
    BrokenLink,
    ConceptRef,
    DerivativeRef,
    LintReport,
    NoteRef,
    SubstrateRef,
    lint_substrate_graph,
)
from oskill.llm.batch_classify import llm_batch_classify
from oskill.llm.consistency import llm_response_consistency
from oskill.llm.cot import chain_of_thought_extractor
from oskill.llm.deterministic_call import deterministic_llm_call
from oskill.llm.faithfulness import faithfulness_score
from oskill.llm.multi_model import multi_model_ensemble
from oskill.llm.prompt_fingerprint import prompt_fingerprint
from oskill.llm.text_translate import text_translate

# Phase 3: LLM
from oskill.llm.tool_validation import tool_call_validator

# Phase 3 P14: LLM client
from oskill.llm_client import (
    LLMAPIError,
    LLMRateLimit,
    LLMTimeout,
    LLMUnavailable,
    deepseek_call,
)
from oskill.macro_cycle_engine_v2 import MacroCycleResult, macro_cycle_engine_v2

# --- B10 — Tide v4 step2 oskills (12) ---
from oskill.macro_surprise_compute import (
    MacroSurpriseItem,
    MacroSurpriseReport,
    macro_surprise_compute,
)

# Phase 9A: Market Making
from oskill.market_making.avellaneda_stoikov import avellaneda_stoikov_quotes
from oskill.market_making.cartea_jaimungal import cartea_jaimungal_optimal_quotes
from oskill.merge_platform_user_results import (
    FusedResult as MergedFusedResult,
)
from oskill.merge_platform_user_results import (
    SearchResult as MergedSearchResult,
)
from oskill.merge_platform_user_results import (
    merge_platform_user_results,
)
from oskill.metric_baseline_compare import (
    BaselineCompareResult,
    MetricDelta,
    metric_baseline_compare,
)
from oskill.microstructure.bar_aggregation import (
    dollar_bar_aggregation,
    tick_imbalance_bar,
    volume_imbalance_bar,
)
from oskill.microstructure.hawkes import hawkes_branching_ratio
from oskill.microstructure.liquidity import amihud_illiquidity, kyle_lambda_estimator

# Phase 4: Microstructure
from oskill.microstructure.order_flow import order_flow_imbalance

# Phase 10: Microstructure
from oskill.microstructure.state_hawkes import order_book_state_hawkes
from oskill.ml_finance.bet_sizing import bet_sizing
from oskill.ml_finance.cusum_filter import cusum_filter
from oskill.ml_finance.fractional_diff import fractional_differentiation
from oskill.ml_finance.meta_labeling import meta_labeling
from oskill.ml_finance.sample_weights import return_attribution_weights, sample_uniqueness_weights

# Phase 4 prerequisites + Phase 5B: ml_finance
from oskill.ml_finance.triple_barrier import triple_barrier_label
from oskill.multi_angle_9 import MultiAngleError, multi_angle_9
from oskill.multi_node_health_sweep import (
    MultiNodeSweepResult,
    NodeHealthReport,
    multi_node_health_sweep,
)
from oskill.multi_shot_storyboard_workflow import (
    MultiShotStoryboard,
    MultiShotStoryboardError,
    multi_shot_storyboard_workflow,
)

# Phase 10: Networks + Systemic Risk
from oskill.networks.centrality import financial_network_centrality
from oskill.networks.clearing import eisenberg_noe_clearing
from oskill.networks.contagion import contagion_simulate
from oskill.node_register_probe import (
    NodeRegisterProbeResult,
    node_register_probe,
)

# Phase 9A: Operational Risk
from oskill.operational_risk.lda import operational_risk_lda
from oskill.performance import (
    bootstrap_sharpe,
    factor_attribution,
    portfolio_metrics_summary,
    psr_dsr,
    regime_aware_performance,
    rule_compliance_winrate_diff,
    subject_forward_winrate,
    trade_pnl_statistics,
)
from oskill.point_process import fit_hawkes
from oskill.policy_sector_attribution import (
    PolicySectorAttributionResult,
    policy_sector_attribution,
)
from oskill.portfolio.hrp import hierarchical_risk_parity_v2
from oskill.portfolio.ssd_milp import ssd_milp_optimizer
from oskill.prediction import calibration_analysis

# Phase 3: RAG
from oskill.rag.chunking import chunking_strategy_apply
from oskill.rag.reranking import reranker_score
from oskill.recommend_content import (
    ContentMeta,
    Recommendation,
    UserBehaviorProfile,
    recommend_content,
)

# Phase 10: Recursive Utility
from oskill.recursive_utility.ez_solver import epstein_zin_solver
from oskill.regime.multi_state_classify import multi_state_classify
from oskill.regime_conditional_score_weighted import regime_conditional_score_weighted

# Tide v4 — Regime Elements (v3.7.0)
from oskill.regime_smoothing import regime_smoothing
from oskill.render_template import TemplateVariableSpec, render_template

# --- Stratum B3 (v3.13.0) ---
from oskill.researcher_workflow import researcher_workflow
from oskill.resolve_conflict import Conflict, ResolvedResult, resolve_conflict
from oskill.restart_and_verify import (
    RestartAndVerifyOutcome,
    restart_and_verify,
)
from oskill.restore_from_backup import RestoreResult, restore_from_backup
from oskill.retrieve_and_synthesize import (
    RetrievedDoc,
    SynthesizedResult,
    retrieve_and_synthesize,
)
from oskill.retrieve_runbook import RetrieveRunbookResult, RunbookEntry, retrieve_runbook
from oskill.risk.systemic import systemic_risk_metrics
from oskill.robust.maxmin_eu import maxmin_expected_utility_portfolio

# Phase 10: Robust Control
from oskill.robust.multiplier_preferences import multiplier_preferences_robust
from oskill.robust.smooth_ambiguity import smooth_ambiguity_portfolio
from oskill.robust.variational_preferences import variational_preferences_estimate
from oskill.runbook_match import (
    RunbookMatchResult,
    runbook_match,
)
from oskill.scm_fit import structural_causal_model_fit
from oskill.screening import candidate_pool_builder
from oskill.seat_winrate_aggregator import (
    SeatTradeInput,
    SeatWinrateReport,
    seat_winrate_aggregator,
)
from oskill.sector_strength_aggregator import SectorStrengthReport, sector_strength_aggregator
from oskill.signal_detection import adx, cusum_detector, platt_calibration
from oskill.signals.aggregation import weighted_signal_aggregation
from oskill.signals.ensemble import signal_ensemble

# Sprint 0 additions (v2.5.0)
from oskill.signals.forward_returns import aggregate_signal_returns

# Phase 9A: Signature
from oskill.signature.kernel import signature_kernel
from oskill.signature.pricing import signature_based_pricing
from oskill.similar_context_injector import SimilarContextResult, similar_context_injector
from oskill.similarity import (
    commodity_ratio_analytics,
    forward_outcome_distribution,
    geopolitical_risk_index,
    historical_analogy_search,
    multi_dim_nearest_search,
    regime_transition_analysis,
)
from oskill.similarity_indexing import batch_similarity_indexing
from oskill.spectral.clustering import spectral_asset_clustering

# Phase 10: Spectral + Portfolio
from oskill.spectral.laplacian import graph_laplacian_compute

# Phase 4: State Space
from oskill.state_space.kalman import kalman_filter_pipeline, kalman_smoother
from oskill.state_space.particle import particle_filter_pipeline
from oskill.storyboard_grid import StoryboardGridError, storyboard_grid
from oskill.structured_log_anomaly_cluster import (
    LogAnomalyClusters,
    LogCluster,
    structured_log_anomaly_cluster,
)
from oskill.synthesize_action_plan import ActionPlanResult, ActionStep, synthesize_action_plan
from oskill.system_history_aggregator import SystemHistoryReport, system_history_aggregator
from oskill.tool_call_loop import (
    ToolHandler,
    tool_call_loop,
)
from oskill.trace_dependency import trace_dependency
from oskill.translate_substrate import translate_substrate
from oskill.types import (
    DimContribution,
    RawRegimeState,
    ScoreWeightedResult,
    SmoothingConfig,
    SmoothingResult,
)
from oskill.unknown_seats_audit_loop import UnknownSeatAuditResult, unknown_seats_audit_loop
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
from oskill.verify_health_after_action import (
    HealthVerifyResult,
    verify_health_after_action,
    verify_health_after_action_detail,
)
from oskill.video_self_assess import VideoQualityScore, VideoSelfAssessError, video_self_assess
from oskill.web_search_augmented import web_search_augmented

__all__ = [
    "__version__",
    # P0-1: cost model (v2.7.0)
    "crypto_market_impact_sigmoid",
    # Group 1: Performance
    "bootstrap_sharpe",
    "psr_dsr",
    "factor_attribution",
    "regime_aware_performance",
    "rule_compliance_winrate_diff",
    "batch_similarity_indexing",
    "point_in_time_join",
    "calendar_surprise_detect",
    "llm_batch_classify",
    "candidate_pool_builder",
    "subject_forward_winrate",
    "text_translate",
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
    # Group 32: Behavioral Portfolio (Phase 10)
    "cpt_portfolio_optimize",
    "maxmin_expected_utility_portfolio",
    "cpt_portfolio_analytical",
    "salience_asset_pricing",
    # Group 33: Networks + Systemic Risk (Phase 10)
    "financial_network_centrality",
    "eisenberg_noe_clearing",
    "systemic_risk_metrics",
    "contagion_simulate",
    # Group 34: Spectral + Portfolio (Phase 10)
    "graph_laplacian_compute",
    "spectral_asset_clustering",
    "hierarchical_risk_parity_v2",
    "ssd_milp_optimizer",
    # Group 35: Microstructure (Phase 10)
    "order_book_state_hawkes",
    # Group 36: Robust Control (Phase 10)
    "multiplier_preferences_robust",
    "variational_preferences_estimate",
    "smooth_ambiguity_portfolio",
    # Group 37: Recursive Utility (Phase 10)
    "epstein_zin_solver",
    # Phase 3 P14: LLM client
    "deepseek_call",
    "LLMUnavailable",
    "LLMRateLimit",
    "LLMAPIError",
    "LLMTimeout",
    # Phase 3 P18: OKX Demo exchange client
    "OKXDemoRestClient",
    "OKXDemoWSPrivate",
    "OKXAPIError",
    "OKXClientError",
    "OrderResponse",
    "FillEvent",
    "AccountSnapshot",
    # Sprint 0 additions (v2.5.0)
    "aggregate_signal_returns",
    "portfolio_metrics_summary",
    "trade_pnl_statistics",
    "multi_dim_nearest_search",
    "forward_outcome_distribution",
    "rule_based_classifier",
    "rule_based_veto_check",
    "dsl_rule_validate",
    "dsl_rule_evaluate",
    "multi_state_classify",
    "disclosure_event_scoring",
    "event_theme_cluster",
    "sector_capital_rotation_detect",
    "market_rules_backtest_run",
    # Aegis Batch 2, 3, 4 (v2.10.0)
    "LLMCaller",
    "Signal",
    "container_health_aggregate",
    "HealthAggregateResult",
    "CheckResult",
    "metric_baseline_compare",
    "BaselineCompareResult",
    "MetricDelta",
    "structured_log_anomaly_cluster",
    "LogAnomalyClusters",
    "LogCluster",
    "event_trail_correlate",
    "CorrelatedEvents",
    "agentic_investigate_loop",
    "InvestigationOutcome",
    "InvestigationStep",
    "tool_call_loop",
    "ToolHandler",
    "retrieve_and_synthesize",
    "SynthesizedResult",
    "RetrievedDoc",
    "runbook_match",
    "RunbookMatchResult",
    "restart_and_verify",
    "RestartAndVerifyOutcome",
    "hybrid_search",
    "Reranker",
    "QueryExpander",
    "SearchResult",
    "ingest_substrate",
    "translate_substrate",
    "render_template",
    "TemplateVariableSpec",
    "expand_tasks_from_note",
    "NormalizedTask",
    # P6-B3 — Video Generation Workflows
    "image_to_video_workflow",
    "ImageToVideoWorkflowError",
    "video_self_assess",
    "VideoQualityScore",
    "VideoSelfAssessError",
    # Tide v4 — Regime Elements (v3.7.0)
    "regime_smoothing",
    "regime_conditional_score_weighted",
    "RawRegimeState",
    "SmoothingConfig",
    "SmoothingResult",
    "DimContribution",
    "ScoreWeightedResult",
    # P7-B3 — Visual Generation Workflows
    "character_three_view",
    "CharacterThreeViewError",
    "ThreeViewResult",
    "storyboard_grid",
    "StoryboardGridError",
    "multi_angle_9",
    "MultiAngleError",
    "comic_to_animation_workflow",
    "ComicToAnimationError",
    "character_consistency_workflow",
    "CharacterConsistencyError",
    "CharacterConsistencyResult",
    "multi_shot_storyboard_workflow",
    "MultiShotStoryboardError",
    "MultiShotStoryboard",
    "SubjectRef",
    # --- Helios Wave 01: Crypto Fusion Scorers (7) ---
    "trend_score",
    "flow_score",
    "sentiment_score",
    "onchain_score",
    "derivatives_score",
    "macro_score",
    "support_resistance_score",
    "FusionScorerError",
    # --- Helios Wave 01: Crypto Environ Processors (10) ---
    "derivatives_agg_compute",
    "dex_truth_compute",
    "dex_truth_dydx_compute",
    "dex_truth_gmx_compute",
    "etf_flow_compute",
    "etf_flow_per_ticker_compute",
    "macro_environ_compute",
    "onchain_aggregate_compute",
    "exchange_netflow_compute",
    "options_environ_compute",
    "EnvironProcessorSkillError",
    # --- Helios Wave 01: Crypto Data/Alert/Collect Skills (18) ---
    "get_symbol_basis",
    "get_symbol_daily_klines",
    "get_symbol_onchain_metrics",
    "get_symbol_options_skew",
    "get_symbol_max_pain",
    "get_etf_inflow_7d",
    "get_30d_returns_stddev",
    "fear_greed_fetch_all",
    "dex_cex_check",
    "proxy_check_and_notify",
    "evaluate_stale",
    "stale_check_and_notify",
    "compute_signal_quality",
    "collect_cycle",
    "collect_sectors",
    "collect_sentiment",
    "store_market",
    "collect_write_event",
    "CryptoSkillError",
    # Stratum B2 (v3.9.0)
    "Citation",
    "CrossLayerSearchResult",
    "FusedResult",
    "cross_layer_search",
    "ContentMeta",
    "Recommendation",
    "UserBehaviorProfile",
    "recommend_content",
    "Conflict",
    "ResolvedResult",
    "resolve_conflict",
    "merge_platform_user_results",
    "lint_substrate_graph",
    "LintReport",
    "SubstrateRef",
    "DerivativeRef",
    "NoteRef",
    "ConceptRef",
    "BrokenLink",
    "check_reference_integrity",
    "IntegrityReport",
    "HybridSearchResult",
    # AII 3O Batch 3b (v3.10.0)
    "hybrid_retrieve",
    "trace_dependency",
    "find_consistency_issues",
    # AII 3O Batch 4b (v3.11.0)
    "ku_extract_pipeline",
    # Stratum B3 (v3.12.0)
    "feed_diff_pipeline",
    "image_qa",
    "web_search_augmented",
    # Stratum B3 (v3.13.0)
    "researcher_workflow",
    # Aegis 3O Batch 3 (v3.14.0)
    "PatternMatchResult",
    "diagnose_pattern_match",
    "SeverityResult",
    "compute_severity_score",
    "SignalClassification",
    "classify_signal",
    "RetrieveRunbookResult",
    "RunbookEntry",
    "retrieve_runbook",
    "ActionPlanResult",
    "ActionStep",
    "synthesize_action_plan",
    "HealthVerifyResult",
    "verify_health_after_action",
    "verify_health_after_action_detail",
    "CircuitBreakerResult",
    "circuit_breaker_check",
    "CapacityForecastResult",
    "ForecastPoint",
    "compute_capacity_forecast",
    "CaddyRouteAddResult",
    "caddy_route_add",
    # Aegis Gap Elements — Batch A (v3.15.0)
    "ContainerResourceEntry",
    "ContainerResourceRankResult",
    "container_resource_rank",
    "MultiNodeSweepResult",
    "NodeHealthReport",
    "multi_node_health_sweep",
    # Aegis Gap Elements — Batch B (v3.16.0)
    "AppUpgradePreflightResult",
    "PreflightCheck",
    "app_upgrade_preflight",
    "BackupScheduleCheckResult",
    "backup_schedule_check",
    "NodeRegisterProbeResult",
    "node_register_probe",
    # Aegis Gap Elements — Batch C (v3.17.0)
    "ContainerSwapResult",
    "container_swap",
    "RestoreResult",
    "restore_from_backup",
    # Additional exports to resolve linting issues
    "CandidateUniverseResult",
    "candidate_universe_builder_v3",
    "DisciplineComparisonResult",
    "GroupStats",
    "TradeRecord",
    "discipline_vs_violation_winrate_compute",
    "EquityCurve3SegResult",
    "equity_curve_3seg_compute",
    "IndustryValuationRow",
    "ValuationCandidateInput",
    "industry_valuation_percentile",
    "MacroCycleResult",
    "macro_cycle_engine_v2",
    "MacroSurpriseItem",
    "MacroSurpriseReport",
    "macro_surprise_compute",
    "MergedFusedResult",
    "MergedSearchResult",
    "PolicySectorAttributionResult",
    "policy_sector_attribution",
    "SeatTradeInput",
    "SeatWinrateReport",
    "seat_winrate_aggregator",
    "SectorStrengthReport",
    "sector_strength_aggregator",
    "SimilarContextResult",
    "similar_context_injector",
    "SystemHistoryReport",
    "system_history_aggregator",
    "UnknownSeatAuditResult",
    "unknown_seats_audit_loop",
]
