# Changelog

<!-- Governance: see RELEASE_POLICY.md. main = release branch; feat branches deleted after merge; oprim → oskill → omodul merge order required; container bind-mount means git checkout is a live operation. -->

## [3.0.0] - 2026-05-24

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added — Hevi Batch 3 — Video Generation Skills

- `oskill.script_writer(topic, target_duration_s, llm, template_prompt, language)` — LLM-based video script generation.
- `oskill.storyboard_planner(script, llm, shots_per_scene_min, shots_per_scene_max)` — Break script into shot-level storyboard.
- `oskill.shot_generator(storyboard, llm)` — Generate image prompts and TTS text per shot.
- `oskill.consistency_check(shots, llm)` — LLM-based character/scene consistency check.
- `oskill.reference_generator(shots, llm, style_prompt)` — Generate detailed image prompts per shot.
- `oskill.frame_renderer(references, image_provider, output_dir, concurrency)` — Concurrent image generation for shots.
- `oskill.subtitle_generator(shots, output_path, format)` — Generate SRT/ASS from shot plans.
- `oskill.avatar_assembler(shots, portrait_path, tts_provider, avatar_provider, output_dir, concurrency)` — Per-shot avatar video assembly.
- `oskill.video_assembler(avatar_videos, bgm_path, subtitle_path, output_path)` — Final video assembly (concat + BGM + subtitles).
- `oskill.shorts_recompose(full_video_path, storyboard, target_duration_s, output_path)` — Long video → shorts by importance.
- `oskill.metadata_generate(script, storyboard, llm, constraints, style_prompt)` — Platform-agnostic video metadata generation.
- `oskill.threeo_ingester(omodul_function, omodul_config, llm)` — Invoke 3O omodul and extract InsightContext.
- `oskill._schemas` — Shared Pydantic models (Script, Scene, Shot, Storyboard, ShotPlan, etc.).

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added — Phase 11C
- `oskill.render_template`: primitive for template variable substitution.
- `oskill.expand_tasks_from_note`: parse and deduplicate obsidian tasks.
- `oskill.hybrid_search`: supports optional `rerank` and `expand`.

### Changed — BREAKING
- **BREAKING**: `hybrid_search` parameter `user_id` is removed and replaced with `corpus_id`.
- `hybrid_search`, `ingest_substrate`, `translate_substrate` moved from `knowledge/` to root `oskill/`.

## [2.11.0] - 2026-05-24

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added — BATCH 19 — LLM Primitives

#### LLM Loop
- `oskill.tool_call_loop`: Generic LLM tool calling loop with ReAct-like pattern. Supports multi-turn interaction, tool handler registration, and usage tracking.
  - Protocol: `ToolHandler`, `LLMCaller`.
  - Termination: `end_turn`, `max_steps`, `tool_error`.

### Changed
- Bumped version to `2.11.0`.
- Coverage: 100% for `tool_call_loop`, overall >90% maintained.

## [2.5.0] - 2026-05-20

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added — Sprint 0 (14 new elements, experimental)

#### Signals
- `signals/forward_returns.py`: `aggregate_signal_returns` — event-driven forward return aggregation across multiple periods

#### Performance
- `performance.py` (appended): `portfolio_metrics_summary` — one-shot metrics bundle (CAGR, Sharpe, drawdown, win_rate)
- `performance.py` (appended): `trade_pnl_statistics` — grouped/overall PnL statistics

#### Similarity
- `similarity.py` (appended): `multi_dim_nearest_search` — k-NN search on multi-dimensional state vectors (euclidean, cosine, weighted)
- `similarity.py` (appended): `forward_outcome_distribution` — forward return distribution from historical analogues

#### Classifier
- `classifier/rule_based.py`: `rule_based_classifier` — deterministic threshold rule engine with exclusive label support
- `classifier/rule_based.py`: `rule_based_veto_check` — hard/soft veto rule evaluation

#### DSL
- `dsl/evaluator.py`: `dsl_rule_validate` — JSON Schema Draft 2020-12 rule validation
- `dsl/evaluator.py`: `dsl_rule_evaluate` — async three-stage (trigger/filter/action) rule evaluation

#### Regime
- `regime/multi_state_classify.py`: `multi_state_classify` — rule-based N-state regime classification with Markov transition validation

#### Factor
- `factor/disclosure_scoring.py`: `disclosure_event_scoring` — multi-dimensional weighted disclosure event scoring
- `factor/event_theme_cluster.py`: `event_theme_cluster` — stock-to-theme clustering with continuation probability
- `factor/sector_rotation.py`: `sector_capital_rotation_detect` — sector-level capital rotation detection

#### Backtest
- `backtest/market_rules_backtest.py`: `market_rules_backtest_run` — backtest engine with T+N, daily limits, commission, stamp tax

### Changed
- Bumped version to `2.5.0`
- Added JSON schemas: `schemas/dsl_rule.schema.json`, `schemas/market_rules_backtest_input.schema.json`, `schemas/market_rules_backtest_output.schema.json`
- Added 18 new test files covering Sprint 0 elements; overall coverage: 90.09% (≥90% target met)
- Fixed `portfolio_metrics_summary` to use `oprim.drawdown_curve["max_drawdown"]` instead of calling `.min()` on dict
- Fixed `market_rules_backtest_run` to correctly compute `prev_close` from previous bar (not current bar)

## [2.0.0] - 2026-05-14

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

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
### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added — Phase 9A
- signature_kernel, signature_based_pricing, avellaneda_stoikov_quotes, cartea_jaimungal_optimal_quotes, operational_risk_lda

## [1.5.0] - 2026-05-14

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

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

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

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

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

### Added

#### Group 4: Similarity Retrieval
- `commodity_ratio_analytics` — Commodity price ratio analysis with regime classification (calls `percentile_rank`, `zscore_normalize`)
- `geopolitical_risk_index` — Geopolitical risk index from event data with EWMA decay (calls `ewma_smooth`, `percentile_rank`)

### Infrastructure
- 27 new tests for the two new skills (211 total, up from 184)
- Updated docs/INDEX.md with new skill entries

## [1.0.0] - 2026-05-10

### Changed — Phase 11B Wave 6 — TTS Deferral

- `oskill.knowledge.generate_audio_narration` — Raises `NotImplementedError` (TTS deferred to v1.1+ due to upstream image issues).

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

---

## Release Governance Note (2026-05-14)

During the Phase 10 release process, we discovered that Phases 4-10 had been
accumulated on a single long-running feature branch (feat/v1.7.0-phase4) without
intermediate merges to main. The main branch was stale at v1.2.0 while the
actual code was at v2.0.0 on the feature branch.

**Resolution**: fast-forward merged main to feat HEAD, retagged on main, deleted
feat branch. See `RELEASE_POLICY.md` for the corrected workflow.

All future Phase releases must:
1. Use independent feat branches (not accumulate Phases on one branch)
2. Merge to main via PR before tagging
3. Tag on main (never on feat branches)
