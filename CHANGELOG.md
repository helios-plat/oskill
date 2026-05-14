# Changelog

<!-- Governance: see RELEASE_POLICY.md. main = release branch; feat branches deleted after merge; oprim → oskill → omodul merge order required; container bind-mount means git checkout is a live operation. -->

## [2.0.0] - 2026-05-14

### Added — Phase 10 (17 new elements)

#### Behavioral Finance
- `behavioral/cpt_portfolio.py`: `cpt_portfolio_optimize` (Tversky-Kahneman CPT portfolio via convex relaxation)
- `behavioral/cpt_analytical.py`: `cpt_portfolio_analytical` (Bernard-Ghossoub 2010 closed-form)
- `behavioral/salience_pricing.py`: `salience_asset_pricing` (BGS 2013)
- `robust/maxmin_eu.py`: `maxmin_expected_utility_portfolio` (Gilboa-Schmeidler 1989)

#### Networks + Systemic Risk
- `networks/centrality.py`: `financial_network_centrality`
- `networks/clearing.py`: `eisenberg_noe_clearing` (Eisenberg-Noe 2001)
- `networks/contagion.py`: `contagion_simulate`
- `risk/systemic.py`: `systemic_risk_metrics` (CoVaR, MES, SRISK)

#### Spectral + Portfolio
- `spectral/laplacian.py`: `graph_laplacian_compute`
- `spectral/clustering.py`: `spectral_asset_clustering` (MST, PMFG, spectral)
- `portfolio/hrp.py`: `hierarchical_risk_parity_v2` (RIE-cleaned HRP, López de Prado 2016)
- `portfolio/ssd_milp.py`: `ssd_milp_optimizer` (Second-order Stochastic Dominance MILP)

#### Microstructure
- `microstructure/state_hawkes.py`: `order_book_state_hawkes`

#### Robust Control
- `robust/multiplier_preferences.py`: `multiplier_preferences_robust` (Hansen-Sargent)
- `robust/variational_preferences.py`: `variational_preferences_estimate`
- `robust/smooth_ambiguity.py`: `smooth_ambiguity_portfolio` (KMM 2005)

#### Recursive Utility
- `recursive_utility/ez_solver.py`: `epstein_zin_solver` (Bansal-Yaron 2004)

### Changed
- Version bump: 1.11.0 → 2.0.0
- Dependency: oprim >=2.0.0,<3.0.0

## [1.11.0] - 2026-05-09
### Added — Phase 9A
- signature_kernel, signature_based_pricing, avellaneda_stoikov_quotes, cartea_jaimungal_optimal_quotes, operational_risk_lda

## [1.5.0] - 2026-05-14

### Added (Phase 2: 5 new elements)

#### Covariance Estimation (`oskill.covariance`)
- `ledoit_wolf_shrinkage`: Ledoit-Wolf analytical shrinkage covariance estimator with three
  target options (constant_correlation, constant_variance, identity). Uses sklearn OAS as
  oracle for identity target; custom closed-form formula for other targets.
  Reference: Ledoit & Wolf (2004), "Honey, I Shrunk the Sample Covariance Matrix".
- `denoised_covariance`: Random Matrix Theory denoising via Marchenko-Pastur filter.
  Removes noise eigenvalues (below MP upper bound lambda_+ = (1+sqrt(N/T))^2) and replaces
  them with their mean to preserve trace. Supports mp_filter and constant_residual methods.
  Reference: López de Prado (2020), "Machine Learning for Asset Managers", Ch.2.

#### Validation Additions (`oskill.validation`)
- `probability_of_backtest_overfitting`: CSCV method (Bailey et al., 2015). Splits T observations
  into n_splits bins, evaluates C(n_splits, n_splits/2) train/test splits (capped at 500 samples),
  computes fraction of splits where IS best strategy ranks below OOS median.
  Reference: Bailey, Borwein, López de Prado, Zhu (2015), J. Computational Finance.
- `deflated_sharpe_ratio`: Corrects for selection bias via E[max(SR)] adjustment.
  Implements Bailey & LdP (2014) Eqs. 3-4: Euler-Mascheroni correction for N candidates,
  non-normality adjustment via skewness/kurtosis.
  Reference: Bailey & López de Prado (2014), Journal of Portfolio Management, 40(5), 94-107.

#### Factor Analysis (`oskill.factor`)
- `factor_quantile_returns`: Fama-MacBeth cross-sectional factor sorting into n_quantiles buckets.
  Computes equal-weighted returns per quantile per period, long-short returns (Q_top - Q_bottom),
  monotonicity score, and Sharpe ratio of the long-short portfolio.
  Reference: Fama & MacBeth (1973); Grinold & Kahn (2000).

### Infrastructure
- New submodules: `oskill/covariance/`, `oskill/validation/` (package, extends existing module),
  `oskill/factor/`
