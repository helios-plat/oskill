# Changelog

<!-- Governance: see RELEASE_POLICY.md. main = release branch; feat branches deleted after merge; oprim → oskill → omodul merge order required; container bind-mount means git checkout is a live operation. -->

## [4.4.0] — 2026-07-03

### Fixed
- fix: `docker_*` 原语导入路径修正 —— 这些原语已在 oprim v3.0.0 迁至 obase，但 7 个模块（container_resource_rank / multi_node_health_sweep / node_register_probe / container_health_aggregate / app_upgrade_preflight / restore_from_backup / restart_and_verify）仍 `from oprim import docker_*`，在当前 main 上 ImportError（自 v2.15.0 起潜伏，因 CI 从未成功运行而未被发现）。改为 `from obase.docker import ...`，并补 `obase>=0.12.1` 直接依赖。解除 omodul 测试套件 6 个模块的 collection 失败。
- fix(B7): `storyboard_planner` 不再无条件对 `script.scenes` 调 `.model_dump()` —— `Chapter.scenes` 是 `list[dict]`(dict 无 model_dump),此前传 Chapter 即 AttributeError。改为按需转换(dict 直用 / model 才 model_dump),拆掉 hevi 的 ScriptWrapper 猴补丁。
- feat(B8): `script_writer` 按 target_duration 在 prompt 中给出**目标旁白字数**(总量 + 每章),避免 LLM 欠写(此前只给 target duration,常严重欠写 → 如 1-5min 只出 ~7s 旁白、成片被压)。

## [3.19.0] — 2026-06-13

### Fixed
- fix: oprim 依赖约束 `>=2.2.0,<3.0.0` → `>=3.0.0`，解除与 oprim v3.x 系列的安装冲突（上限 <3.0.0 为历史遗留错误）

## [3.18.0] — 2026-06-13

### Added (hevi v2 — M5/M6 新建 + M7 扩展)
- feat: `select_reference` — 从 timeline_history 选 best reference frame (LLM 语义匹配)
- feat: `mllm_frame_consistency_check` — VLM 视觉一致性评分 (候选帧 → best_frame + passed)
- feat: `script_writer` +`chapter_mode=True` — 多章节 ChapterScript + SpeakerLine 多角色对话; chapter_mode=False 不变
- types: `_schemas.py` 新增 SpeakerLine / ShotFrame / ReferenceSet / FrameConsistencyResult / Chapter / ChapterScript

## [3.17.0] — 2026-06-12

### Changed — L2 枢纽惰性化
- feat: 顶层 `__init__.py` 惰性化: 采用 PEP 562 (`__getattr__`) + AST 静态扫描机制。
- 效果: `import oskill` 启动速度显著提升，在仅访问轻量函数时不再触发重依赖加载。
- 兼容性: 100% 保持现有 `from oskill import <name>` 路径可用 (含 343 个导出项)，非 BREAKING。

## [3.16.0] — 2026-06-12

### Added (AII 3O Batch 6 — 1 new element)
- feat: `formal_proof_verify` — 既有定理形式化确证: 查 Mathlib 是否有该定理形式化条目, 唯一命中则判 proven。依赖注入 oprim.mathlib_lookup。守 "proven 非 LLM 自信", 信任已有证明。

## [3.15.0] — 2026-06-12

### Changed — 版本序列纠偏
- chore: 修正版本序列: 此前 v2.16.0/v2.17.0 系 067871d 错误回退所致; v3.15.0 接续 v3.14.0 真实序列。代码内容 = v2.17.0 (含 liquidation_cascade_risk), 仅版本号纠偏。废弃 v2.16.0/v2.17.0 两个 tag (保留不删)。
- feat: `liquidation_cascade_risk` — 清算级联风险评估: OI历史分位 + funding极端度 + 拥挤度 + 基差背离 → risk_level (low/elevated/high/extreme) + direction_bias (long_squeeze/short_squeeze/neutral); 复用 oprim.percentile_rank; 12 测试 100% 覆盖

## [3.14.0] — 2026-06-05

