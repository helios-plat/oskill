# Changelog

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
- CI workflow (lint + test + coverage gate ≥ 90%)
- Layer 2 discipline enforcement (no internal imports, must use oprim)
- 181 tests, 95.77% coverage

### Fixed (pre-release review)
- cpcv_pipeline path reconstruction rewritten per LdP Ch.12
- bootstrap_distribution single bootstrap pass (no double sampling)
- historical_analogy_search reports excluded indices, proper Borda count
- distribution_shift_test JSD zero-bin handling
