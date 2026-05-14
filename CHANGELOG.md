# Changelog

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
- Coverage: oskill total ≥90%, Phase 1 elements 100%

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
- CI workflow (lint + test + coverage gate ≥ 90%)
- Layer 2 discipline enforcement (no internal imports, must use oprim)
- 181 tests, 95.77% coverage

### Fixed (pre-release review)
- cpcv_pipeline path reconstruction rewritten per LdP Ch.12
- bootstrap_distribution single bootstrap pass (no double sampling)
- historical_analogy_search reports excluded indices, proper Borda count
- distribution_shift_test JSD zero-bin handling