### Added — Aegis 3O Batch 3 (9 new oskill elements)
- feat: `diagnose_pattern_match` — 纯算法信号→故障模式匹配 (5 内置: memory_pressure/cpu_saturation/queue_backlog/connection_exhaustion/disk_pressure + 自定义 patterns 支持)
- feat: `compute_severity_score` — 多维加权严重度评分 0–100 (error_rate/latency/affected_users/resource/pattern_confidence; is_prod ×1.3 倍率; 5标签 critical→info)
- feat: `classify_signal` — 信号类别分类 (infrastructure/application/business/security/unknown; keyword match + metric key presence)
- feat: `retrieve_runbook` — RAG runbook 检索 (vector_encode_fn → vector_search_fn composition; over-fetch + score filter + top_k)
- feat: `synthesize_action_plan` — LLM 行动计划合成 (症状 + runbook 上下文 + severity → JSON ActionStep 列表; list/str LLM response 双支持)
- feat: `verify_health_after_action` / `verify_health_after_action_detail` — HTTP 健康检查轮询 (oprim.network_http_health composition; bool + HealthVerifyResult 两种返回)
- feat: `circuit_breaker_check` — 熔断器状态机 (closed/open/half_open; error_rate + p99 latency 触发; 自定义阈值)
- feat: `compute_capacity_forecast` — 线性回归容量预测 (OLS 外推 + 阈值突破检测 + 可选 LLM narrative)
- feat: `caddy_route_add` — 原子添加 Caddy 路由 + 健康验证 (oprim.caddy_route_add_atomic → oprim.network_http_health composition)
- test: 78 新测试 (test_aegis_b3_pure_algo.py 44 + test_aegis_b3_composition.py 34)

## [3.13.2] — 2026-06-05

### Fixed
- fix: `ingest_substrate` INSERT 列对齐 Stratum migration 020 真 DDL — 去 `ulid`, 加 `user_id NOT NULL` (新必填参数 `user_id_hash: str`); mime `""` → `detect_mime(path) or None`
- fix: 区分 schema mismatch (`BinderException` → raise) vs connection error (`ConnectionException` → warn), 不再静默吞错
- fix: 全 sweep `apply_remote_events.py` substrates INSERT (去 ulid, 加 `event.user_id`, 补 is_pinned/pinned_at/pin_priority); concepts INSERT 对齐 migration 020 (去 description/source_ids/meta_json, 加 user_id/type/substrate_refs/related_concept_ids)
- fix: 测试 fixture `_SCHEMA_DDL` 升级为 migration 020 真 schema (substrates: user_id NOT NULL, pin_priority; concepts: migration 020 结构)
- test: 新增 `TestIngestV2` — user_id_hash 必填验证, user_id DB 写入验证, NULL mime 验证, BinderException raise, ConnectionException 降级 (5 新测试)

## [3.13.1] — 2026-06-05

### Fixed
- fix: SQL 表名修 substrate→substrates (SPEC v1.1 §M2 重命名后未跟进, advisor R-3 真测试暴露). 同步扫 note→notes, concept→concepts. 单元测试改用真 DuckDB fixture, 不再纯 mock.

## [3.13.0] — 2026-06-05

### Added (Stratum B3)
- `researcher_workflow` — search + fetch + concept extraction pipeline (searxng_search + url_fetch_ssrf_safe + concept_extractor oprim composition)

### Fixed (B0 pyproject drift)
- pyproject.toml synced from 3.0.0 → 3.12.0 → 3.13.0 to match git tag history

## [3.12.0] — 2026-06-04

### Added (Stratum B3)
- `feed_diff_pipeline` — Multi-feed monitoring: fetch RSS/Atom + diff detection (oprim composition)
- `image_qa` — Image Q&A: OCR + vision LLM + concept extraction (oprim composition)
- `web_search_augmented` — Web search via searxng + BM25 re-ranking (needs searxng deployment)

## [3.11.0] — 2026-06-04

### Added (AII-3O Batch 4b)
- `ku_extract_pipeline` — KU extraction pipeline: structural_chunk → llm_extract_ku per chunk → ku_gate_validate; returns candidates/rejected/chunks_processed

## [3.10.0] — 2026-06-04

### Added (AII-3O Batch 3b)
- `hybrid_retrieve` — multi-signal BM25 + graph RRF fusion retrieval (oprim composition)
- `trace_dependency` — multi-hop dependency chain traversal with coherence assessment
- `find_consistency_issues` — knowledge graph consistency validation (label conflicts, contradictions, cycles)

### Supporting oprim addition
- `oprim.bm25_search` — single BM25 keyword retrieval (added to oprim v2.25.0 without version bump)

## [3.9.0] - 2026-06-01 — Stratum Batch 2: 7 oskill (stateless)

### Added — Stratum B2

