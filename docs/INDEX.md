# oskill Skills Index

## Group 1: Performance Evaluation

| Skill | Description | Calls |
|-------|-------------|-------|
| `bootstrap_sharpe` | Sharpe ratio bootstrap distribution + CI | `bootstrap_ci`, `sharpe_ratio` |
| `psr_dsr` | Probabilistic & Deflated Sharpe Ratio | `bootstrap_ci`, `skew_kurt_robust`, `sharpe_ratio` |
| `factor_attribution` | Fama-French factor attribution + bootstrap CI | `beta_alpha_ols`, `bootstrap_ci` |
| `regime_aware_performance` | Per-regime performance breakdown | `regime_filter_data`, `sharpe_ratio`, `drawdown_curve`, `value_at_risk` |

## Group 2: Time-Series Validation

| Skill | Description | Calls |
|-------|-------------|-------|
| `walk_forward_optimization` | Walk-Forward IS/OOS rolling splits | `purge_embargo_split`, `rolling_window_split` |
| `cpcv_pipeline` | Combinatorial Purged CV with path reconstruction | `purge_embargo_split`, `bootstrap_ci`, `distribution_summary` |
| `regime_aware_rolling` | Regime-aware rolling window computation | `regime_filter_data`, `rolling_window_split` |

## Group 3: Distribution & Anomaly

| Skill | Description | Calls |
|-------|-------------|-------|
| `distribution_shift_test` | Multi-method distribution drift detection | `kolmogorov_smirnov_test`, `wasserstein_distance`, `symmetric_kl_divergence`, `distribution_summary` |
| `detect_outliers_robust` | Robust multi-method outlier detection | `zscore_normalize`, `distribution_summary` |
| `bootstrap_distribution` | Bootstrap distribution of any statistic | `bootstrap_ci`, `distribution_summary`, `kde_density` |

## Group 4: Similarity Retrieval

| Skill | Description | Calls |
|-------|-------------|-------|
| `historical_analogy_search` | Historical analogy ensemble search | `dtw_distance`, `wasserstein_distance`, `cosine_similarity_batch`, `euclidean_distance_matrix` |
| `regime_transition_analysis` | Regime transition matrix + duration analysis | `regime_transition_matrix`, `regime_filter_data`, `distribution_summary` |
| `commodity_ratio_analytics` | Commodity price ratio analysis + regime classification | `percentile_rank`, `zscore_normalize` |
| `geopolitical_risk_index` | Geopolitical risk index from event data with EWMA decay | `ewma_smooth`, `percentile_rank` |

## Group 5: Prediction Quality

| Skill | Description | Calls |
|-------|-------------|-------|
| `calibration_analysis` | Full calibration analysis (Brier + ECE + MCE) | `brier_score_decomposed`, `percentile_rank`, `bayes_beta_update` |

## Group 6: General Purpose (MathModelAgent SKILL 3O 内化, v4.15.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `typst_minimal_doc` | Typst 最小文档生成 | — |
| `typst_format_check` | typstyle 格式化检查循环 (check→diff→apply) | `bash_exec` |
| `typst_probe` | 无文件 Typst 表达式探针 (stdin + query) | `bash_exec` |
| `typst_compile` | typst compile 编译验证 | `bash_exec` |
| `detect_platform` | 平台/发行版/包管理器检测 | `bash_exec` |
| `check_dependencies` | 依赖探测 (cmd / python 包) | `bash_exec`, `_import_module` |
| `install_commands` | 按平台选择安装命令 | — |
| `run_doctor` | 环境检查总入口 (可选自动安装) | 上述全部 |
| `resolve_template` | 科研绘图模板解析 (id/别名/中文) | — |
| `list_figure_templates` | 模板清单 | — |
| `render_figure_template` | 复制模板脚本到工作区并执行 | `subprocess` |