- JSON Schemas in `oskill/schemas/covariance/`, `oskill/schemas/validation/`,
  `oskill/schemas/factor/`
- `oskill/validation/` is now a package (previously a flat module); backward compatible
- All new elements have `@pytest.mark.academic_reference` tests

## [1.4.0] - 2026-05-14

### Added (Phase 1: 4 new elements)

#### Signal Ensemble
- `signal_ensemble`: Multi-method signal aggregation (linear/geometric/harmonic) with optional
  time decay. Clips output to [-1, 1].
  Reference: Carver (2015), "Systematic Trading"; López de Prado (2018) Ch.16.
- `weighted_signal_aggregation`: Carver's 3-layer forecast combination — shrinkage toward equal
  weights + Forecast Diversification Multiplier (FDM). Clips output to [-2, 2].
  Reference: Carver (2015), "Systematic Trading", Chapter 8.

#### LLM Integration (3O exclusive differentiation layer)
- `deterministic_llm_call`: Audit-ready LLM call wrapper with prompt fingerprinting,
  dependency-injected client_fn, JSON parsing, and inline schema validation.
  Stability: **experimental** (API surface may evolve as LLM ecosystem matures).
  Reference: arxiv 2601.15322 (Replayable Financial Agents); arxiv 2603.22567 (TrustTrade).
- `prompt_fingerprint`: Deterministic SHA-256 fingerprint for prompt configurations.
  Supports audit, caching, A/B testing, and cross-session reproducibility.
  Reference: arxiv 2601.15322 (Replayable Financial Agents, 2026).

### Breaking
- Bumped `oprim` dependency to `>=1.4.0,<2.0.0` (uses `oprim.sha256_hash`, `oprim.canonical_json`)

### Infrastructure
- JSON Schemas in `oskill/schemas/signals/` and `oskill/schemas/llm/`
- All elements have `@pytest.mark.academic_reference` tests
- LLM elements use dependency injection: caller provides `client_fn`; oskill does no network I/O
- Coverage: oskill total >=90%, Phase 1 elements 100%

### Architecture Note
The LLM integration follows the "delegated I/O" pattern: `oskill.llm.*` accepts a `client_fn`
callable from Layer 4 rather than bundling any LLM SDK. This preserves §1.1 "no I/O" while
enabling LLM-augmented signal generation and audit-grade fingerprinting.

## [1.1.0] - 2026-05-11

### Added

#### Group 4: Similarity Retrieval
- `commodity_ratio_analytics` — Commodity price ratio analysis with regime classification (calls `percentile_rank`, `zscore_normalize`)
- `geopolitical_risk_index` — Geopolitical risk index from event data with EWMA decay (calls `ewma_smooth`, `percentile_rank`)

### Infrastructure
- 27 new tests for the two new skills (211 total, up from 184)
- Updated docs/INDEX.md with new skill entries

## [1.0.0] - 2026-05-10

### Added

#### Group 1: Performance Evaluation
- `bootstrap_sharpe` — Sharpe ratio bootstrap distribution + CI
- `psr_dsr` — Probabilistic & Deflated Sharpe Ratio (Bailey & López de Prado 2012, 2014)
- `factor_attribution` — Fama-French factor attribution + bootstrap CI
- `regime_aware_performance` — Per-regime performance breakdown

#### Group 2: Time-Series Validation
- `walk_forward_optimization` — Walk-Forward IS/OOS rolling splits with purge/embargo
- `cpcv_pipeline` — Combinatorial Purged CV with path reconstruction (López de Prado 2018)
- `regime_aware_rolling` — Regime-aware rolling window computation

#### Group 3: Distribution & Anomaly
- `distribution_shift_test` — Multi-method distribution drift detection (KS + Wasserstein + JSD)
- `detect_outliers_robust` — Robust multi-method outlier detection with voting
- `bootstrap_distribution` — Bootstrap distribution of any statistic

#### Group 4: Similarity Retrieval
- `historical_analogy_search` — Historical analogy ensemble search (DTW + Wasserstein + cosine + euclidean)
- `regime_transition_analysis` — Regime transition matrix + duration + half-life analysis

#### Group 5: Prediction Quality
- `calibration_analysis` — Full calibration analysis (Brier decomposition + ECE + MCE + reliability diagram)

### Infrastructure
- Package skeleton with pyproject.toml (hatchling build)
- CI workflow (lint + test + coverage gate >= 90%)
- Layer 2 discipline enforcement (no internal imports, must use oprim)
- 181 tests, 95.77% coverage

### Fixed (pre-release review)
- cpcv_pipeline path reconstruction rewritten per LdP Ch.12
- bootstrap_distribution single bootstrap pass (no double sampling)
- historical_analogy_search reports excluded indices, proper Borda count
- distribution_shift_test JSD zero-bin handling