- `cross_layer_search` — RRF-fused multi-index search (tantivy + lancedb + pgvector); injected Callable managers; pinned_boost; scope filtering
- `recommend_content` — Recency + relevance recommender; domain/concept overlap scoring; graceful empty-profile fallback
- `resolve_conflict` — Three-way merge dispatch: highlight→merge, note→keep_both, metadata→last_write_wins
- `merge_platform_user_results` — Pure RRF fusion with pinned_boost multiplier
- `lint_substrate_graph` — In-memory substrate graph integrity: orphans, broken_links, stale_concepts, health_score 0–100
- `check_reference_integrity` — Single-source referential integrity check (missing_refs / orphan_refs)

### Extended — Stratum B2

- `hybrid_search` — `corpus_id: str | None = None` (was required); added `HybridSearchResult` wrapper type

### Notes
- All 6 NEW oskill stateless (no I/O, deps injected as Callable protocols)
- 43 new tests (27 group-A + 16 group-B)

## [3.8.0] - 2026-05-30 — B10 Tide v4 step2 oskills (12 oskills)

### Added — B10 Tide v4 step2

- `macro_surprise_compute` — fetch_macro_calendar + zscore_normalize + percentile_rank; returns MacroSurpriseReport with z-scored surprise and shock_count.
- `macro_cycle_engine_v2` — fetch_macro_m2 + fetch_macro_lpr + fetch_macro_pboc; majority-vote phase classification (easing/tightening/expansion/contraction/uncertain).
- `policy_sector_attribution` — policy_event_extraction + industry_attribution + fetch_sector_returns; links policy news to sector performance.
- `seat_winrate_aggregator` — compute_seat_t3_return + percentile_rank; per-seat win-rate ranked cross-sectionally.
- `unknown_seats_audit_loop` — percentile_rank + zscore_normalize + obase.text.fuzzy_match + obase.audit.format_audit_entry; creates audit entries for unrecognised high-volume seats.
- `sector_strength_aggregator` — fetch_themes_daily + theme_to_sw_industry_mapping + percentile_rank; maps concept themes → SW industry strength scores.
- `candidate_universe_builder_v3` — apply_screen_filter + percentile_rank + (oskill) candidate_pool_builder depth-1; enhanced pool with structured veto and percentile ranking.
- `similar_context_injector` — zscore_normalize + cosine_similarity_batch + LLMCaller Protocol; top-k context retrieval injected into LLM prompt.
- `industry_valuation_percentile` — pe_ttm_lookback_safe + percentile_rank; look-ahead-safe TTM PE with cross-sectional ranking (cheaper = lower percentile).
- `discipline_vs_violation_winrate_compute` — compute_seat_t3_return + stop_loss_compliance_check + percentile_rank + zscore_normalize; P0 — discipline vs violation group comparison with win-rate / P&L ratio / Sharpe.
- `system_history_aggregator` — percentile_rank + zscore_normalize + obase.audit.AuditEntry; action frequency report with anomaly detection.
- `equity_curve_3seg_compute` — train_val_oos_splitter + percentile_rank + (oskill) market_rules_backtest_run depth-1; 3-segment equity curve evaluation with overfitting detection.
- All 12 satisfy ≥2 oprim composition constraint; "Internal oprim composition:" docstring section present.
- 96 tests across 12 oskills (≥8 each; discipline P0 has 12 tests); 3.7.0 → 3.8.0.

## [Unreleased]

### Changed — P7-B4 — MINOR extensions: script_writer + storyboard_planner (backward compatible)

- `oskill.script_writer`: new optional `subjects: list[SubjectRef] | None = None` parameter. When provided, character names + descriptions are appended to the LLM system prompt. `subjects=None` (default) is identical to all prior behaviour.
- `oskill.storyboard_planner`: three new optional parameters — `subjects: list[SubjectRef] | None = None`, `style_marker: str | None = None`, `lighting_control: str | None = None`. When provided, `style_marker_prompt` / `lighting_control_prompt` / character info are injected into the system prompt. All default to `None` (backward compatible).
- `oskill._schemas.SubjectRef` — canonical Pydantic model (`subject_id`, `name`, `description=""`, `image_path=None`) moved from `multi_shot_storyboard_workflow` to `_schemas.py`. Re-exported at `oskill.SubjectRef`. `multi_shot_storyboard_workflow` imports from `_schemas`.
- 16 new tests (8 script_writer subjects + 8 storyboard_planner style/lighting/subjects). All 48 Phase-6 + P7-B4 tests pass. 100% coverage on modified files.

