# oskill Coverage Gap Report — feat/v1.5.0-phase2

**Current:** 80.86% (281 missing lines / 1468 statements)  
**Target:** 90%  
**Gap to close:** ~9.1 pp ≈ ~134 lines 须从 A 类覆盖

---

## 分类汇总

| 类别 | 行数 | 策略 |
|------|------|------|
| A — 须补测 | ~246 | 新增测试用例 |
| B — 可豁免 | ~35 | 加 `# pragma: no cover` 或接受为 exempt |
| C — 可标 | ~0 | 无明确死代码 |

**关键发现:** 281 行缺口中有 **198 行**来自 4 个零测试模块（`causal`, `hmm`, `point_process`, `signal_detection`），全是 Phase 1 Selene 迁移遗留的补测欠账。这是达标的决定性因素。

---

## 未覆盖文件逐一分析

### 1. `oskill/_base.py` (0%, 5 lines) + `oskill/_manifest.py` (0%, 5 lines)

**类别: B**  
纯类型别名 + 纯数据文件，无执行逻辑。  
**豁免方式:** 两文件顶部各加 `# pragma: no cover`

---

### 2. `oskill/causal.py` (14%, 38 lines: 50-109)

公开 API `symbolic_transfer_entropy` + 两个私有 helper `_compute_ste`, `_H_arr`，完全零测试。

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 50-69 | `symbolic_transfer_entropy` 函数体 (without surrogates) | **A** | 公开 API，omodul 使用 |
| 57-68 | surrogate significance testing 分支 (n_surrogates > 0) | **A** | 用户可触发的统计显著性路径 |
| 72-102 | `_compute_ste` 完整逻辑 | **A** | 核心算法，被公开函数调用 |
| 105-109 | `_H_arr` helper | **A** | 被 `_compute_ste` 调用 |

**建议新增测试 (在 `tests/causal/test_symbolic_transfer_entropy.py`):**
- `test_ste_basic_returns_dict_with_te_key` — 两段随机序列
- `test_ste_zero_for_independent_series` — 独立序列 TE ≈ 0
- `test_ste_positive_for_coupled_series` — `target = 0.8*source + 0.2*noise`
- `test_ste_with_surrogates_returns_p_value` — n_surrogates=100
- `test_ste_series_too_short_returns_zero_te` — min_len < 10 分支
- `@academic_reference test_ste_staniek_lehnertz_2008` — 验证 TE(X→Y) > TE(Y→X) for driven system

---

### 3. `oskill/hmm.py` (9%, 74 lines: 45-157)

`gaussian_hmm` + 四个私有 helpers 全部零测试。**这是 omodul 的直接依赖（`regime_aware_mean_reversion` 调用它），覆盖率最紧迫。**

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 45-98 | `gaussian_hmm` EM 主循环 | **A** | 公开 API，被 omodul 调用 |
| 101-108 | `_emission` Gaussian PDF | **A** | 核心算法，私有但须通过主函数覆盖 |
| 111-123 | `_forward` scaled forward algorithm | **A** | 核心算法 |
| 126-134 | `_backward` scaled backward algorithm | **A** | 核心算法 |
| 137-157 | `_viterbi` decoding | **A** | 核心算法，输出 viterbi_path |

**建议新增测试 (在 `tests/hmm/test_gaussian_hmm.py`):**
- `test_gaussian_hmm_returns_correct_keys` — 验证 {means, stds, state_probs, viterbi_path, ...}
- `test_gaussian_hmm_two_state_convergence` — 双峰分布 → 2 个状态
- `test_gaussian_hmm_viterbi_path_length` — len(path) == len(input)
- `test_gaussian_hmm_state_probs_sum_to_one` — 每行 sum ≈ 1
- `test_gaussian_hmm_convergence_flag` — 足够长数据应 converged=True
- `@academic_reference test_gaussian_hmm_baum_welch_1970` — 验证 EM log-likelihood 单调递增

---

### 4. `oskill/point_process.py` (19%, 21 lines: 42-77)

`fit_hawkes` 优化主循环零测试（虽然 `oprim.hawkes_nll` 依赖图已明确）。

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 42-43 | `len < 5` 早退路径 | **A** | 用户触发，当 event 数不足时 |
| 45-67 | Nelder-Mead 多起点优化循环 | **A** | 主算法路径 |
| 69-77 | `best_result is None` 失败路径 + 结果提取 | **A** | 失败路径 + 正常输出 |

**建议新增测试 (在 `tests/point_process/test_fit_hawkes.py`):**
- `test_fit_hawkes_too_few_events_returns_not_converged`
- `test_fit_hawkes_synthetic_returns_dict_keys`
- `test_fit_hawkes_branching_ratio_between_0_and_1` — 稳态要求 α/β < 1
- `test_fit_hawkes_known_params_rough_recovery` — 模拟 Hawkes 数据再拟合

---

### 5. `oskill/signal_detection.py` (8%, 65 lines: 36-188)

三个公开 API 全部零测试。