### Added — P7-B3 — Visual Generation Workflows (6 elements)

**Depth-0 oskill (direct oprim composition):**

- `oskill.character_three_view` — Portrait image → front/side/back character views via LLM prompt + `oprim.image_generate` × 3. Returns `ThreeViewResult` with paths + `consistency_score`.
- `oskill.storyboard_grid` — Scene description → 3×3 or 5×5 PIL grid via LLM + `oprim.image_generate` × N. Supports `grid_size` 9 or 25.
- `oskill.multi_angle_9` — Scene description → 9-camera-angle grid (3 angles × 3 distances) via LLM + `oprim.image_generate` × 9 + PIL 3×3 stitch.
- `oskill.comic_to_animation_workflow` — Comic panel → animation via LLM analysis + `oprim.image_generate` × N + `oprim.image_to_video` × N + `oprim.video_concat`.

**Depth-1 oskill (oskill composition, per v0.9 SPEC):**

- `oskill.character_consistency_workflow` — Calls `oskill.character_three_view` (depth-1) + `oprim.image_generate` × scenes. Returns `CharacterConsistencyResult`.
- `oskill.multi_shot_storyboard_workflow` — Calls `oskill.storyboard_grid` (depth-1) + `oprim.style_marker_prompt` + `oprim.lighting_control_prompt` + `oprim.image_generate` × scenes. Returns `MultiShotStoryboard`.

**New types:** `ThreeViewResult`, `CharacterThreeViewError`, `StoryboardGridError`, `MultiAngleError`, `ComicToAnimationError`, `CharacterConsistencyResult`, `CharacterConsistencyError`, `MultiShotStoryboard`, `MultiShotStoryboardError`, `SubjectRef`.

**Tests:** 75 tests, 100% coverage on all 6 modules. mypy --strict + ruff 0 errors.

### Added — Tide v4 Regime Elements (v3.7.0)

- `oskill.regime_smoothing` — Smooth raw regime states to prevent flapping. Configurable per-state minimum duration.
- `oskill.regime_conditional_score_weighted` — Regime-aware weighted composite scoring with per-regime multiplier overrides.
- `candidate_pool_builder` extended with `regime_aware` + `regime` parameters (backward compatible).
- New type dataclasses: `RawRegimeState`, `SmoothingConfig`, `SmoothingResult`, `DimContribution`, `ScoreWeightedResult`.

### Added — P6-B3 — Video Generation Workflows

- `oskill.image_to_video_workflow` — Multi-image animation with retry + fallback + concurrency.
- `oskill.video_self_assess` — VLM-based video quality self-assessment (metrics + frames + scoring).
- `VideoQualityScore` — Pydantic model (script/visual/pacing/overall scores + issues + suggestions).

---

## [3.3.0] - 2026-05-25

### Changed — Sprint 12 — multi_state_classify E1 Extension

- `multi_state_classify` now accepts `n_states_constraint` parameter (backward compatible).
- Output includes `n_states` field.

## [3.2.0] - 2026-05-24

### Added — Sprint 12 — Batch Similarity Indexing (B4) + Point-in-Time Join (B5)

- `batch_similarity_indexing(vectors, metadata, method, n_clusters, persist_path)` — Build flat/ivf similarity index.
- `point_in_time_join(left, right, left_on, right_on, value_cols, publish_lag_days)` — PIT join preventing lookahead bias.

## [3.1.0] - 2026-05-24

### Added — Sprint 11 — Rule Compliance Winrate Diff (B8)

- `rule_compliance_winrate_diff(trades, rule_check_fn, return_field)` — Compare winrate between rule-compliant and rule-violating trades.
  - Example: `result = rule_compliance_winrate_diff(trades=trades, rule_check_fn=check, return_field="pnl_pct")`

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

## [3.4.0] - 2026-05-25

### Added — Sprint 13 — Calendar Surprise Detect (B6) + LLM Batch Classify (B7)

- `calendar_surprise_detect(events, importance_filter)` — Detect economic calendar surprises.
- `llm_batch_classify(items, labels, llm, batch_size, multi_label)` — Batch LLM classification.