| 行 | 函数 | 类别 | 理由 |
|----|------|------|------|
| 36-87 | `adx` Wilder ADX 全函数体 | **A** | 公开 API，量化趋势强度 |
| 90-134 | `cusum_detector` CUSUM 全函数体 | **A** | 公开 API，变点检测 |
| 137-188 | `platt_calibration` 全函数体 | **A** | 公开 API，预测校准 |

**建议新增测试 (在 `tests/signal_detection/test_signal_detection.py`):**
- `test_adx_basic_returns_float`
- `test_adx_too_few_bars_raises`
- `test_adx_trending_market_high_value` — 强趋势数据 ADX > 25
- `test_cusum_basic_detects_shift` — mean shift 后有 signals
- `test_cusum_no_shift_no_signals` — 白噪声，threshold 较高
- `test_cusum_reset_after_signal` — signal 触发后累积器归零
- `test_platt_calibration_too_few_samples`
- `test_platt_calibration_returns_center_and_scale`
- `@academic_reference test_platt_1999_sigmoid_calibration` — 验证 log-loss 格式

---

### 6. `oskill/factor/quantile_returns.py` (74%, ~15 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 53, 58 | DataFrame input 转换 | **A** | 允许 DataFrame 输入，未测 |
| 66-71 | shape mismatch + 1D reshape | **A** | 验证分支 |
| 76-78 | N < n_quantiles raises | **A** | 验证分支 |
| 90 | sparse period skip (`valid < n_quantiles`) | **A** | 稀疏周期处理 |
| 98-101 | `pd.qcut` 失败的 rank fallback | **B** | 防御性 tie-handling，qcut 成功时不触发 |
| 107 | empty quantile bin skip | **B** | 极端情形，防御性 continue |
| 110-114 | `value_weighted` 方法 + unknown method raises | **A** | 两个分支均未测 |
| 129, 134, 138 | monotonicity/Sharpe 边界 (no valid LS) | **A** | 全 NaN 场景 |

**建议新增测试:**
- `test_factor_quantile_returns_dataframe_input`
- `test_factor_quantile_returns_shape_mismatch_raises`
- `test_factor_quantile_returns_too_few_assets_raises`
- `test_factor_quantile_returns_value_weighted`
- `test_factor_quantile_returns_unknown_method_raises`
- `test_factor_quantile_returns_all_nan_periods`

---

### 7. `oskill/covariance/denoising.py` (87%, 11 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 50-54 | ndarray input + 1D reshape | **A** | DataFrame 覆盖了，ndarray 和 1D 没测 |
| 101-105 | `constant_residual` 方法 + unknown method raises | **A** | 仅测了 mp_filter |
| 120-128 | PSD 强制修正 (eigvalsh < -1e-10) | **B** | 数值边界，正常数据极少触发 |

**建议新增测试:**
- `test_denoised_covariance_ndarray_input`
- `test_denoised_covariance_1d_input_raises`
- `test_denoised_covariance_constant_residual_method`
- `test_denoised_covariance_unknown_method_raises`

---

### 8. `oskill/covariance/shrinkage.py` (93%, 4 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 80-84 | ndarray input + 1D input | **A** | 同上，ndarray 路径未测 |
| 91 | N<2 validation | **A** | 验证分支 |
| 116 | alpha=0 when denominator≈0 | **B** | 数值保护，正常数据不触发 |

**建议新增测试:**
- `test_lw_shrinkage_ndarray_input`
- `test_lw_shrinkage_single_asset_raises`

---

### 9. `oskill/distribution.py` (94%, 10 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 229-233 | `mahalanobis` 1D fallback path | **A** | 1D 输入时退化为 z-score |
| 316-324 | `bootstrap_distribution`: `percentile` + `basic` CI 方法 | **A** | 仅测了 BCa，另两种方法未测 |

**建议新增测试:**
- `test_detect_outliers_mahalanobis_1d`
- `test_bootstrap_distribution_percentile_method`
- `test_bootstrap_distribution_basic_method`

---

### 10. `oskill/signals/aggregation.py` (92%, 6 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 69 | empty signals dict raises | **A** | 用户可触发 |
| 81 | weight key not in signals raises | **A** | 用户可触发 |
| 85 | sum of weights == 0 raises | **A** | 用户可触发 |
| 99 | signal length mismatch raises | **A** | 用户可触发 |
| 102 | pandas index mismatch raises | **A** | 用户可触发 |
| 163 | corr matrix diagonal != 1 raises | **A** | 用户可触发 |

**建议新增测试:**
- `test_wsa_empty_signals_raises`
- `test_wsa_missing_weight_key_raises`
- `test_wsa_zero_total_weight_raises`
- `test_wsa_signal_length_mismatch_raises`
- `test_wsa_corr_diagonal_not_one_raises`

---

### 11. `oskill/performance.py` (96%, 7 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 180, 196 | DSR/PSR: denominator≤0 → NaN | **B** | 数值退化边界，极端 skew/kurt 才触发 |
| 192 | multi-factor skew/kurt retrieval | **A** | 多因子 `factor_attribution` 从未测 |
| 300-301 | single-factor beta dict conversion | **A** | 单因子时 betas 为 float 非 dict 的分支 |
| 350, 354 | bootstrap multi-factor / single-factor beta | **A** | bootstrap 路径仅测了双因子 dict |
| 412-418 | `regime_aware_performance`: metrics + non-Series inputs defaults | **A** | 默认 metrics=None 和 ndarray input 未测 |