## [3.20.0] — 2026-06-13
### Added
- hicode 批次 D: apply_edit_block/apply_unified_diff/three_way_merge/syntax_check
  validate_edit/generate_patch_preview/chunk_code/extract_symbols/repo_map_build
  resolve_mentions/summarize_file/compress_context/plan_decompose/rank_relevant_files
  build_repo_context/semantic_search/format_diagnostics/parse_llm_tool_calls
  select_tools/merge_config/evaluate_hooks/match_permission_rule
  escalate_thinking_budget/plan_to_todos/apply_todo_update/compose_plugin_manifest
  build_subagent_prompt/merge_subagent_result/select_skill/load_skill_progressive
  resolve_memory_hierarchy/dedup_edits/build_undo_plan (共 34 个新元素)

## [3.25.1] — 2026-06-14
### Fixed
- cognitive_state: import KCState from oprim (not oprim.types)

## [3.25.2] — 2026-06-17
### Added
- trend_signal_compose: SuperTrend+EMA+ADX+MACD confluence 趋势信号 (R7)
- mean_reversion_compose: VWAP+BB+RSI+Stoch confluence 均值回归信号 (R7)
### Fixed
- 去掉 try/except ImportError 静默降级，改为直接 import

## [3.25.5] — 2026-06-18
### Fixed
- storyboard_planner: result = await llm(...) (同 script_writer v3.25.2 修复)

## [3.25.9] — 2026-06-19
### Fixed
- ingest_substrate: 加 content_override/metadata_override 参数
  content_override 非 None 时跳过文件解析，直接用传入 markdown
  → 修复 EPUB 套装拆分路径（process_inbox_substrate bundle 模式）

## [3.25.10] — 2026-06-19
### Fixed
- ingest_substrate: content_override 时跳过去重（bundle 多本共享源文件）
- ingest_substrate: content_override 路径直接用传入内容不重解析
- ingest_substrate: bundle 书 file_hash=None（无独立文件），title 从 metadata 取
- ingest_substrate: derivative 写入 content（bundle 路径内容不丢）
- classify_inbox_file: .epub 扩展名短路（detect_mime 把 epub 识别成 zip 的 bug）

## [3.25.11] — 2026-06-19
### Added
- ingest_substrate: D-assert bundle 衍生项入口去重断言（WARN 模式，不阻断）
  content_override 路径检测 bundle_file_hash 是否已存在
  覆盖盲区：API 直传路径绕过 folder_watcher 前置拦截的重复入库
  _detect_bundle_duplicate 辅助函数（查 meta_json.bundle_file_hash）

## [3.25.12] — 2026-06-19
### Added
- physics_force_analysis_guide: 物理受力分析苏格拉底引导
  （识别力→选定律→列方程，不直接给答案，错误反问引导）
- reading_comprehension_guide: 阅读理解引导（english/chinese）
  （定位关键句→推理，防元认知懒惰，Fan 2024 实证）

## [3.25.15] — 2026-06-24
### Fixed
- ontology_extract: 缺陷A — edge端點同步（temp_id→new_id映射表，edge source/target同步重寫）
- ontology_extract: 缺陷B — sub_type按knowledge_type分類約束，prompt內嵌合法值清單
  + 代碼層coerce：非法sub_type自動置NULL（不整條丟棄KU）

## [3.25.16] — 2026-06-24
### Changed
- ontology_extract: prompt 改為可注入參數（Layer 4 可注入領域 prompt）
  pass1_chunk_tmpl/system, pass1_outline_tmpl/system,
  pass2_chunk_tmpl, pass2_system, six_class_rules
  全部 optional，不注入則用內置默認（保留已驗證的六分類+grade unverified+論據降級邏輯）

## [4.0.0] — 2026-06-24
### BREAKING
- ontology_extract: prompt 改为必填参数（移除所有内置业务 prompt）
  元素只保留两遍法编排机制 + 结构性校验（grade/knowledge_type/sub_type/edge同步）
  六分类判据等业务语义全部由调用方注入
  必填参数：pass1_chunk_tmpl/system, pass1_outline_tmpl/system, pass2_chunk_tmpl, pass2_system
  迁移：调用方需自行提供 prompt（业务判据从主库移到 Layer 4）
### Fixed
- 修复 v3.25.15/16 未生效的缺陷A（edge端点同步 temp_id→new_id）
- 修复缺陷B（sub_type 非法值 coerce 为 NULL，不丢弃 KU）

## [4.1.0] — 2026-06-25
### Added
- ontology_extract: valid_knowledge_types / valid_sub_types / valid_relation_types injectable params
  (backward-compatible defaults to built-in VALID_* sets from oprim._aii_graph_types)
  Layer4 can now inject domain-specific vocabulary without modifying core element