**建议新增测试:**
- `test_psr_dsr_single_factor_beta_float` — 单因子场景
- `test_regime_aware_performance_default_metrics`
- `test_regime_aware_performance_ndarray_input`

---

### 12. `oskill/similarity.py` (93%, 12 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 51, 55 | `historical_analogy_search`: ndarray input + ndarray DB | **A** | 允许 ndarray |
| 61 | empty DB raises | **A** | 用户触发 |
| 88-93, 102-106 | cosine/euclidean length mismatch warnings | **B** | 边界警告，极少触发 |
| 142-146 | weighted / unweighted ensemble paths | **A** | ensemble 两路均未测 |
| 189 | `regime_transition_analysis`: non-Series input | **A** | ndarray 输入 |
| 231 | `commodity_ratio_analytics`: data_per_regime non-Series | **A** | ndarray 输入 |
| 296-303 | `commodity_ratio_analytics`: high/low/extreme regime branches | **A** | 3 个 regime 分支仅测了 normal |
| 361-367 | `geopolitical_risk_index`: elevated/normal/low branches | **A** | 3 个分支仅测了 extreme |

**建议新增测试:**
- `test_analogy_search_ndarray_input`
- `test_analogy_search_empty_db_raises`
- `test_analogy_search_ensemble_weighted`
- `test_regime_transition_ndarray_input`
- `test_commodity_ratio_regime_high_branch`
- `test_commodity_ratio_regime_low_branch`
- `test_geo_risk_elevated_branch`
- `test_geo_risk_normal_branch`

---

### 13. `oskill/validation/_legacy.py` (96%, 4 lines)

| 行 | 内容 | 类别 | 理由 |
|----|------|------|------|
| 89-93 | `walk_forward`: non-anchored OOS end overflow → break | **A** | 当 OOS end 超出 n_total 时的提前退出 |
| 102, 106 | embargo 边界：actual_embargo 裁剪 + is_end_final ≤ is_start continue | **B** | 防御性保护，极端参数才触发 |
| 169, 173 | `cpcv_pipeline`: n_folds < 2 + n_test_groups < 1 | **A** | 验证分支 |
| 277 | path assignment fallback | **B** | 防御性 fallback |
| 348, 350 | `regime_aware_rolling`: non-Series inputs | **A** | ndarray 输入路径 |

**建议新增测试:**
- `test_walk_forward_oos_overflow_break` — oos_window 大到最后一步超边界
- `test_cpcv_invalid_n_folds_raises`
- `test_cpcv_invalid_n_test_groups_raises`
- `test_regime_aware_rolling_ndarray_inputs`

---

### 14. `oskill/validation/deflated_sharpe.py` (92%, 2 lines) + `pbo.py` (93%, 5 lines)

| 文件 | 行 | 内容 | 类别 |
|------|----|------|------|
| `deflated_sharpe.py` | 54 | empty sharpe_ratios → ValueError | **A** |
| `deflated_sharpe.py` | 56 | n_observations < 2 → ValueError | **A** |
| `pbo.py` | 58 | DataFrame input 转换 | **A** |
| `pbo.py` | 68 | n_splits < 2 → ValueError | **A** |
| `pbo.py` | 72 | N < 2 → ValueError | **A** |
| `pbo.py` | 99-100 | comb > 500 → 随机采样路径 | **A** |

**建议新增测试:**
- `test_dsr_empty_sharpe_ratios_raises`
- `test_dsr_insufficient_observations_raises`
- `test_pbo_dataframe_input`
- `test_pbo_invalid_n_splits_raises`
- `test_pbo_single_strategy_raises`
- `test_pbo_large_n_splits_triggers_sampling` — n_splits=20 → C(20,10)=184756 > 500

---

## 行动优先级

| 优先级 | 目标 | 行数 | 覆盖率增量估算 |
|--------|------|------|---------------|
| **P0** | `hmm.py` 全部测试 | 74 行 | **+5.0 pp** |
| **P0** | `signal_detection.py` (adx, cusum, platt) | 65 行 | **+4.4 pp** |
| **P0** | `causal.py` (ste, _compute_ste, _H_arr) | 38 行 | **+2.6 pp** |
| **P1** | `point_process.py` fit_hawkes | 21 行 | **+1.4 pp** |
| **P1** | `factor/quantile_returns.py` 缺失分支 | ~12 行 | **+0.8 pp** |
| **P2** | `aggregation.py` 验证分支 | ~6 行 | **+0.4 pp** |
| **P2** | `similarity.py` + `performance.py` + 小缺口 | ~30 行 | **+2.0 pp** |
| B 豁免 | `_base.py` + `_manifest.py` + defensive guards | ~35 行 | −2.4 pp 需求 |

**估算达标路径:**  
P0 完成 → +12.0 pp → 80.9% + 12.0% = 92.9%（已超 90% 目标）  
加上 B 豁免 → 需求再降 2.4 pp → 仅补 P0 即可达标。
